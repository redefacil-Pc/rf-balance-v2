"""Comparação entre a migração esperada pelo código e a aplicada no banco.

O readiness falha quando divergem: app e schema fora de sincronia é causa de
erro silencioso em produção (seção 12.5 do blueprint).
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

_ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"


def revisao_esperada() -> str | None:
    """Head do diretório de migrações. `None` quando ainda não há revisão."""
    script = ScriptDirectory.from_config(Config(str(_ALEMBIC_INI)))
    return script.get_current_head()


async def revisao_aplicada(engine: AsyncEngine) -> str | None:
    """`None` quando o banco ainda não tem nenhuma migração aplicada."""
    async with engine.connect() as conexao:
        existe = await conexao.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'alembic_version'"
            )
        )
        if not existe.scalar():
            return None

        resultado = await conexao.execute(text("SELECT version_num FROM alembic_version"))
        linha = resultado.first()
        return str(linha[0]) if linha else None


async def esta_sincronizado(engine: AsyncEngine) -> tuple[bool, str | None, str | None]:
    esperada = revisao_esperada()
    aplicada = await revisao_aplicada(engine)
    return esperada == aplicada, esperada, aplicada
