"""Catálogo de contas que recebem o dinheiro do cliente.

CRUD simples de propósito: a arquitetura pede para não montar aggregate,
repositório e use case por operação quando não há regra de negócio — e aqui não
há. As duas únicas invariantes são rótulo único e conta desativada não voltar a
aparecer na escolha; o resto é cadastro.

Conta nunca é apagada: recebimento antigo aponta para ela, e sumir com o
registro faria o histórico mentir sobre onde o dinheiro caiu. Desativar tira da
escolha e preserva o passado.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.organization.domain.errors import (
    ContaDeRecebimentoDuplicadaError,
    RecursoNaoEncontradoError,
)
from app.modules.organization.infrastructure.models.receiving_account_model import (
    ReceivingAccountModel,
)
from app.platform.db.session.unit_of_work import UnitOfWork

MODULO = "organization"


class ReceivingAccountManager:
    def __init__(self, *, uow: UnitOfWork, audit: AuditRecorder) -> None:
        self._uow = uow
        self._session = uow.session
        self._audit = audit

    async def list(self, *, apenas_ativas: bool = False) -> list[ReceivingAccountModel]:
        consulta = select(ReceivingAccountModel)
        if apenas_ativas:
            consulta = consulta.where(ReceivingAccountModel.is_active.is_(True))
        # o rótulo desempata: sem isso, contas com a mesma ordem trocariam de
        # lugar entre uma consulta e outra
        consulta = consulta.order_by(
            ReceivingAccountModel.display_order, ReceivingAccountModel.label
        )
        return list((await self._session.scalars(consulta)).all())

    async def create(
        self,
        *,
        label: str,
        display_order: int | None,
        actor: int,
        correlation_id: str | None,
    ) -> ReceivingAccountModel:
        limpo = label.strip()
        await self._exigir_rotulo_livre(limpo, exceto=None)
        # sem ordem informada, entra no fim da lista
        ordem = display_order if display_order is not None else await self._proxima_ordem()
        model = ReceivingAccountModel(
            label=limpo,
            display_order=ordem,
            is_active=True,
            created_by=actor,
            updated_by=actor,
        )
        self._session.add(model)
        await self._session.flush()
        self._registrar(model, "receiving_account_created", actor, correlation_id)
        await self._uow.commit()
        await self._session.refresh(model)
        return model

    async def update(
        self,
        *,
        account_id: int,
        label: str,
        display_order: int | None,
        actor: int,
        correlation_id: str | None,
    ) -> ReceivingAccountModel:
        model = await self._exigir(account_id)
        limpo = label.strip()
        await self._exigir_rotulo_livre(limpo, exceto=account_id)
        model.label = limpo
        if display_order is not None:
            model.display_order = display_order
        model.updated_by = actor
        self._registrar(model, "receiving_account_updated", actor, correlation_id)
        await self._uow.commit()
        await self._session.refresh(model)
        return model

    async def set_status(
        self,
        *,
        account_id: int,
        is_active: bool,
        actor: int,
        correlation_id: str | None,
    ) -> ReceivingAccountModel:
        model = await self._exigir(account_id)
        model.is_active = is_active
        model.updated_by = actor
        acao = "receiving_account_activated" if is_active else "receiving_account_deactivated"
        self._registrar(model, acao, actor, correlation_id)
        await self._uow.commit()
        await self._session.refresh(model)
        return model

    async def _exigir(self, account_id: int) -> ReceivingAccountModel:
        model = await self._session.get(ReceivingAccountModel, account_id)
        if model is None:
            raise RecursoNaoEncontradoError("Conta de recebimento não encontrada.")
        return model

    async def _exigir_rotulo_livre(self, label: str, *, exceto: int | None) -> None:
        consulta = select(ReceivingAccountModel.id).where(ReceivingAccountModel.label == label)
        if exceto is not None:
            consulta = consulta.where(ReceivingAccountModel.id != exceto)
        if await self._session.scalar(consulta) is not None:
            raise ContaDeRecebimentoDuplicadaError("Já existe uma conta com esse nome.")

    async def _proxima_ordem(self) -> int:
        maior = await self._session.scalar(select(func.max(ReceivingAccountModel.display_order)))
        return int(maior or 0) + 1

    def _registrar(
        self,
        model: ReceivingAccountModel,
        acao: str,
        actor: int,
        correlation_id: str | None,
    ) -> None:
        self._audit.registrar(
            module=MODULO,
            action=f"organization.{acao}",
            actor_user_id=actor,
            aggregate_type="receiving_account",
            aggregate_id=str(model.id),
            correlation_id=correlation_id,
            payload={
                "label": model.label,
                "display_order": model.display_order,
                "is_active": model.is_active,
            },
        )
