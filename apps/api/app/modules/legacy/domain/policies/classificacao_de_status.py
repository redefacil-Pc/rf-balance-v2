"""Status da proposta a partir do que foi recebido.

Mesma regra que a entidade `Proposal` aplica, aplicada a dado que ainda não é
entidade. Fica numa política própria porque o importador precisa **classificar
sem instanciar** — a linha do legado pode ser justamente a que não passa nas
invariantes do aggregate, e ainda assim precisa aparecer no relatório.
"""

from __future__ import annotations

from app.modules.commercial.domain.policies import settlement_tolerance_policy as tolerancia
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.shared.domain.dinheiro import Dinheiro


def pelo_recebido(*, esperado: Dinheiro, recebido: Dinheiro) -> StatusDaProposta:
    resultado = tolerancia.vigente().classificar(esperado=esperado, recebido=recebido)
    if resultado is not tolerancia.ResultadoDeQuitacao.EM_ABERTO:
        # sobrepagamento também quita; o excedente é sinalizado à parte
        return StatusDaProposta.PAID
    return StatusDaProposta.OPEN if recebido.zerado else StatusDaProposta.PARTIALLY_PAID
