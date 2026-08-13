"""Compatibilidade de papéis no vínculo consultor-líder (seção 7.3).

Invariante: "papéis precisam ser compatíveis". Vínculo comercial exige um LIDER
liderando um CONSULTOR — não um BKO liderando um finalizador.
"""

from __future__ import annotations

from collections.abc import Collection

from app.modules.organization.domain.errors import PapelIncompativelError
from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PAPEIS_DE_LIDERANCA,
    PAPEIS_LIDERAVEIS,
    PapelDeColaborador,
)


def garantir_compatibilidade(
    *,
    tipo_de_vinculo: str,
    papeis_do_consultor: Collection[PapelDeColaborador],
    papeis_do_lider: Collection[PapelDeColaborador],
) -> None:
    if tipo_de_vinculo not in PAPEIS_DE_LIDERANCA:
        raise PapelIncompativelError(f"Tipo de vínculo desconhecido: {tipo_de_vinculo}.")

    exigidos_do_lider = PAPEIS_DE_LIDERANCA[tipo_de_vinculo]
    if not exigidos_do_lider.intersection(papeis_do_lider):
        esperados = ", ".join(sorted(exigidos_do_lider))
        raise PapelIncompativelError(
            f"O líder precisa ter, na data de início, um destes papéis: {esperados}."
        )

    exigidos_do_consultor = PAPEIS_LIDERAVEIS[tipo_de_vinculo]
    if not exigidos_do_consultor.intersection(papeis_do_consultor):
        esperados = ", ".join(sorted(exigidos_do_consultor))
        raise PapelIncompativelError(
            f"O liderado precisa ter, na data de início, um destes papéis: {esperados}."
        )
