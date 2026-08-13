"""ACL: `propostas` do v1 → candidato de **staging**, nunca proposta canônica.

Estrutura paralela a `proposals`, com nomes que parecem os mesmos e não são
(`valor_venda`, `valor_comissao_empresa`, `tps`, `data_venda`). Não guarda
cliente, então nem existe documento por onde deduplicar com segurança.

Traduzimos para poder **comparar e relatar** — a promoção a proposta canônica
depende de decisão humana. O importador não escolhe entre estruturas duplicadas
(seção 18).
"""

from __future__ import annotations

from app.modules.legacy.application.ports.legacy_source import LinhaLegada
from app.modules.legacy.domain.policies import classificacao_de_status as classificacao
from app.modules.legacy.domain.value_objects.candidato_a_proposta import CandidatoAProposta
from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Issue, bloqueio
from app.modules.legacy.infrastructure.translators import campos_legados as campos
from app.shared.domain.dinheiro import Dinheiro

ORIGEM = "propostas"


def traduzir(linha: LinhaLegada) -> tuple[CandidatoAProposta | None, list[Issue]]:
    problemas: list[Issue] = []
    legacy_id = campos.texto(linha.get("id"))

    if legacy_id is None:
        return None, [
            bloqueio(ORIGEM, "?", CodigoDeIssue.LINHA_ILEGIVEL, "Linha sem `id` de origem.")
        ]

    leitor = campos.LeitorDeCampos(ORIGEM, legacy_id, problemas)
    consultor = campos.texto(linha.get("consultor_id"))
    operacao = leitor.dinheiro(linha.get("valor_venda"), campo="valor_venda")
    tps = leitor.tps(linha.get("tps"), campo="tps")
    data = leitor.data(linha.get("data_venda"), campo="data_venda")
    comissao_legada = leitor.dinheiro(
        linha.get("valor_comissao_empresa"), campo="valor_comissao_empresa"
    )

    if consultor is None:
        problemas.append(
            bloqueio(
                ORIGEM,
                legacy_id,
                CodigoDeIssue.CONSULTOR_NAO_ENCONTRADO,
                "Registro sem `consultor_id`.",
            )
        )
    if consultor is None or operacao is None or tps is None or data is None:
        return None, problemas

    comissao_legada = comissao_legada or Dinheiro.zero()
    # `propostas` não registra pagamento: o status vem do legado, não de recebido
    status_legado = (campos.texto(linha.get("status")) or "").upper()

    return (
        CandidatoAProposta(
            origem=ORIGEM,
            legacy_id=legacy_id,
            consultant_legacy_id=consultor,
            business_date=data,
            operation_amount=operacao,
            tps=tps,
            paid_amount=Dinheiro.zero(),
            comissao_do_legado=comissao_legada,
            comissao_calculada=tps.aplicar_sobre(operacao),
            status_do_legado=status_legado,
            status_calculado=classificacao.pelo_recebido(
                esperado=tps.aplicar_sobre(operacao), recebido=Dinheiro.zero()
            ),
        ),
        problemas,
    )
