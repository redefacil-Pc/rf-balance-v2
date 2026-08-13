"""Atualização dos dados cadastrais de colaborador, preservando funções e histórico."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.application.commands.create_collaborator import (
    ChavePixSolicitada,
    _mascarar_chave,
)
from app.modules.organization.domain.errors import (
    RecursoNaoEncontradoError,
    UnidadeDeOutraEmpresaError,
)
from app.modules.organization.domain.value_objects.papel_de_colaborador import RegimeTributario
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.pii_cipher import PiiCipher
from app.platform.time.clock import Clock


@dataclass(frozen=True, slots=True)
class UpdateCollaborator:
    collaborator_id: int
    company_id: int
    unit_id: int | None
    full_name: str
    tax_regime: RegimeTributario
    email: str | None
    phone: str | None
    chave_pix: ChavePixSolicitada | None
    ator: int | None
    correlation_id: str | None


class UpdateCollaboratorHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        colaboradores: SqlCollaboratorRepository,
        empresas: SqlCompanyRepository,
        audit: AuditRecorder,
        cipher: PiiCipher,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._colaboradores = colaboradores
        self._empresas = empresas
        self._audit = audit
        self._cipher = cipher
        self._clock = clock

    async def execute(self, cmd: UpdateCollaborator) -> None:
        modelo = await self._colaboradores.buscar_por_id(cmd.collaborator_id)
        if modelo is None:
            raise RecursoNaoEncontradoError("Colaborador não encontrado.")
        if await self._empresas.buscar_por_id(cmd.company_id) is None:
            raise RecursoNaoEncontradoError("Empresa não encontrada.")
        if cmd.unit_id is not None:
            unidade = await self._empresas.buscar_unidade(cmd.unit_id)
            if unidade is None:
                raise RecursoNaoEncontradoError("Unidade não encontrada.")
            if unidade.company_id != cmd.company_id:
                raise UnidadeDeOutraEmpresaError("A unidade informada pertence a outra empresa.")

        antes = {
            "full_name": modelo.full_name,
            "company_id": modelo.company_id,
            "unit_id": modelo.unit_id,
            "tax_regime": modelo.tax_regime,
        }
        await self._colaboradores.atualizar_cadastro(
            collaborator_id=cmd.collaborator_id,
            company_id=cmd.company_id,
            unit_id=cmd.unit_id,
            full_name=cmd.full_name.strip(),
            tax_regime=cmd.tax_regime.value,
            email=(cmd.email or "").strip().lower() or None,
            phone=(cmd.phone or "").strip() or None,
            ator=cmd.ator,
        )
        if cmd.chave_pix is not None:
            hoje = self._clock.business_date()
            await self._colaboradores.encerrar_chaves_vigentes(
                collaborator_id=cmd.collaborator_id, em=hoje
            )
            valor = cmd.chave_pix.valor.strip()
            await self._colaboradores.registrar_chave_pix(
                collaborator_id=cmd.collaborator_id,
                key_type=cmd.chave_pix.tipo,
                key_encrypted=self._cipher.cifrar(valor),
                key_hash=self._cipher.hash_de_busca(valor),
                key_masked=_mascarar_chave(valor),
                valid_from=hoje,
                ator=cmd.ator,
            )
        self._audit.registrar(
            module="organization",
            action="collaborator.updated",
            actor_user_id=cmd.ator,
            aggregate_type="collaborator",
            aggregate_id=str(cmd.collaborator_id),
            correlation_id=cmd.correlation_id,
            payload={
                "antes": antes,
                "depois": {
                    "full_name": cmd.full_name.strip(),
                    "company_id": cmd.company_id,
                    "unit_id": cmd.unit_id,
                    "tax_regime": cmd.tax_regime.value,
                    "email": (cmd.email or "").strip().lower() or None,
                    "phone": (cmd.phone or "").strip() or None,
                    "payment_key_changed": cmd.chave_pix is not None,
                },
            },
        )
        await self._uow.commit()
