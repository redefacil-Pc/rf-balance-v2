"""Aplica o catálogo de RBAC no banco: `python -m app.platform.db.sync_rbac`.

Separado do seed de propósito. O seed cria **dado** (contas) e não roda em
produção; isto reaplica **estrutura** derivada do código e precisa rodar em todo
ambiente, junto das migrações. Eram a mesma coisa, e por isso uma permissão nova
no catálogo só chegava ao banco quando alguém lembrava de semear usuários.

Sai com código 0 mesmo sem mudança alguma: é idempotente por natureza e o alvo
`migrate` depende disso para poder chamá-lo sempre.
"""

from __future__ import annotations

import asyncio
import sys

from app.modules.identity.infrastructure import rbac_sync
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes


async def executar(*, purgar: bool = False) -> int:
    settings = get_settings()
    engine = criar_engine(settings.database)
    fabrica = criar_fabrica_de_sessoes(engine)

    saida: list[str] = []
    try:
        async with fabrica() as session:
            relatorio = await rbac_sync.sincronizar(session)
            saida.extend(relatorio.mensagens())
            if not relatorio.mudou:
                saida.append("rbac já estava sincronizado")
            if purgar:
                # depois da sincronização: o que o catálogo declara já existe, e
                # sobra exatamente o que deve sumir
                saida.extend((await rbac_sync.purgar_obsoletos(session)).mensagens())
            await session.commit()
    finally:
        await engine.dispose()

    for mensagem in saida:
        print(mensagem)
    return 0


if __name__ == "__main__":
    # `--purgar` é explícito de propósito: remover papel é decisão de operador,
    # nunca efeito colateral do `migrate`
    raise SystemExit(asyncio.run(executar(purgar="--purgar" in sys.argv[1:])))
