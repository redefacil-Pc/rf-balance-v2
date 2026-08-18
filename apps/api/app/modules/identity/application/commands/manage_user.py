"""Manutenção de conta: cadastro, papéis, situação e senha provisória.

Quatro comandos no mesmo arquivo porque são a mesma superfície — a tela de
administração de um usuário — e separá-los renderia quatro arquivos de trinta
linhas com as mesmas dependências.

Duas travas contra o erro que deixa o sistema sem dono, ambas sobre a própria
conta do ator: ninguém se desativa e ninguém tira os próprios papéis. Sem elas,
o último administrador consegue se trancar do lado de fora, e a saída seria
mexer no banco à mão.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from app.modules.audit.application.ports.audit_recorder import AuditRecorder
from app.modules.identity.application.ports.password_hasher import PasswordHasher
from app.modules.identity.application.ports.session_cache import SessionCache
from app.modules.identity.domain.errors import (
    AutoAlteracaoProibidaError,
    EmailInvalidoError,
    EmailJaCadastradoError,
    PapelInexistenteError,
    UsuarioNaoEncontradoError,
    UsuarioSemPapelError,
)
from app.modules.identity.domain.policies import password_policy
from app.modules.identity.domain.value_objects.email_address import EmailAddress
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.identity.infrastructure.repositories.sql_session_repository import (
    SqlSessionRepository,
)
from app.modules.identity.infrastructure.repositories.sql_user_repository import SqlUserRepository
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

MODULO = "identity"
_BYTES_DA_SENHA = 12


@dataclass(frozen=True, slots=True)
class UpdateUser:
    user_id: int
    email: str
    full_name: str
    papeis: tuple[str, ...] | None = None
    ativo: bool | None = None
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class SetUserRoles:
    user_id: int
    papeis: tuple[str, ...]
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class SetUserStatus:
    user_id: int
    ativo: bool
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResetUserPassword:
    user_id: int
    #: `None` gera uma provisória. Definida, passa pela mesma política de senha
    #: que vale para todo mundo — administrador não é exceção à regra de força.
    senha: str | None = None
    #: quem administra passa a conhecer a senha em uso, então a troca no próximo
    #: acesso é o padrão. Desligar é decisão consciente, para conta de serviço
    #: ou ambiente de teste.
    exigir_troca: bool = True
    ator: int | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class SenhaRedefinida:
    id: int
    email: str
    #: só volta preenchida quando o sistema gerou. Senha escolhida por quem
    #: administra não é devolvida: quem a definiu já a conhece, e ecoá-la só
    #: acrescentaria uma cópia do segredo em log, cache e histórico de rede.
    senha_provisoria: str | None
    exige_troca: bool


class _BaseDeUsuario:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        users: SqlUserRepository,
        sessions: SqlSessionRepository,
        cache: SessionCache,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._users = users
        self._sessions = sessions
        self._cache = cache
        self._audit = audit
        self._clock = clock

    async def _exigir(self, user_id: int) -> UserModel:
        modelo = await self._users.linha(user_id)
        if modelo is None:
            raise UsuarioNaoEncontradoError(f"Usuário {user_id} não encontrado.")
        return modelo

    async def _revogar_sessoes(self, user_id: int, motivo: str) -> tuple[list[str], int]:
        """Revoga no banco e devolve as chaves de cache a limpar **depois** do
        commit.

        Sem limpar o cache, a mudança de acesso só valeria quando o TTL
        vencesse — e nesse intervalo a conta desativada continua trabalhando com
        os papéis antigos.

        A limpeza fica para depois do commit de propósito: limpar antes abre uma
        janela em que um request concorrente relê o estado ainda não commitado e
        repopula o cache com o valor velho — que então sobreviveria o TTL
        inteiro, exatamente o que se queria evitar. Depois do commit, a pior
        janela é de microssegundos.
        """
        hashes = await self._sessions.token_hashes_vivos(user_id)
        encerradas = await self._sessions.revogar_do_usuario(
            user_id=user_id, quando=self._clock.now(), motivo=motivo
        )
        return hashes, encerradas

    async def _limpar_cache(self, hashes: list[str]) -> None:
        for token_hash in hashes:
            await self._cache.invalidar(token_hash)


class UpdateUserHandler(_BaseDeUsuario):
    async def execute(self, cmd: UpdateUser) -> None:
        modelo = await self._exigir(cmd.user_id)
        email = _normalizar(cmd.email)
        nome = cmd.full_name.strip()

        if await self._users.existe_email(email, exceto=cmd.user_id):
            raise EmailJaCadastradoError(email.valor)

        anteriores_papeis = (await self._users.papeis_de_varios([cmd.user_id])).get(
            cmd.user_id, []
        )
        finais_papeis = anteriores_papeis
        role_ids: list[int] | None = None
        if cmd.papeis is not None:
            if cmd.ator == cmd.user_id:
                raise AutoAlteracaoProibidaError(
                    "Você não pode alterar os próprios papéis. Peça a outro administrador."
                )
            if not cmd.papeis:
                raise UsuarioSemPapelError()
            encontrados = await self._users.papeis_por_codigo(cmd.papeis)
            faltando = sorted(set(cmd.papeis) - set(encontrados))
            if faltando:
                raise PapelInexistenteError(f"Papel não encontrado: {', '.join(faltando)}.")
            finais_papeis = sorted(set(cmd.papeis))
            role_ids = [encontrados[code].id for code in finais_papeis]

        if cmd.ativo is not None and cmd.ator == cmd.user_id and not cmd.ativo:
            raise AutoAlteracaoProibidaError(
                "Você não pode desativar a própria conta. Peça a outro administrador."
            )

        situacao_anterior = modelo.is_active
        anterior = {"email": modelo.email, "full_name": modelo.full_name}
        await self._users.atualizar_cadastro(cmd.user_id, email=email, full_name=nome)
        papeis_mudaram = role_ids is not None and finais_papeis != anteriores_papeis
        situacao_mudou = cmd.ativo is not None and cmd.ativo != situacao_anterior
        if papeis_mudaram and role_ids is not None:
            await self._users.substituir_papeis(cmd.user_id, role_ids)
        if situacao_mudou and cmd.ativo is not None:
            await self._users.definir_situacao(cmd.user_id, ativo=cmd.ativo)

        hashes: list[str] = []
        encerradas = 0
        if papeis_mudaram or (situacao_mudou and cmd.ativo is False):
            hashes, encerradas = await self._revogar_sessoes(
                cmd.user_id, "cadastro de acesso alterado"
            )

        self._audit.registrar(
            module=MODULO,
            action="user.updated",
            actor_user_id=cmd.ator,
            aggregate_type="user",
            aggregate_id=str(cmd.user_id),
            correlation_id=cmd.correlation_id,
            payload={
                "antes": {
                    **anterior,
                    "roles": anteriores_papeis,
                    "is_active": situacao_anterior,
                },
                "depois": {
                    "email": email.valor,
                    "full_name": nome,
                    "roles": finais_papeis,
                    "is_active": cmd.ativo if cmd.ativo is not None else situacao_anterior,
                },
                "sessoes_encerradas": encerradas,
            },
        )
        await self._uow.commit()
        await self._limpar_cache(hashes)


class SetUserRolesHandler(_BaseDeUsuario):
    async def execute(self, cmd: SetUserRoles) -> tuple[str, ...]:
        await self._exigir(cmd.user_id)

        if cmd.ator == cmd.user_id:
            raise AutoAlteracaoProibidaError(
                "Você não pode alterar os próprios papéis. Peça a outro administrador."
            )
        if not cmd.papeis:
            raise UsuarioSemPapelError()

        encontrados = await self._users.papeis_por_codigo(cmd.papeis)
        faltando = sorted(set(cmd.papeis) - set(encontrados))
        if faltando:
            raise PapelInexistenteError(f"Papel não encontrado: {', '.join(faltando)}.")

        anteriores = (await self._users.papeis_de_varios([cmd.user_id])).get(cmd.user_id, [])
        finais = sorted(set(cmd.papeis))
        await self._users.substituir_papeis(cmd.user_id, [encontrados[code].id for code in finais])
        # papel novo só vale na próxima autenticação: a sessão em curso carrega
        # as permissões antigas em cache
        hashes, encerradas = await self._revogar_sessoes(cmd.user_id, "papéis alterados")

        self._audit.registrar(
            module=MODULO,
            action="user.roles_changed",
            actor_user_id=cmd.ator,
            aggregate_type="user",
            aggregate_id=str(cmd.user_id),
            correlation_id=cmd.correlation_id,
            payload={
                "antes": sorted(anteriores),
                "depois": finais,
                "sessoes_encerradas": encerradas,
            },
        )
        await self._uow.commit()
        await self._limpar_cache(hashes)
        return tuple(finais)


class SetUserStatusHandler(_BaseDeUsuario):
    async def execute(self, cmd: SetUserStatus) -> None:
        modelo = await self._exigir(cmd.user_id)

        if cmd.ator == cmd.user_id and not cmd.ativo:
            raise AutoAlteracaoProibidaError(
                "Você não pode desativar a própria conta. Peça a outro administrador."
            )
        if modelo.is_active == cmd.ativo:
            return

        await self._users.definir_situacao(cmd.user_id, ativo=cmd.ativo)
        # desativar sem derrubar sessão deixa a conta trabalhando até o cache
        # vencer — que é justamente o intervalo em que se desativa alguém
        hashes: list[str] = []
        encerradas = 0
        if not cmd.ativo:
            hashes, encerradas = await self._revogar_sessoes(cmd.user_id, "conta desativada")

        self._audit.registrar(
            module=MODULO,
            action="user.activated" if cmd.ativo else "user.deactivated",
            actor_user_id=cmd.ator,
            aggregate_type="user",
            aggregate_id=str(cmd.user_id),
            correlation_id=cmd.correlation_id,
            payload={"email": modelo.email, "sessoes_encerradas": encerradas},
        )
        await self._uow.commit()
        await self._limpar_cache(hashes)


class ResetUserPasswordHandler(_BaseDeUsuario):
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        users: SqlUserRepository,
        sessions: SqlSessionRepository,
        cache: SessionCache,
        hasher: PasswordHasher,
        audit: AuditRecorder,
        clock: Clock,
    ) -> None:
        super().__init__(
            uow=uow, users=users, sessions=sessions, cache=cache, audit=audit, clock=clock
        )
        self._hasher = hasher

    async def execute(self, cmd: ResetUserPassword) -> SenhaRedefinida:
        modelo = await self._exigir(cmd.user_id)

        gerada = cmd.senha is None
        if gerada:
            senha = secrets.token_urlsafe(_BYTES_DA_SENHA)
        else:
            senha = cmd.senha or ""
            # a política é a mesma de qualquer troca de senha: quem administra
            # não pode instalar uma senha que o próprio sistema recusaria
            password_policy.validar(senha)

        await self._users.definir_senha(
            cmd.user_id,
            novo_hash=self._hasher.gerar(senha),
            exigir_troca=cmd.exigir_troca,
        )
        # senha trocada por administrador costuma ser resposta a conta
        # comprometida: manter a sessão antiga viva anularia o motivo do reset
        hashes, encerradas = await self._revogar_sessoes(cmd.user_id, "senha redefinida")

        self._audit.registrar(
            module=MODULO,
            action="user.password_reset",
            actor_user_id=cmd.ator,
            aggregate_type="user",
            aggregate_id=str(cmd.user_id),
            correlation_id=cmd.correlation_id,
            # como a senha foi definida importa para auditoria; a senha em si
            # não entra aqui em hipótese alguma
            payload={
                "email": modelo.email,
                "origem": "gerada" if gerada else "definida_pelo_administrador",
                "exige_troca": cmd.exigir_troca,
                "sessoes_encerradas": encerradas,
            },
        )
        await self._uow.commit()
        await self._limpar_cache(hashes)

        return SenhaRedefinida(
            id=cmd.user_id,
            email=modelo.email,
            senha_provisoria=senha if gerada else None,
            exige_troca=cmd.exigir_troca,
        )


def _normalizar(bruto: str) -> EmailAddress:
    try:
        return EmailAddress.normalizar(bruto)
    except ValueError as exc:
        raise EmailInvalidoError(str(exc)) from exc
