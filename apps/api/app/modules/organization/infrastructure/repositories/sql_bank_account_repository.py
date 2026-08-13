from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.infrastructure.models.bank_account_model import BankAccountModel


class SqlBankAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_collaborator(self, collaborator_id: int) -> list[BankAccountModel]:
        return list(
            (
                await self._session.scalars(
                    select(BankAccountModel)
                    .where(
                        BankAccountModel.owner_type == "COLLABORATOR",
                        BankAccountModel.owner_id == collaborator_id,
                    )
                    .order_by(BankAccountModel.id)
                )
            ).all()
        )

    async def get_for_collaborator(
        self, account_id: int, collaborator_id: int
    ) -> BankAccountModel | None:
        found: BankAccountModel | None = await self._session.scalar(
            select(BankAccountModel).where(
                BankAccountModel.id == account_id,
                BankAccountModel.owner_type == "COLLABORATOR",
                BankAccountModel.owner_id == collaborator_id,
            )
        )
        return found

    async def create(
        self,
        *,
        collaborator_id: int,
        company_id: int,
        bank_code: str,
        bank_name: str,
        branch: str,
        account_encrypted: str,
        account_masked: str,
        account_type: str,
        actor: int | None,
    ) -> BankAccountModel:
        model = BankAccountModel(
            owner_type="COLLABORATOR",
            owner_id=collaborator_id,
            company_id=company_id,
            bank_code=bank_code,
            bank_name=bank_name,
            branch=branch,
            account_encrypted=account_encrypted,
            account_masked=account_masked,
            account_type=account_type,
            created_by=actor,
            updated_by=actor,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(
        self,
        *,
        account_id: int,
        bank_code: str,
        bank_name: str,
        branch: str,
        account_encrypted: str | None,
        account_masked: str | None,
        account_type: str,
        actor: int | None,
    ) -> None:
        values: dict[str, object] = {
            "bank_code": bank_code,
            "bank_name": bank_name,
            "branch": branch,
            "account_type": account_type,
            "updated_by": actor,
        }
        if account_encrypted is not None and account_masked is not None:
            values.update(account_encrypted=account_encrypted, account_masked=account_masked)
        await self._session.execute(
            update(BankAccountModel).where(BankAccountModel.id == account_id).values(**values)
        )

    async def set_status(self, account_id: int, *, active: bool, actor: int | None) -> None:
        await self._session.execute(
            update(BankAccountModel)
            .where(BankAccountModel.id == account_id)
            .values(is_active=active, updated_by=actor)
        )
