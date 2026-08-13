"""CPF e CNPJ: normalização e validação de dígito verificador.

Documento inválido barrado na entrada evita duplicidade e trabalho manual de
correção depois — e a unicidade do cadastro depende de o valor estar normalizado
antes de virar hash (ADR-0012).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TipoDeDocumento(StrEnum):
    CPF = "CPF"
    CNPJ = "CNPJ"


@dataclass(frozen=True, slots=True)
class Documento:
    """Guarda apenas dígitos. A formatação é responsabilidade da apresentação."""

    digitos: str
    tipo: TipoDeDocumento

    @classmethod
    def normalizar(cls, bruto: str) -> Documento:
        digitos = "".join(caractere for caractere in bruto if caractere.isdigit())

        if len(digitos) == 11:
            if not _cpf_valido(digitos):
                raise ValueError("CPF inválido")
            return cls(digitos, TipoDeDocumento.CPF)

        if len(digitos) == 14:
            if not _cnpj_valido(digitos):
                raise ValueError("CNPJ inválido")
            return cls(digitos, TipoDeDocumento.CNPJ)

        raise ValueError("documento deve ter 11 dígitos (CPF) ou 14 (CNPJ)")

    def mascarado(self) -> str:
        """Mostra só o suficiente para o operador reconhecer o cadastro."""
        if self.tipo is TipoDeDocumento.CPF:
            return f"***.***.{self.digitos[6:9]}-{self.digitos[9:]}"
        return f"**.***.{self.digitos[5:8]}/{self.digitos[8:12]}-{self.digitos[12:]}"

    def formatado(self) -> str:
        d = self.digitos
        if self.tipo is TipoDeDocumento.CPF:
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"

    def __str__(self) -> str:
        return self.digitos


def _cpf_valido(digitos: str) -> bool:
    if digitos == digitos[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho))
        resto = (soma * 10) % 11
        esperado = 0 if resto == 10 else resto
        if esperado != int(digitos[tamanho]):
            return False
    return True


def _cnpj_valido(digitos: str) -> bool:
    if digitos == digitos[0] * 14:
        return False
    pesos_primeiro = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_segundo = [6, *pesos_primeiro]
    for pesos, posicao in ((pesos_primeiro, 12), (pesos_segundo, 13)):
        soma = sum(int(digitos[i]) * pesos[i] for i in range(posicao))
        resto = soma % 11
        esperado = 0 if resto < 2 else 11 - resto
        if esperado != int(digitos[posicao]):
            return False
    return True
