"""Sessão autenticada.

Sessão viva é: não revogada e não expirada. A entidade decide isso — nunca a
camada de API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class Session:
    id: int
    user_id: int
    token_hash: str
    csrf_token: str
    issued_at: datetime
    expires_at: datetime
    last_used_at: datetime
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_reason: str | None = None

    def esta_viva(self, agora: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > agora

    def precisa_rotacionar(self, agora: datetime, intervalo_segundos: int) -> bool:
        referencia = self.rotated_at or self.issued_at
        return agora - referencia >= timedelta(seconds=intervalo_segundos)

    def revogar(self, agora: datetime, motivo: str) -> None:
        if self.revoked_at is None:
            self.revoked_at = agora
            self.revoked_reason = motivo
