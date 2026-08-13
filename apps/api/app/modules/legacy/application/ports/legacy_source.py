"""Porta de leitura do sistema atual.

A ACL depende desta interface, nunca de um `SELECT` direto: o mesmo importador
roda contra o dump extraído (CSV) e contra o banco legado, e o tradutor não muda.

A leitura devolve dicionários de strings porque é isso que as duas fontes têm em
comum — converter e validar é responsabilidade do tradutor, que sabe o que cada
campo significa. Fonte é **somente leitura**: o v1 continua sendo a verdade até o
cutover.
"""

from __future__ import annotations

from typing import Protocol

#: uma linha do legado, com os valores ainda crus
LinhaLegada = dict[str, str | None]


class LegacySource(Protocol):
    @property
    def rotulo(self) -> str:
        """Identificação da origem para o relatório — sem credencial."""
        ...

    async def ler(self, tabela: str) -> list[LinhaLegada]:
        """Todas as linhas da tabela. Tabela ausente devolve lista vazia:
        `propostas` e `sales` podem não existir no recorte extraído."""
        ...
