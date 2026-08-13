"""`proposals` versus `propostas`/`sales`: nunca escolher sozinho (seção 18)."""

from __future__ import annotations

from datetime import date

from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.legacy.domain.policies import deteccao_de_duplicidade as duplicidade
from app.modules.legacy.domain.value_objects.candidato_a_proposta import CandidatoAProposta
from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Severidade
from app.shared.domain.dinheiro import Dinheiro


def candidato(
    origem: str,
    legacy_id: str,
    *,
    consultor: str = "35",
    quando: date = date(2026, 3, 10),
    valor: str = "10000.00",
) -> CandidatoAProposta:
    operacao = Dinheiro.de(valor)
    tps = PercentualTps.de("30")
    return CandidatoAProposta(
        origem=origem,
        legacy_id=legacy_id,
        consultant_legacy_id=consultor,
        business_date=quando,
        operation_amount=operacao,
        tps=tps,
        paid_amount=Dinheiro.zero(),
        comissao_do_legado=tps.aplicar_sobre(operacao),
        comissao_calculada=tps.aplicar_sobre(operacao),
        status_do_legado="ABERTA",
        status_calculado=StatusDaProposta.OPEN,
    )


def test_coincidencia_por_consultor_data_e_valor_vira_excecao() -> None:
    principais = [candidato("proposals", "1")]
    paralelos = [candidato("propostas", "90")]

    issues = duplicidade.detectar(principais, paralelos)

    assert len(issues) == 1
    assert issues[0].codigo is CodigoDeIssue.ESTRUTURA_DUPLICADA
    assert issues[0].dados["correspondentes"] == ["1"]
    # nada é promovido automaticamente, então é atenção e não bloqueio
    assert issues[0].severidade is Severidade.ATENCAO


def test_registro_paralelo_sem_correspondente_tambem_e_excecao() -> None:
    principais = [candidato("proposals", "1")]
    paralelos = [candidato("sales", "90", valor="777.00")]

    issues = duplicidade.detectar(principais, paralelos)

    assert len(issues) == 1
    assert "sem correspondente" in issues[0].detalhe
    assert "correspondentes" not in issues[0].dados


def test_data_diferente_nao_e_a_mesma_venda() -> None:
    principais = [candidato("proposals", "1", quando=date(2026, 3, 10))]
    paralelos = [candidato("propostas", "90", quando=date(2026, 3, 11))]

    issues = duplicidade.detectar(principais, paralelos)

    assert "sem correspondente" in issues[0].detalhe


def test_sem_estruturas_paralelas_nao_ha_excecao() -> None:
    assert duplicidade.detectar([candidato("proposals", "1")], []) == []
