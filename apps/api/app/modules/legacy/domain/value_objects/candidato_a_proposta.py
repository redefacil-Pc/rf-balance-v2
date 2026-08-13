"""Proposta traduzida do legado, ainda **não** persistida.

Guarda lado a lado o que o legado afirma (`comissao_do_legado`, `status_do_legado`)
e o que a v2 calcula. A comparação entre os dois é o relatório de divergência: é
onde regra implícita do v1 aparece, antes de a F4 depender dela.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.shared.domain.dinheiro import Dinheiro
from app.shared.domain.documento import Documento


@dataclass(frozen=True, slots=True)
class CandidatoAProposta:
    #: tabela de origem: `proposals`, `propostas` ou `sales`
    origem: str
    legacy_id: str
    consultant_legacy_id: str
    business_date: date
    operation_amount: Dinheiro
    tps: PercentualTps
    paid_amount: Dinheiro
    #: o que o legado gravou como comissão da empresa
    comissao_do_legado: Dinheiro
    #: o que a v2 calcula a partir de operação e TPS
    comissao_calculada: Dinheiro
    status_do_legado: str
    status_calculado: StatusDaProposta
    external_id: str | None = None
    customer_name: str | None = None
    customer_document: Documento | None = None
    #: nomes digitados no legado; a resolução para colaborador é outro passo
    bko_do_legado: str | None = None
    finalizacao_do_legado: str | None = None
    bko_collaborator_legacy_id: str | None = None
    finalizer_collaborator_legacy_id: str | None = None

    @property
    def divergencia_de_comissao(self) -> Dinheiro:
        return self.comissao_calculada - self.comissao_do_legado
