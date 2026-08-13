"""Colaborador traduzido do legado, ainda **não** persistido.

Candidato, e não entidade: em dry-run nada disso vira linha em `collaborators`.
O tipo existe para que o relatório e a futura carga da F7 falem do mesmo objeto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.organization.domain.value_objects.papel_de_colaborador import PapelDeColaborador
from app.shared.domain.documento import Documento


@dataclass(frozen=True, slots=True)
class CandidatoAColaborador:
    legacy_id: str
    full_name: str
    documento: Documento
    is_active: bool
    #: nulo quando o `role` do legado não está no catálogo canônico
    papel: PapelDeColaborador | None
    #: derivado de `created_at` — o legado não guarda início de vigência
    valid_from: date
    unidade: str | None
    tipo_de_chave_pix: str | None
    chave_pix: str | None
    #: razão social do MEI do próprio colaborador; sem destino canônico definido
    empresa_do_legado: str | None
