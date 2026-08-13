"""Regra de sobreposição de vigências (ADR-0013).

O MySQL não tem constraint de exclusão por intervalo, então esta é a única
barreira em tempo de escrita. A rotina periódica de integridade existe para
detectar o que escapar por concorrência.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.modules.organization.domain.errors import VigenciaSobrepostaError
from app.shared.domain.date_range import DateRange


def garantir_sem_sobreposicao(
    nova: DateRange, existentes: Iterable[DateRange], *, descricao: str
) -> None:
    for existente in existentes:
        if nova.sobrepoe(existente):
            fim = existente.fim.isoformat() if existente.fim else "sem fim"
            raise VigenciaSobrepostaError(
                f"{descricao} conflita com a vigência de "
                f"{existente.inicio.isoformat()} a {fim}."
            )
