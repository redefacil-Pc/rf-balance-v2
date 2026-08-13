"""Importador legado em dry-run, ponta a ponta (seção 18, DoD da F2).

Cobre: leitura por CSV, tradução das quatro estruturas, fila de exceção
persistida, reconciliação de contagens e totais — e, o mais importante, a
garantia de que **nada** é escrito no modelo canônico.

As fixtures são sintéticas. Dado real do v1 não entra no repositório.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text

from app.modules.legacy.application.commands.run_legacy_import import (
    CargaRealNaoImplementadaError,
    RelatorioDaImportacao,
    RunLegacyImport,
    RunLegacyImportHandler,
)
from app.modules.legacy.infrastructure.repositories.sql_legacy_import_repository import (
    SqlLegacyImportRepository,
)
from app.modules.legacy.infrastructure.sources.csv_legacy_source import CsvLegacySource
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import SystemClock

pytestmark = pytest.mark.integration

#: extração sintética que reproduz os defeitos reais do v1: documento inválido,
#: `role` fora do catálogo, BKO citado por um nome que não existe, comissão
#: gravada errada e a mesma venda repetida nas estruturas paralelas
FIXTURES = Path(__file__).parent.parent / "fixtures" / "legado"


@pytest.fixture
def legado() -> Path:
    return FIXTURES


@pytest.fixture
async def relatorio(legado: Path) -> AsyncIterator[RelatorioDaImportacao]:
    settings = get_settings()
    engine = criar_engine(settings.database)
    fabrica = criar_fabrica_de_sessoes(engine)
    try:
        async with UnitOfWork(fabrica) as uow:
            handler = RunLegacyImportHandler(
                uow=uow,
                origem=CsvLegacySource(legado),
                execucoes=SqlLegacyImportRepository(uow.session),
                clock=SystemClock(settings.app.app_timezone),
            )
            yield await handler.execute(RunLegacyImport(dry_run=True))
    finally:
        await engine.dispose()


async def _consultar(sql: str, **parametros: object) -> list[tuple[object, ...]]:
    engine = criar_engine(get_settings().database)
    try:
        async with engine.connect() as conexao:
            resultado = await conexao.execute(text(sql), parametros)
            return [tuple(linha) for linha in resultado]
    finally:
        await engine.dispose()


# ---------- a garantia principal ----------


async def test_dry_run_nao_escreve_no_modelo_canonico(
    relatorio: RelatorioDaImportacao,
) -> None:
    assert relatorio.run_id > 0

    for tabela in ("collaborators", "proposals", "collaborator_roles", "team_assignments"):
        linhas = await _consultar(f"SELECT COUNT(*) FROM {tabela}")
        assert linhas[0][0] == 0, f"dry-run escreveu em {tabela}"


async def test_carga_real_e_recusada_explicitamente(legado: Path) -> None:
    settings = get_settings()
    engine = criar_engine(settings.database)
    fabrica = criar_fabrica_de_sessoes(engine)
    try:
        async with UnitOfWork(fabrica) as uow:
            handler = RunLegacyImportHandler(
                uow=uow,
                origem=CsvLegacySource(legado),
                execucoes=SqlLegacyImportRepository(uow.session),
                clock=SystemClock(settings.app.app_timezone),
            )
            with pytest.raises(CargaRealNaoImplementadaError):
                await handler.execute(RunLegacyImport(dry_run=False))
    finally:
        await engine.dispose()


# ---------- tradução e fila de exceção ----------


async def test_traduz_os_consultores_validos_e_barra_o_documento_ruim(
    relatorio: RelatorioDaImportacao,
) -> None:
    assert relatorio.consultores_lidos == 4
    # o de documento inválido não vira candidato
    assert relatorio.colaboradores == 3


async def test_issues_ficam_persistidas_com_origem_e_codigo(
    relatorio: RelatorioDaImportacao,
) -> None:
    linhas = await _consultar(
        "SELECT source_table, code, severity FROM legacy_import_issues WHERE run_id = :run",
        run=relatorio.run_id,
    )
    encontrados = {(str(origem), str(codigo)) for origem, codigo, _ in linhas}

    assert ("consultants", "documento-invalido") in encontrados
    assert ("consultants", "papel-desconhecido") in encontrados
    assert ("consultants", "empresa-do-consultor-sem-destino") in encontrados
    assert ("proposals", "participante-nao-resolvido") in encontrados
    assert ("proposals", "comissao-divergente") in encontrados
    assert ("propostas", "estrutura-duplicada") in encontrados
    assert ("sales", "estrutura-duplicada") in encontrados


async def test_bko_resolvido_por_nome_exato_e_o_desconhecido_relatado(
    relatorio: RelatorioDaImportacao,
) -> None:
    linhas = await _consultar(
        "SELECT legacy_id FROM legacy_import_issues "
        "WHERE run_id = :run AND code = 'participante-nao-resolvido'",
        run=relatorio.run_id,
    )
    # a proposta 1 tem BKO que existe; a 2 cita alguém que não existe
    assert {str(linha[0]) for linha in linhas} == {"2"}


async def test_estrutura_paralela_coincidente_aponta_a_proposta_principal(
    relatorio: RelatorioDaImportacao,
) -> None:
    linhas = await _consultar(
        "SELECT detail FROM legacy_import_issues "
        "WHERE run_id = :run AND source_table = 'propostas'",
        run=relatorio.run_id,
    )

    assert len(linhas) == 1
    assert "coincide com 1" in str(linhas[0][0])


# ---------- reconciliação ----------


async def test_resumo_totaliza_operacao_e_comissao_por_origem(
    relatorio: RelatorioDaImportacao,
) -> None:
    resumo = relatorio.para_dicionario()
    principal = resumo["propostas"]["proposals"]

    assert principal["lidos"] == 3
    assert principal["traduzidos"] == 3
    # 14629.64 + 10000.00 + 5000.00
    assert principal["operacao"] == "29629.64"
    # a proposta 3 tem comissão gravada errada no legado (400 em vez de 500)
    assert principal["comissao_do_legado"] == "5788.89"
    assert principal["comissao_calculada"] == "5888.89"
    assert principal["divergencia_de_comissao"] == "100.00"


async def test_resumo_fica_gravado_na_execucao(relatorio: RelatorioDaImportacao) -> None:
    linhas = await _consultar(
        "SELECT dry_run, finished_at FROM legacy_import_runs WHERE id = :run",
        run=relatorio.run_id,
    )

    assert linhas[0][0] == 1
    assert linhas[0][1] is not None


async def test_divergencia_grande_de_comissao_conta_como_bloqueio(
    relatorio: RelatorioDaImportacao,
) -> None:
    assert relatorio.bloqueios >= 2  # documento inválido + comissão divergente
