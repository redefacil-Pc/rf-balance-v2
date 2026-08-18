"""ACL: `sales` do v1 → candidato de **staging**, nunca proposta canônica.

Terceira estrutura comercial paralela. Tem cliente (`cpf`, `nome`) e um
`valor_comissionavel` que **não é** a comissão da empresa: é a base sobre a qual
se comissiona. Tratá-lo como `company_commission_amount` inflaria a comissão de
toda venda importada — por isso ele viaja como valor do legado e a comparação com
o recalculado fica explícita no relatório.

`vendedor` é nome digitado e coexiste com `consultant_id`; quando os dois
divergem, quem decide é gente, não o importador.
"""

from __future__ import annotations

from app.modules.legacy.application.ports.legacy_source import LinhaLegada
from app.modules.legacy.domain.policies import classificacao_de_status as classificacao
from app.modules.legacy.domain.value_objects.candidato_a_proposta import CandidatoAProposta
from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Issue, bloqueio
from app.modules.legacy.infrastructure.translators import campos_legados as campos
from app.shared.domain.dinheiro import Dinheiro

ORIGEM = "sales"


def traduzir(linha: LinhaLegada) -> tuple[CandidatoAProposta | None, list[Issue]]:
    problemas: list[Issue] = []
    legacy_id = campos.texto(linha.get("id"))

    if legacy_id is None:
        return None, [
            bloqueio(ORIGEM, "?", CodigoDeIssue.LINHA_ILEGIVEL, "Linha sem `id` de origem.")
        ]

    leitor = campos.LeitorDeCampos(ORIGEM, legacy_id, problemas)
    consultor = campos.texto(linha.get("consultant_id"))
    operacao = leitor.dinheiro(linha.get("valor_operacao"), campo="valor_operacao")
    tps = leitor.tps(linha.get("tps_percentage"), campo="tps_percentage")
    data = leitor.data(linha.get("data_pag"), campo="data_pag")
    comissionavel = leitor.dinheiro(linha.get("valor_comissionavel"), campo="valor_comissionavel")

    if consultor is None:
        problemas.append(
            bloqueio(
                ORIGEM,
                legacy_id,
                CodigoDeIssue.CONSULTOR_NAO_ENCONTRADO,
                "Venda sem `consultant_id`.",
            )
        )
    if consultor is None or operacao is None or tps is None or data is None:
        return None, problemas

    comissao_calculada = tps.aplicar_sobre(operacao)

    return (
        CandidatoAProposta(
            origem=ORIGEM,
            legacy_id=legacy_id,
            consultant_legacy_id=consultor,
            business_date=data,
            operation_amount=operacao,
            tps=tps,
            paid_amount=Dinheiro.zero(),
            comissao_do_legado=comissionavel or Dinheiro.zero(),
            comissao_calculada=comissao_calculada,
            status_do_legado="ATIVA" if campos.texto(linha.get("is_active")) == "1" else "INATIVA",
            status_calculado=classificacao.pelo_recebido(
                esperado=comissao_calculada, recebido=Dinheiro.zero()
            ),
            customer_name=campos.texto(linha.get("nome")),
            customer_document=leitor.documento_do_cliente(linha.get("cpf")),
        ),
        problemas,
    )
