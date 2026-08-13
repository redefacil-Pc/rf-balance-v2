"""Resolver `bko` e `finalizacao` — nomes digitados — para colaborador.

No v1 esses campos são texto livre, não chave estrangeira. Casar nome com pessoa
é o passo mais frágil da importação: nome tem homônimo, acento inconsistente,
espaço a mais e abreviação.

A regra é deliberadamente conservadora: **só resolve quando há exatamente uma
correspondência** pelo nome normalizado. Nenhuma, ou mais de uma, o campo fica
vazio e vai para a fila de exceção. Comissão de BKO e de finalização sai desses
campos na F4 — atribuir à pessoa errada é pagar a pessoa errada.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict

from app.modules.legacy.domain.value_objects.candidato_a_colaborador import CandidatoAColaborador


def normalizar(nome: str) -> str:
    """Ignora acento, caixa e espaço repetido — não ignora nome diferente."""
    sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", nome)
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(sem_acento.upper().split())


class IndiceDeColaboradores:
    """Índice por nome normalizado, guardando as ambiguidades em vez de escondê-las."""

    __slots__ = ("_por_nome",)

    def __init__(self, colaboradores: list[CandidatoAColaborador]) -> None:
        indice: dict[str, list[str]] = defaultdict(list)
        for colaborador in colaboradores:
            indice[normalizar(colaborador.full_name)].append(colaborador.legacy_id)
        self._por_nome = dict(indice)

    def resolver(self, nome: str | None) -> tuple[str | None, str | None]:
        """Devolve (legacy_id, motivo da não resolução)."""
        if not nome:
            return None, None

        encontrados = self._por_nome.get(normalizar(nome), [])
        if len(encontrados) == 1:
            return encontrados[0], None
        if not encontrados:
            return None, f"Nenhum colaborador com o nome {nome!r}."
        return None, f"{len(encontrados)} colaboradores com o nome {nome!r}: ambíguo."
