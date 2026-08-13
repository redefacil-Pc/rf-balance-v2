"""Intervalo de vigência, fechado nas duas pontas (ADR-0013).

`[inicio, fim]`, com `fim = None` significando "vigente, sem fim previsto".
Único lugar do sistema que interpreta vigência: nenhuma comparação de data solta
em query de negócio.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class DateRange:
    inicio: date
    fim: date | None = None

    def __post_init__(self) -> None:
        if self.fim is not None and self.fim < self.inicio:
            raise ValueError(f"vigência inválida: fim {self.fim} antes do início {self.inicio}")

    @property
    def aberto(self) -> bool:
        return self.fim is None

    def contem(self, referencia: date) -> bool:
        if referencia < self.inicio:
            return False
        return self.fim is None or referencia <= self.fim

    def sobrepoe(self, outro: DateRange) -> bool:
        """Dois intervalos fechados se sobrepõem quando cada um começa antes do
        fim do outro. Vigência aberta se sobrepõe a tudo que vem depois."""
        depois_do_outro = outro.fim is not None and self.inicio > outro.fim
        antes_do_outro = self.fim is not None and outro.inicio > self.fim
        return not (depois_do_outro or antes_do_outro)

    def encerrar_em(self, novo_inicio: date) -> DateRange:
        """Fecha este intervalo no dia anterior a `novo_inicio`.

        É a operação de transferência da seção 7.3: intervalos fechados não
        admitem duração zero, então o anterior termina em `novo_inicio - 1 dia`.
        """
        fim = novo_inicio - timedelta(days=1)
        if fim < self.inicio:
            raise ValueError(
                f"não é possível encerrar vigência iniciada em {self.inicio} "
                f"para um novo início em {novo_inicio}: geraria intervalo negativo"
            )
        return DateRange(self.inicio, fim)
