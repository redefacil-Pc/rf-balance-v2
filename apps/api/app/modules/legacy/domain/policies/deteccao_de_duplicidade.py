"""Duplicidade entre as três estruturas comerciais do v1.

`proposals`, `propostas` e `sales` guardam a mesma venda de formas diferentes, e
`propostas` sequer registra o cliente. A única chave comparável entre as três é
**(consultor, data de negócio, valor da operação)**.

Coincidiu, é candidata a duplicata: as duas origens vão para a fila de exceção
com os ids, e alguém decide qual é a boa. Não coincidiu, o registro paralelo
continua órfão — e órfão também é exceção, porque significa venda que existe numa
estrutura e não na outra.

Em nenhum dos dois casos o importador promove `propostas` ou `sales` a proposta
canônica: escolher sozinho entre estruturas duplicadas é como o dado financeiro
se corrompe em silêncio (seção 18).
"""

from __future__ import annotations

from collections import defaultdict

from app.modules.legacy.domain.value_objects.candidato_a_proposta import CandidatoAProposta
from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Issue, atencao

#: a estrutura que é fonte principal; as outras são paralelas
ORIGEM_PRINCIPAL = "proposals"

Chave = tuple[str, str, str]


def _chave(candidato: CandidatoAProposta) -> Chave:
    return (
        candidato.consultant_legacy_id,
        candidato.business_date.isoformat(),
        str(candidato.operation_amount),
    )


def detectar(
    principais: list[CandidatoAProposta], paralelos: list[CandidatoAProposta]
) -> list[Issue]:
    """Compara as estruturas paralelas com a principal e devolve as exceções."""
    indice: dict[Chave, list[CandidatoAProposta]] = defaultdict(list)
    for candidato in principais:
        indice[_chave(candidato)].append(candidato)

    problemas: list[Issue] = []
    for paralelo in paralelos:
        correspondentes = indice.get(_chave(paralelo), [])
        problemas.append(_issue(paralelo, correspondentes))
    return problemas


def _issue(paralelo: CandidatoAProposta, correspondentes: list[CandidatoAProposta]) -> Issue:
    contexto = {
        "consultant_legacy_id": paralelo.consultant_legacy_id,
        "business_date": paralelo.business_date.isoformat(),
        "operation_amount": str(paralelo.operation_amount),
    }

    if not correspondentes:
        return atencao(
            paralelo.origem,
            paralelo.legacy_id,
            CodigoDeIssue.ESTRUTURA_DUPLICADA,
            f"Registro de `{paralelo.origem}` sem correspondente em `{ORIGEM_PRINCIPAL}` "
            "por (consultor, data, valor): pode ser venda que só existe na estrutura "
            "paralela. Não importado.",
            **contexto,
        )

    ids = [candidato.legacy_id for candidato in correspondentes]
    return atencao(
        paralelo.origem,
        paralelo.legacy_id,
        CodigoDeIssue.ESTRUTURA_DUPLICADA,
        f"Registro de `{paralelo.origem}` coincide com {len(ids)} de `{ORIGEM_PRINCIPAL}` "
        f"(ids {', '.join(ids)}) por (consultor, data, valor). Qual é a boa é decisão "
        "humana; nada foi importado desta origem.",
        correspondentes=ids,
        **contexto,
    )
