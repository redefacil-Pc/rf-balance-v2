"""Fonte CSV: um arquivo por tabela legada, num diretório.

É a fonte padrão porque a extração fica sendo um passo separado e auditável — o
arquivo lido hoje é o mesmo que se relê amanhã para explicar uma divergência.
Também é o que permite testar o importador sem acesso ao banco de produção.

Convenção: `<diretorio>/<tabela>.csv`, com cabeçalho igual ao nome das colunas do
legado. Campo vazio vira `None`, não string vazia: no legado a diferença entre
"não preenchido" e "preenchido com nada" não é confiável, e tratar os dois como
ausente evita decisão silenciosa.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.modules.legacy.application.ports.legacy_source import LinhaLegada

#: onde o DictReader joga colunas além do cabeçalho — descartadas na leitura
COLUNAS_EXTRAS = "__extras__"


class CsvLegacySource:
    __slots__ = ("_diretorio",)

    def __init__(self, diretorio: Path) -> None:
        self._diretorio = diretorio

    @property
    def rotulo(self) -> str:
        return f"csv:{self._diretorio}"

    async def ler(self, tabela: str) -> list[LinhaLegada]:
        arquivo = self._diretorio / f"{tabela}.csv"
        if not arquivo.is_file():
            return []

        with arquivo.open(encoding="utf-8", newline="") as origem:
            # `restkey` nomeia as colunas a mais em vez de deixá-las sob a chave
            # `None`, que é o padrão do DictReader e complica o consumo depois
            leitor = csv.DictReader(origem, restkey=COLUNAS_EXTRAS)
            return [self._normalizar(linha) for linha in leitor]

    @staticmethod
    def _normalizar(linha: dict[str, str | None]) -> LinhaLegada:
        normalizada: LinhaLegada = {}
        for chave, valor in linha.items():
            if chave == COLUNAS_EXTRAS:
                continue
            texto = (valor or "").strip()
            # `NULL` literal aparece em dump exportado por ferramenta gráfica
            normalizada[chave] = None if texto in ("", "NULL", "\\N") else texto
        return normalizada
