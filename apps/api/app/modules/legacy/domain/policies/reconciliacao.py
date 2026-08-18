"""Reconciliação mínima da migração (seção 18).

Contagem e soma por origem, mais o confronto entre a comissão que o legado gravou
e a que a v2 calcula. É o número que o financeiro confere: se as somas não batem
no dry-run, não existe cutover — e a diferença aparece aqui, agregada, antes de
alguém abrir registro por registro na fila de exceção.

Dinheiro sai como string decimal, como em toda a API.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.modules.legacy.domain.value_objects.candidato_a_proposta import CandidatoAProposta
from app.modules.legacy.domain.value_objects.issue import Issue, Severidade
from app.shared.domain.dinheiro import Dinheiro


@dataclass(frozen=True, slots=True)
class TotaisDaOrigem:
    origem: str
    lidos: int
    traduzidos: int
    operacao: Dinheiro
    comissao_do_legado: Dinheiro
    comissao_calculada: Dinheiro
    por_status: dict[str, int]

    @property
    def divergencia_de_comissao(self) -> Dinheiro:
        return self.comissao_calculada - self.comissao_do_legado

    def para_dicionario(self) -> dict[str, Any]:
        return {
            "lidos": self.lidos,
            "traduzidos": self.traduzidos,
            "nao_traduzidos": self.lidos - self.traduzidos,
            "operacao": str(self.operacao),
            "comissao_do_legado": str(self.comissao_do_legado),
            "comissao_calculada": str(self.comissao_calculada),
            "divergencia_de_comissao": str(self.divergencia_de_comissao),
            "por_status_calculado": self.por_status,
        }


def totalizar(origem: str, *, lidos: int, candidatos: list[CandidatoAProposta]) -> TotaisDaOrigem:
    operacao = Dinheiro.zero()
    comissao_legada = Dinheiro.zero()
    comissao_calculada = Dinheiro.zero()
    status: Counter[str] = Counter()

    for candidato in candidatos:
        operacao = operacao + candidato.operation_amount
        comissao_legada = comissao_legada + candidato.comissao_do_legado
        comissao_calculada = comissao_calculada + candidato.comissao_calculada
        status[candidato.status_calculado.value] += 1

    return TotaisDaOrigem(
        origem=origem,
        lidos=lidos,
        traduzidos=len(candidatos),
        operacao=operacao,
        comissao_do_legado=comissao_legada,
        comissao_calculada=comissao_calculada,
        por_status=dict(sorted(status.items())),
    )


def contar_issues(issues: list[Issue]) -> dict[str, Any]:
    por_codigo: Counter[str] = Counter()
    por_severidade: Counter[str] = Counter()
    for issue in issues:
        por_codigo[issue.codigo.value] += 1
        por_severidade[issue.severidade.value] += 1

    return {
        "total": len(issues),
        "bloqueios": por_severidade.get(Severidade.BLOQUEIO.value, 0),
        "atencoes": por_severidade.get(Severidade.ATENCAO.value, 0),
        "por_codigo": dict(sorted(por_codigo.items())),
    }
