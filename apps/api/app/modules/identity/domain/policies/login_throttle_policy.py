"""Política de throttle do login (seção 13.1).

Contagem por e-mail e por IP dentro de uma janela. A política decide; quem conta
é o repositório.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoginThrottlePolicy:
    max_tentativas: int
    janela_em_segundos: int

    def bloqueado(self, tentativas_falhas: int) -> bool:
        return tentativas_falhas >= self.max_tentativas

    def espera_em_segundos(self) -> int:
        return self.janela_em_segundos
