"""Unit of Work: um commit por caso de uso.

Repositórios recebem a mesma sessão. Nenhum repositório commita; quem commita é
o handler, uma única vez, ao final do caso de uso.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UnitOfWork:
    __slots__ = ("_fabrica", "session")

    def __init__(self, fabrica: async_sessionmaker[AsyncSession]) -> None:
        self._fabrica = fabrica
        self.session: AsyncSession

    async def __aenter__(self) -> UnitOfWork:
        self.session = self._fabrica()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self.session.rollback()
        finally:
            await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
