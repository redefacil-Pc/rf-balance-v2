"""Importador legado em dry-run: `python -m app.modules.legacy.entrypoints.import_legacy`.

Uso:

    python -m app.modules.legacy.entrypoints.import_legacy --csv /dados/legado
    python -m app.modules.legacy.entrypoints.import_legacy --mysql

O `--mysql` lê `LEGACY_DATABASE_URL` do ambiente e exige usuário somente-leitura:
o v1 continua sendo a verdade até o cutover.

Imprime o relatório de divergência no terminal e o persiste em
`legacy_import_runs`. Sai com código 1 quando há bloqueio — assim uma execução em
pipeline falha enquanto existir registro que ninguém decidiu.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from app.modules.legacy.application.commands.run_legacy_import import (
    RunLegacyImport,
    RunLegacyImportHandler,
)
from app.modules.legacy.application.ports.legacy_source import LegacySource
from app.modules.legacy.infrastructure.repositories.sql_legacy_import_repository import (
    SqlLegacyImportRepository,
)
from app.modules.legacy.infrastructure.sources.csv_legacy_source import CsvLegacySource
from app.modules.legacy.infrastructure.sources.mysql_legacy_source import MySqlLegacySource
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import SystemClock


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importador legado (dry-run)")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--csv", type=Path, help="diretório com <tabela>.csv")
    grupo.add_argument(
        "--mysql", action="store_true", help="lê LEGACY_DATABASE_URL (somente leitura)"
    )
    parser.add_argument(
        "--json", action="store_true", help="imprime o relatório em JSON, para pipeline"
    )
    return parser.parse_args()


def _origem(argumentos: argparse.Namespace) -> LegacySource:
    if argumentos.csv:
        if not argumentos.csv.is_dir():
            raise SystemExit(f"diretório não encontrado: {argumentos.csv}")
        return CsvLegacySource(argumentos.csv)

    url = os.getenv("LEGACY_DATABASE_URL")
    if not url:
        raise SystemExit("LEGACY_DATABASE_URL não configurada")
    return MySqlLegacySource(url)


async def executar() -> int:
    argumentos = _argumentos()
    origem = _origem(argumentos)
    settings = get_settings()

    engine = criar_engine(settings.database)
    fabrica = criar_fabrica_de_sessoes(engine)

    try:
        async with UnitOfWork(fabrica) as uow:
            handler = RunLegacyImportHandler(
                uow=uow,
                origem=origem,
                execucoes=SqlLegacyImportRepository(uow.session),
                clock=SystemClock(settings.app.app_timezone),
            )
            relatorio = await handler.execute(RunLegacyImport(dry_run=True))
    finally:
        fechar = getattr(origem, "fechar", None)
        if fechar is not None:
            await fechar()
        await engine.dispose()

    if argumentos.json:
        print(json.dumps(relatorio.para_dicionario(), indent=2, ensure_ascii=False))
    else:
        _imprimir(relatorio.run_id, relatorio.source_label, relatorio.para_dicionario())

    return 1 if relatorio.bloqueios else 0


def _imprimir(run_id: int, rotulo: str, resumo: dict[str, object]) -> None:
    print(f"execução #{run_id} — origem {rotulo} — DRY-RUN, nada foi escrito no modelo canônico")
    print(f"consultores lidos: {resumo['consultores_lidos']}")
    print(f"colaboradores traduzidos: {resumo['colaboradores_traduzidos']}")

    propostas = resumo["propostas"]
    assert isinstance(propostas, dict)
    for origem, totais in propostas.items():
        print(f"\n[{origem}]")
        for chave, valor in totais.items():
            print(f"  {chave}: {valor}")

    issues = resumo["issues"]
    assert isinstance(issues, dict)
    print(f"\nfila de exceção: {issues['total']} ({issues['bloqueios']} bloqueios)")
    for codigo, quantidade in issues["por_codigo"].items():
        print(f"  {codigo}: {quantidade}")

    if issues["bloqueios"]:
        print(
            "\nhá bloqueios: nenhuma carga real pode acontecer antes de resolvê-los",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(executar()))
