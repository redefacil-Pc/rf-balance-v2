"""ACL de `proposals`: as duas conferências que sustentam o relatório (seção 18)."""

from __future__ import annotations

from datetime import date

from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Issue, Severidade
from app.modules.legacy.infrastructure.translators import proposal_translator as tradutor
from app.shared.domain.dinheiro import Dinheiro

CPF_CLIENTE = "07610793515"


def linha(**alteracoes: str | None) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "id": "1",
        "consultant_id": "35",
        "valor_proposta": "14629.64",
        "percentual_tps": "30.00",
        "valor_total_comissao": "4388.89",
        "nome_cliente": "CLIENTE EXEMPLO",
        "cpf_cliente": CPF_CLIENTE,
        "bko": "JUCELIA BARBOSA",
        "status": "FINALIZADA",
        "valor_total_pago": "4388.89",
        "valor_pendente": "0.00",
        "finalizacao": "RAFAELLA PINHO",
        "redmine_id": "6731",
        "proposal_date": "2026-03-10",
    }
    base.update(alteracoes)
    return base


def codigos(problemas: list[Issue]) -> set[str]:
    return {problema.codigo.value for problema in problemas}


def por_codigo(problemas: list[Issue], codigo: CodigoDeIssue) -> Issue:
    return next(problema for problema in problemas if problema.codigo is codigo)


def test_traduz_proposta_do_legado() -> None:
    candidato, problemas = tradutor.traduzir(linha())

    assert candidato is not None
    assert candidato.legacy_id == "1"
    assert candidato.external_id == "6731"
    assert candidato.business_date == date(2026, 3, 10)
    assert candidato.operation_amount == Dinheiro.de("14629.64")
    assert candidato.status_calculado is StatusDaProposta.PAID
    # o legado bate com o recálculo: nada de divergência
    assert CodigoDeIssue.COMISSAO_DIVERGENTE.value not in codigos(problemas)
    assert CodigoDeIssue.STATUS_DIVERGENTE.value not in codigos(problemas)


def test_divergencia_de_centavo_e_atencao() -> None:
    _, problemas = tradutor.traduzir(linha(valor_total_comissao="4388.88"))

    issue = por_codigo(problemas, CodigoDeIssue.COMISSAO_DIVERGENTE)
    assert issue.severidade is Severidade.ATENCAO
    assert issue.dados["diferenca"] == "0.01"


def test_divergencia_grande_de_comissao_bloqueia() -> None:
    _, problemas = tradutor.traduzir(linha(valor_total_comissao="3000.00"))

    issue = por_codigo(problemas, CodigoDeIssue.COMISSAO_DIVERGENTE)
    assert issue.severidade is Severidade.BLOQUEIO


def test_status_do_legado_divergente_do_recalculado_aparece() -> None:
    # o v1 diz quitada, mas nada foi recebido
    candidato, problemas = tradutor.traduzir(linha(valor_total_pago="0.00"))

    assert candidato is not None
    assert candidato.status_calculado is StatusDaProposta.OPEN
    issue = por_codigo(problemas, CodigoDeIssue.STATUS_DIVERGENTE)
    assert issue.dados == {"legado": "FINALIZADA", "calculado": "OPEN"}


def test_quitacao_dentro_da_tolerancia_e_reconhecida() -> None:
    # faltaram R$ 5,00 para a comissão: dentro da tolerância do v1
    candidato, problemas = tradutor.traduzir(linha(valor_total_pago="4383.89"))

    assert candidato is not None
    assert candidato.status_calculado is StatusDaProposta.PAID
    assert CodigoDeIssue.STATUS_DIVERGENTE.value not in codigos(problemas)


def test_operacao_zerada_bloqueia() -> None:
    candidato, problemas = tradutor.traduzir(linha(valor_proposta="0.00"))

    assert candidato is None
    assert CodigoDeIssue.VALOR_INVALIDO.value in codigos(problemas)


def test_tps_fora_do_intervalo_bloqueia() -> None:
    candidato, problemas = tradutor.traduzir(linha(percentual_tps="150"))

    assert candidato is None
    assert CodigoDeIssue.VALOR_INVALIDO.value in codigos(problemas)


def test_sem_data_de_negocio_nao_ha_periodo() -> None:
    candidato, problemas = tradutor.traduzir(linha(proposal_date=None))

    assert candidato is None
    assert CodigoDeIssue.LINHA_ILEGIVEL.value in codigos(problemas)


def test_documento_de_cliente_invalido_nao_barra_a_proposta() -> None:
    candidato, problemas = tradutor.traduzir(linha(cpf_cliente="000"))

    # o dinheiro entrou de qualquer forma: relata, não descarta
    assert candidato is not None
    assert candidato.customer_document is None
    assert por_codigo(problemas, CodigoDeIssue.DOCUMENTO_INVALIDO).severidade is Severidade.ATENCAO


def test_nomes_de_bko_e_finalizacao_ficam_como_texto() -> None:
    candidato, _ = tradutor.traduzir(linha())

    assert candidato is not None
    # a resolução para colaborador é outro passo, com o índice de nomes
    assert candidato.bko_do_legado == "JUCELIA BARBOSA"
    assert candidato.bko_collaborator_legacy_id is None
