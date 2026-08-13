"""Leitura tipada de campo do legado, com issue em vez de exceção.

As três estruturas comerciais do v1 (`proposals`, `propostas`, `sales`) guardam as
mesmas grandezas com nomes diferentes. A conversão é a mesma; o que muda é de
onde o valor vem — por isso ela mora aqui, e não copiada em cada tradutor.

Nenhum método levanta: campo ruim vira issue e `None`. Importador que estoura na
primeira linha torta não produz relatório, e o relatório é o entregável.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.legacy.domain.value_objects.issue import (
    CodigoDeIssue,
    Issue,
    atencao,
    bloqueio,
)
from app.shared.domain.dinheiro import Dinheiro
from app.shared.domain.documento import Documento


class LeitorDeCampos:
    """Converte campos de **uma** linha, acumulando os problemas encontrados."""

    __slots__ = ("_legacy_id", "_origem", "_problemas")

    def __init__(self, origem: str, legacy_id: str, problemas: list[Issue]) -> None:
        self._origem = origem
        self._legacy_id = legacy_id
        self._problemas = problemas

    def dinheiro(self, bruto: str | None, *, campo: str) -> Dinheiro | None:
        if bruto is None:
            return None
        try:
            return Dinheiro(Decimal(bruto))
        except (InvalidOperation, ValueError):
            self._bloquear(
                CodigoDeIssue.VALOR_INVALIDO,
                f"Campo `{campo}` não é um valor monetário: {bruto!r}.",
            )
            return None

    def tps(self, bruto: str | None, *, campo: str) -> PercentualTps | None:
        try:
            return PercentualTps.de(bruto or "")
        except (ValueError, InvalidOperation):
            self._bloquear(
                CodigoDeIssue.VALOR_INVALIDO,
                f"Campo `{campo}` fora de 0 a 100 ou ilegível: {bruto!r}.",
            )
            return None

    def data(self, bruto: str | None, *, campo: str) -> date | None:
        """Aceita `2026-03-10` e `2026-03-10 10:19:34` — o legado usa os dois."""
        if not bruto:
            self._bloquear(
                CodigoDeIssue.LINHA_ILEGIVEL,
                f"Sem `{campo}`: sem data de negócio não há período.",
            )
            return None
        try:
            return datetime.fromisoformat(bruto).date()
        except ValueError:
            self._bloquear(CodigoDeIssue.LINHA_ILEGIVEL, f"Campo `{campo}` ilegível: {bruto!r}.")
            return None

    def documento_do_cliente(self, bruto: str | None) -> Documento | None:
        """Documento de cliente inválido não bloqueia a proposta: o dinheiro entrou
        de qualquer forma. Vira atenção, para alguém corrigir o cadastro."""
        try:
            return Documento.normalizar(bruto or "")
        except ValueError as exc:
            self._problemas.append(
                atencao(
                    self._origem,
                    self._legacy_id,
                    CodigoDeIssue.DOCUMENTO_INVALIDO,
                    f"Documento do cliente não passa na validação: {exc}.",
                )
            )
            return None

    def _bloquear(self, codigo: CodigoDeIssue, detalhe: str) -> None:
        self._problemas.append(bloqueio(self._origem, self._legacy_id, codigo, detalhe))


def texto(bruto: str | None) -> str | None:
    return (bruto or "").strip() or None
