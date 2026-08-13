"""Orquestrador de semeadura: `python -m app.platform.db.seed`.

Chama o seeder de cada módulo — cada módulo semeia as suas próprias tabelas.
Não roda em produção.
"""

from __future__ import annotations

import asyncio
import sys

from app.modules.identity.infrastructure import seed_identity
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes


async def executar() -> int:
    settings = get_settings()
    if settings.app.is_production:
        print("seed não roda em produção", file=sys.stderr)
        return 1

    engine = criar_engine(settings.database)
    fabrica = criar_fabrica_de_sessoes(engine)

    try:
        async with fabrica() as session:
            mensagens = await seed_identity.semear(session)
            await session.commit()
    finally:
        await engine.dispose()

    for mensagem in mensagens:
        print(mensagem)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(executar()))
