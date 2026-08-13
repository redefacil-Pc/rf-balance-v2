"""Tipo de coluna para instantes em UTC.

O MySQL grava `DATETIME` sem fuso: sem cuidado, o valor volta do banco como
naive e vira fonte de erro silencioso de uma hora. Este tipo garante que
qualquer instante gravado seja convertido para UTC e que todo valor lido volte
com `tzinfo=UTC`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Dialect
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.types import TypeDecorator, TypeEngine


class UtcDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        # microssegundos precisam ser explícitos no MySQL: DATETIME sem fsp
        # trunca a fração e destrói a ordenação de eventos no mesmo segundo
        if dialect.name == "mysql":
            return dialect.type_descriptor(MYSQL_DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime())

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("instante sem timezone não pode ser persistido")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        instante: datetime = value
        return instante.replace(tzinfo=UTC)
