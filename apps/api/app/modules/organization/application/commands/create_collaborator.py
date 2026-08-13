"""Caso de uso: cadastrar colaborador com papéis e chave PIX.

Um único commit cobre colaborador, papéis, PIX e auditoria. Documento e PIX são
cifrados aqui; nada de PII em claro chega ao log ou ao payload de auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    ContaJaVinculadaError,
    DocumentoDuplicadoError,
    DocumentoInvalidoError,
    RecursoNaoEncontradoError,
    UnidadeDeOutraEmpresaError,
)
from app.modules.organization.domain.policies.vigencia_policy import garantir_sem_sobreposicao
from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PapelDeColaborador,
    RegimeTributario,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.pii_cipher import PiiCipher
from app.platform.time.clock import Clock
from app.shared.domain.date_range import DateRange
from app.shared.domain.documento import Documento

MODULO = "organization"


@dataclass(frozen=True, slots=True)
class PapelSolicitado:
    papel: PapelDeColaborador
    valid_from: date
    valid_to: date | None = None


@dataclass(frozen=True, slots=True)
class ChavePixSolicitada:
    tipo: str
    valor: str


@dataclass(frozen=True, slots=True)
class CreateCollaborator:
    company_id: int
    unit_id: int | None
    full_name: str
    documento: str
    regime: RegimeTributario
    papeis: tuple[PapelSolicitado, ...]
    email: str | None = None
    phone: str | None = None
    chave_pix: ChavePixSolicitada | None = None
    #: conta de acesso já existente, vinculada no mesmo commit. Evita o cadastro
    #: em dois passos, em que uma falha no segundo deixaria a pessoa sem acesso
    user_id: int | None = None
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ColaboradorCriado:
    id: int
    full_name: str
    documento_mascarado: str
    papeis: list[str]


class CreateCollaboratorHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        colaboradores: SqlCollaboratorRepository,
        empresas: SqlCompanyRepository,
        cipher: PiiCipher,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._colaboradores = colaboradores
        self._empresas = empresas
        self._cipher = cipher
        self._audit = audit
        self._clock = clock

    async def execute(
        self, cmd: CreateCollaborator, *, commit: bool = True
    ) -> ColaboradorCriado:
        documento = self._normalizar_documento(cmd.documento)
        await self._validar_empresa_e_unidade(cmd)

        hash_do_documento = self._cipher.hash_de_busca(documento.digitos)
        if await self._colaboradores.existe_documento(hash_do_documento):
            raise DocumentoDuplicadoError()

        self._validar_papeis(cmd.papeis)
        await self._validar_conta(cmd.user_id)

        colaborador = await self._colaboradores.criar(
            company_id=cmd.company_id,
            unit_id=cmd.unit_id,
            full_name=cmd.full_name.strip(),
            document_encrypted=self._cipher.cifrar(documento.digitos),
            document_hash=hash_do_documento,
            document_type=documento.tipo.value,
            tax_regime=cmd.regime.value,
            email=(cmd.email or "").strip().lower() or None,
            phone=(cmd.phone or "").strip() or None,
            ator=cmd.ator,
        )

        for solicitado in cmd.papeis:
            await self._colaboradores.adicionar_papel(
                collaborator_id=colaborador.id,
                papel=solicitado.papel.value,
                valid_from=solicitado.valid_from,
                valid_to=solicitado.valid_to,
                ator=cmd.ator,
            )

        if cmd.user_id is not None:
            await self._colaboradores.definir_conta(
                collaborator_id=colaborador.id, user_id=cmd.user_id
            )

        if cmd.chave_pix:
            await self._registrar_pix(colaborador.id, cmd)

        self._audit.registrar(
            module=MODULO,
            action="collaborator.created",
            actor_user_id=cmd.ator,
            aggregate_type="collaborator",
            aggregate_id=str(colaborador.id),
            correlation_id=cmd.correlation_id,
            payload={
                "full_name": colaborador.full_name,
                "company_id": cmd.company_id,
                "unit_id": cmd.unit_id,
                "tax_regime": cmd.regime.value,
                "roles": [p.papel.value for p in cmd.papeis],
                # hash, nunca o documento
                "document_hash": hash_do_documento,
            },
        )
        if commit:
            await self._uow.commit()

        return ColaboradorCriado(
            id=colaborador.id,
            full_name=colaborador.full_name,
            documento_mascarado=documento.mascarado(),
            papeis=[p.papel.value for p in cmd.papeis],
        )

    @staticmethod
    def _normalizar_documento(bruto: str) -> Documento:
        try:
            return Documento.normalizar(bruto)
        except ValueError as exc:
            raise DocumentoInvalidoError(str(exc)) from exc

    async def _validar_empresa_e_unidade(self, cmd: CreateCollaborator) -> None:
        if await self._empresas.buscar_por_id(cmd.company_id) is None:
            raise RecursoNaoEncontradoError("Empresa não encontrada.")

        if cmd.unit_id is None:
            return

        unidade = await self._empresas.buscar_unidade(cmd.unit_id)
        if unidade is None:
            raise RecursoNaoEncontradoError("Unidade não encontrada.")
        if unidade.company_id != cmd.company_id:
            raise UnidadeDeOutraEmpresaError("A unidade informada pertence a outra empresa.")

    @staticmethod
    def _validar_papeis(papeis: tuple[PapelSolicitado, ...]) -> None:
        """Mesmo papel não pode ter vigências sobrepostas (ADR-0013)."""
        por_papel: dict[str, list[DateRange]] = {}
        for solicitado in papeis:
            intervalo = DateRange(solicitado.valid_from, solicitado.valid_to)
            existentes = por_papel.setdefault(solicitado.papel.value, [])
            garantir_sem_sobreposicao(
                intervalo, existentes, descricao=f"A vigência do papel {solicitado.papel.value}"
            )
            existentes.append(intervalo)

    async def _validar_conta(self, user_id: int | None) -> None:
        """Uma conta pertence a um colaborador só: duas pessoas no mesmo login
        tornariam "meus resultados" ambíguo, e é esse recorte que decide o que
        cada um enxerga."""
        if user_id is None:
            return
        dono = await self._colaboradores.colaborador_da_conta(user_id)
        if dono is not None:
            raise ContaJaVinculadaError(f"A conta já pertence ao colaborador {dono.full_name}.")

    async def _registrar_pix(self, collaborator_id: int, cmd: CreateCollaborator) -> None:
        assert cmd.chave_pix is not None
        valor = cmd.chave_pix.valor.strip()
        await self._colaboradores.registrar_chave_pix(
            collaborator_id=collaborator_id,
            key_type=cmd.chave_pix.tipo,
            key_encrypted=self._cipher.cifrar(valor),
            key_hash=self._cipher.hash_de_busca(valor),
            key_masked=_mascarar_chave(valor),
            valid_from=self._clock.business_date(),
            ator=cmd.ator,
        )


def _mascarar_chave(valor: str) -> str:
    """Amostra suficiente para o operador reconhecer a chave, sem expô-la."""
    if len(valor) <= 4:
        return "*" * len(valor)
    return f"{'*' * (len(valor) - 4)}{valor[-4:]}"
