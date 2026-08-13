"""Fonte MySQL: leitura direta do banco do sistema atual.

Usada quando há rota até o banco legado e se quer o dado mais fresco — no ensaio
de cutover, por exemplo, onde o delta final não pode passar por exportação manual.

**Somente leitura, e isso não é confiança no código:** a conexão deve usar um
usuário com `SELECT` apenas. O v1 continua sendo a verdade até o cutover, e um
importador com permissão de escrita no legado é um acidente esperando acontecer.

O nome da tabela nunca vem do usuário: é escolhido do conjunto declarado em
`TABELAS_CONHECIDAS`. Interpolar nome de tabela em SQL é a única forma de fazer
`FROM` dinâmico, então a lista fechada é a proteção.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.modules.legacy.application.ports.legacy_source import LinhaLegada

TABELAS_CONHECIDAS = frozenset(
    {
        "consultants",
        "proposals",
        "propostas",
        "sales",
        "payments",
        "consultor_lider",
        "users",
    }
)


class TabelaLegadaDesconhecidaError(ValueError):
    pass


class MySqlLegacySource:
    __slots__ = ("_engine", "_rotulo")

    def __init__(self, url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True)
        partes = urlsplit(url)
        # host e database bastam para o relatório; usuário e senha ficam de fora
        self._rotulo = f"mysql:{partes.hostname or '?'}{partes.path or ''}"

    @property
    def rotulo(self) -> str:
        return self._rotulo

    async def ler(self, tabela: str) -> list[LinhaLegada]:
        if tabela not in TABELAS_CONHECIDAS:
            raise TabelaLegadaDesconhecidaError(f"tabela legada não reconhecida: {tabela!r}")

        async with self._engine.connect() as conexao:
            resultado = await conexao.execute(text(f"SELECT * FROM {tabela}"))
            return [
                {chave: _texto(valor) for chave, valor in linha._mapping.items()}
                for linha in resultado
            ]

    async def fechar(self) -> None:
        await self._engine.dispose()


def _texto(valor: object) -> str | None:
    """Uniformiza com a fonte CSV: o tradutor recebe string ou ausência."""
    if valor is None:
        return None
    return str(valor)
