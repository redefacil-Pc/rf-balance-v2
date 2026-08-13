"""Issue de importação: o que o importador **não** resolveu sozinho.

O importador não escolhe entre estruturas duplicadas nem adivinha a pessoa por
trás de um nome digitado (seção 18). Tudo o que exige decisão humana vira uma
issue com origem, id legado e motivo — é a fila de exceção, e é o que o relatório
de divergência mostra ao negócio antes de qualquer carga real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Severidade(StrEnum):
    #: o registro não pode ser importado como está
    BLOQUEIO = "BLOQUEIO"
    #: importa, mas com campo em branco, aproximado ou divergente do legado
    ATENCAO = "ATENCAO"


class CodigoDeIssue(StrEnum):
    DOCUMENTO_INVALIDO = "documento-invalido"
    DOCUMENTO_DUPLICADO = "documento-duplicado"
    CONSULTOR_NAO_ENCONTRADO = "consultor-nao-encontrado"
    VALOR_INVALIDO = "valor-invalido"
    COMISSAO_DIVERGENTE = "comissao-divergente"
    STATUS_DIVERGENTE = "status-divergente"
    PAPEL_DESCONHECIDO = "papel-desconhecido"
    VIGENCIA_PRESUMIDA = "vigencia-presumida"
    PARTICIPANTE_NAO_RESOLVIDO = "participante-nao-resolvido"
    REDMINE_DUPLICADO = "redmine-duplicado"
    EMPRESA_DO_CONSULTOR_SEM_DESTINO = "empresa-do-consultor-sem-destino"
    ESTRUTURA_DUPLICADA = "estrutura-duplicada"
    LINHA_ILEGIVEL = "linha-ilegivel"


@dataclass(frozen=True, slots=True)
class Issue:
    origem: str
    legacy_id: str
    codigo: CodigoDeIssue
    severidade: Severidade
    detalhe: str
    #: contexto para quem for decidir — sem PII crua
    dados: dict[str, Any] = field(default_factory=dict)

    @property
    def bloqueia(self) -> bool:
        return self.severidade is Severidade.BLOQUEIO


def bloqueio(
    origem: str,
    legacy_id: str,
    codigo: CodigoDeIssue,
    detalhe: str,
    **dados: Any,
) -> Issue:
    return Issue(origem, legacy_id, codigo, Severidade.BLOQUEIO, detalhe, dados)


def atencao(
    origem: str,
    legacy_id: str,
    codigo: CodigoDeIssue,
    detalhe: str,
    **dados: Any,
) -> Issue:
    return Issue(origem, legacy_id, codigo, Severidade.ATENCAO, detalhe, dados)
