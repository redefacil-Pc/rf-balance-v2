"""Defaults de timestamp no servidor.

Escritos exatamente como o MySQL os reporta em `information_schema`. Usar
`func.now(6)` aqui funcionaria, mas renderiza `now(6)` e faz o `alembic check`
detectar drift falso em toda migração seguinte.
"""

from __future__ import annotations

from sqlalchemy import text

AGORA = text("CURRENT_TIMESTAMP(6)")
AGORA_COM_ON_UPDATE = text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)")
