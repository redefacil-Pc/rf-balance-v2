"""Erros de domínio do módulo de identidade.

`InvalidCredentialsError` é deliberadamente genérico: a resposta não revela se o
e-mail existe, se a senha está errada ou se a conta está inativa. A distinção
fica no log e em `login_attempts`, não na API.
"""

from __future__ import annotations

from app.platform.errors.domain_error import DomainError


class InvalidCredentialsError(DomainError):
    status = 401
    code = "invalid-credentials"
    title = "Credenciais inválidas"

    def __init__(self) -> None:
        super().__init__("E-mail ou senha inválidos.")


class TooManyAttemptsError(DomainError):
    status = 429
    code = "too-many-attempts"
    title = "Tentativas excedidas"

    def __init__(self, segundos: int) -> None:
        super().__init__(f"Muitas tentativas. Tente novamente em {segundos} segundos.")
        self.segundos = segundos


class SessionInvalidError(DomainError):
    status = 401
    code = "session-invalid"
    title = "Sessão inválida"

    def __init__(self, detalhe: str = "Sessão expirada ou revogada.") -> None:
        super().__init__(detalhe)


class WeakPasswordError(DomainError):
    status = 422
    code = "weak-password"
    title = "Senha fraca"


class UsuarioNaoEncontradoError(DomainError):
    status = 404
    code = "usuario-nao-encontrado"
    title = "Usuário não encontrado"


class EmailJaCadastradoError(DomainError):
    status = 409
    code = "email-ja-cadastrado"
    title = "E-mail já cadastrado"

    def __init__(self, email: str) -> None:
        super().__init__(f"Já existe um usuário com o e-mail {email}.")


class EmailInvalidoError(DomainError):
    status = 422
    code = "email-invalido"
    title = "E-mail inválido"


class PapelInexistenteError(DomainError):
    status = 422
    code = "papel-inexistente"
    title = "Papel inexistente"


class UsuarioSemPapelError(DomainError):
    status = 422
    code = "usuario-sem-papel"
    title = "Usuário sem papel"

    def __init__(self) -> None:
        # conta sem papel loga e não enxerga nada: erro de cadastro que só
        # aparece quando a pessoa tenta usar o sistema
        super().__init__("Atribua ao menos um papel ao usuário.")


class AutoAlteracaoProibidaError(DomainError):
    status = 409
    code = "auto-alteracao-proibida"
    title = "Operação sobre a própria conta"

    def __init__(self, detalhe: str) -> None:
        super().__init__(detalhe)
