"""Caso de uso: cadastrar empresa."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    DocumentoDuplicadoError,
    DocumentoInvalidoError,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security.pii_cipher import PiiCipher
from app.shared.domain.documento import Documento

MODULO = "organization"


@dataclass(frozen=True, slots=True)
class CreateCompany:
    legal_name: str
    trade_name: str
    documento: str | None
    ator: int | None
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class EmpresaCriada:
    id: int
    legal_name: str


class CreateCompanyHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        empresas: SqlCompanyRepository,
        cipher: PiiCipher,
        audit: AuditRecorder,
    ) -> None:
        self._uow = uow
        self._empresas = empresas
        self._cipher = cipher
        self._audit = audit

    async def execute(self, cmd: CreateCompany) -> EmpresaCriada:
        cifrado: str | None = None
        hash_do_documento: str | None = None

        if cmd.documento:
            try:
                documento = Documento.normalizar(cmd.documento)
            except ValueError as exc:
                raise DocumentoInvalidoError(str(exc)) from exc
            cifrado = self._cipher.cifrar(documento.digitos)
            hash_do_documento = self._cipher.hash_de_busca(documento.digitos)

            if await self._empresas.buscar_por_hash_de_documento(hash_do_documento):
                raise DocumentoDuplicadoError("empresa")

        empresa = await self._empresas.criar(
            legal_name=cmd.legal_name.strip(),
            trade_name=cmd.trade_name.strip(),
            document_encrypted=cifrado,
            document_hash=hash_do_documento,
            ator=cmd.ator,
        )
        self._audit.registrar(
            module=MODULO,
            action="company.created",
            actor_user_id=cmd.ator,
            aggregate_type="company",
            aggregate_id=str(empresa.id),
            correlation_id=cmd.correlation_id,
            # sem PII no payload: só o nome, que não é dado sensível
            payload={"legal_name": empresa.legal_name},
        )
        await self._uow.commit()

        return EmpresaCriada(id=empresa.id, legal_name=empresa.legal_name)
