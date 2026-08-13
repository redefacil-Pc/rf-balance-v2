"""ACL: `proposals` do v1 → candidato a proposta.

Fonte principal do comercial. Duas conferências acontecem aqui e são o coração do
relatório de divergência:

1. **Comissão.** Recalculamos `operação * TPS / 100` e comparamos com
   `valor_total_comissao`. Diferença de centavo denuncia arredondamento diferente;
   diferença maior denuncia regra implícita que ninguém documentou.
2. **Status.** O v1 decide `ABERTA`/`PENDENTE`/`FINALIZADA` no código antigo.
   Recalculamos pela política de tolerância (ADR-0009) e comparamos — proposta que
   o v1 dá como quitada e a v2 não é exatamente o caso que precisa aparecer antes
   do cutover, não depois.

`bko` e `finalizacao` são nomes digitados, não chaves. A resolução para
colaborador acontece fora daqui, com o conjunto de colaboradores já traduzido.
"""

from __future__ import annotations

from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.legacy.application.ports.legacy_source import LinhaLegada
from app.modules.legacy.domain.policies import classificacao_de_status as classificacao
from app.modules.legacy.domain.value_objects.candidato_a_proposta import CandidatoAProposta
from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Issue, atencao, bloqueio
from app.modules.legacy.infrastructure.translators import campos_legados as campos
from app.shared.domain.dinheiro import Dinheiro

ORIGEM = "proposals"

#: acima disto a divergência de comissão deixa de ser arredondamento
TOLERANCIA_DE_ARREDONDAMENTO = Dinheiro.de("0.01")

STATUS_DO_LEGADO = {
    "ABERTA": StatusDaProposta.OPEN,
    "PENDENTE": StatusDaProposta.PARTIALLY_PAID,
    "FINALIZADA": StatusDaProposta.PAID,
}


def traduzir(linha: LinhaLegada) -> tuple[CandidatoAProposta | None, list[Issue]]:
    problemas: list[Issue] = []
    legacy_id = campos.texto(linha.get("id"))

    if legacy_id is None:
        return None, [
            bloqueio(ORIGEM, "?", CodigoDeIssue.LINHA_ILEGIVEL, "Linha sem `id` de origem.")
        ]

    consultor = campos.texto(linha.get("consultant_id"))
    if consultor is None:
        problemas.append(
            bloqueio(
                ORIGEM,
                legacy_id,
                CodigoDeIssue.CONSULTOR_NAO_ENCONTRADO,
                "Proposta sem `consultant_id`.",
            )
        )

    leitor = campos.LeitorDeCampos(ORIGEM, legacy_id, problemas)
    operacao = leitor.dinheiro(linha.get("valor_proposta"), campo="valor_proposta")
    tps = leitor.tps(linha.get("percentual_tps"), campo="percentual_tps")
    data = leitor.data(linha.get("proposal_date"), campo="proposal_date")
    pago = leitor.dinheiro(linha.get("valor_total_pago"), campo="valor_total_pago")
    comissao_legada = leitor.dinheiro(
        linha.get("valor_total_comissao"), campo="valor_total_comissao"
    )

    if consultor is None or operacao is None or tps is None or data is None:
        return None, problemas
    if not operacao.positivo:
        problemas.append(
            bloqueio(
                ORIGEM,
                legacy_id,
                CodigoDeIssue.VALOR_INVALIDO,
                "Valor da operação precisa ser maior que zero.",
                valor=str(operacao),
            )
        )
        return None, problemas

    pago = pago or Dinheiro.zero()
    comissao_legada = comissao_legada or Dinheiro.zero()
    comissao_calculada = tps.aplicar_sobre(operacao)
    status_legado = (campos.texto(linha.get("status")) or "").upper()
    status_calculado = classificacao.pelo_recebido(esperado=comissao_calculada, recebido=pago)

    _conferir_comissao(legacy_id, comissao_calculada, comissao_legada, problemas)
    _conferir_status(legacy_id, status_legado, status_calculado, problemas)

    return (
        CandidatoAProposta(
            origem=ORIGEM,
            legacy_id=legacy_id,
            consultant_legacy_id=consultor,
            business_date=data,
            operation_amount=operacao,
            tps=tps,
            paid_amount=pago,
            comissao_do_legado=comissao_legada,
            comissao_calculada=comissao_calculada,
            status_do_legado=status_legado,
            status_calculado=status_calculado,
            external_id=campos.texto(linha.get("redmine_id")),
            customer_name=campos.texto(linha.get("nome_cliente")),
            customer_document=leitor.documento_do_cliente(linha.get("cpf_cliente")),
            bko_do_legado=campos.texto(linha.get("bko")),
            finalizacao_do_legado=campos.texto(linha.get("finalizacao")),
        ),
        problemas,
    )


def _conferir_comissao(
    legacy_id: str, calculada: Dinheiro, do_legado: Dinheiro, problemas: list[Issue]
) -> None:
    diferenca = calculada - do_legado
    if diferenca.zerado:
        return

    absoluta = diferenca if diferenca.positivo else -diferenca
    detalhe = (
        f"Comissão recalculada ({calculada}) diverge da gravada no legado ({do_legado}) "
        f"em {diferenca}."
    )
    dados = {"calculada": str(calculada), "legado": str(do_legado), "diferenca": str(diferenca)}
    severidade = atencao if absoluta <= TOLERANCIA_DE_ARREDONDAMENTO else bloqueio

    problemas.append(
        severidade(ORIGEM, legacy_id, CodigoDeIssue.COMISSAO_DIVERGENTE, detalhe, **dados)
    )


def _conferir_status(
    legacy_id: str, do_legado: str, calculado: StatusDaProposta, problemas: list[Issue]
) -> None:
    if STATUS_DO_LEGADO.get(do_legado) is calculado:
        return
    problemas.append(
        atencao(
            ORIGEM,
            legacy_id,
            CodigoDeIssue.STATUS_DIVERGENTE,
            f"Status do legado ({do_legado or 'vazio'}) não corresponde ao recalculado "
            f"({calculado}).",
            legado=do_legado or None,
            calculado=calculado.value,
        )
    )
