"""Sincronização do RBAC: o catálogo em código é a fonte da verdade.

Permissões, papéis e a composição entre eles são **estrutura derivada do
código**, não dado operacional. Precisam bater com o catálogo do mesmo jeito que
o schema precisa bater com a migração — e pelo mesmo motivo: divergência aqui
não estoura, ela nega acesso em silêncio. Um deploy que acrescenta
`proposals:approve` ao catálogo e não sincroniza deixa a aprovação devolvendo
403 para todo mundo, sem nada no log dizendo o porquê.

Por isso a sincronização vive separada da semeadura de usuários: usuário é dado
(nasce uma vez, tem senha, muda pela tela), permissão é estrutura (tem que ser
reaplicada a cada deploy). Estavam juntas, e era preciso rodar o seed de
usuários para corrigir uma permissão.

O que a sincronização faz e o que deliberadamente não faz:

- **Cria** permissão e papel que o catálogo declara e o banco não tem.
- **Reconcilia** a composição papel↔permissão nos dois sentidos: concede o que
  falta e **revoga o que o catálogo não declara mais**. Só adicionar deixaria
  uma permissão removida do código continuar valendo no banco — que é uma falha
  de segurança silenciosa, não um detalhe.
- **Não apaga** linha de `permissions` nem de `roles` que sumiu do catálogo:
  pode haver usuário vinculado, e derrubar acesso de gente é decisão de operador,
  não efeito colateral de deploy. O item obsoleto é **reportado** para alguém
  decidir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.permission_catalog import (
    NOMES_DOS_PAPEIS,
    PAPEIS,
    PERMISSOES,
)
from app.modules.identity.infrastructure.models.permission_model import PermissionModel
from app.modules.identity.infrastructure.models.role_model import RoleModel
from app.modules.identity.infrastructure.models.role_permission_model import RolePermissionModel
from app.modules.identity.infrastructure.models.user_role_model import UserRoleModel


@dataclass(frozen=True, slots=True)
class Divergencia:
    """O que o catálogo declara e o banco não reflete."""

    permissoes_faltando: tuple[str, ...] = ()
    papeis_faltando: tuple[str, ...] = ()
    #: (papel, permissão) que o catálogo concede e o banco não
    concessoes_faltando: tuple[tuple[str, str], ...] = ()
    #: (papel, permissão) que o banco concede e o catálogo não declara mais
    concessoes_a_mais: tuple[tuple[str, str], ...] = ()

    @property
    def sincronizado(self) -> bool:
        return not (
            self.permissoes_faltando
            or self.papeis_faltando
            or self.concessoes_faltando
            or self.concessoes_a_mais
        )

    def resumo(self) -> str:
        if self.sincronizado:
            return ""
        partes: list[str] = []
        if self.permissoes_faltando:
            partes.append(f"permissões ausentes: {', '.join(self.permissoes_faltando)}")
        if self.papeis_faltando:
            partes.append(f"papéis ausentes: {', '.join(self.papeis_faltando)}")
        if self.concessoes_faltando:
            pares = ", ".join(f"{p}->{c}" for p, c in self.concessoes_faltando)
            partes.append(f"concessões ausentes: {pares}")
        if self.concessoes_a_mais:
            pares = ", ".join(f"{p}->{c}" for p, c in self.concessoes_a_mais)
            partes.append(f"concessões indevidas: {pares}")
        return "; ".join(partes)


@dataclass(slots=True)
class RelatorioDeSincronizacao:
    permissoes_criadas: list[str] = field(default_factory=list)
    descricoes_atualizadas: list[str] = field(default_factory=list)
    papeis_criados: list[str] = field(default_factory=list)
    nomes_atualizados: list[str] = field(default_factory=list)
    concessoes_adicionadas: list[tuple[str, str]] = field(default_factory=list)
    concessoes_revogadas: list[tuple[str, str]] = field(default_factory=list)
    #: existem no banco e sumiram do catálogo — não são apagados aqui
    permissoes_obsoletas: list[str] = field(default_factory=list)
    papeis_obsoletos: list[str] = field(default_factory=list)

    @property
    def mudou(self) -> bool:
        return bool(
            self.permissoes_criadas
            or self.descricoes_atualizadas
            or self.papeis_criados
            or self.nomes_atualizados
            or self.concessoes_adicionadas
            or self.concessoes_revogadas
        )

    def mensagens(self) -> list[str]:
        linhas = [
            f"permissões: {len(self.permissoes_criadas)} criadas, "
            f"{len(self.descricoes_atualizadas)} redescritas",
            f"papéis: {len(self.papeis_criados)} criados, {len(self.nomes_atualizados)} renomeados",
            f"concessões: {len(self.concessoes_adicionadas)} adicionadas, "
            f"{len(self.concessoes_revogadas)} revogadas",
        ]
        for papel, permissao in self.concessoes_revogadas:
            linhas.append(f"  revogado {papel} -> {permissao}")
        if self.permissoes_obsoletas:
            linhas.append(
                "permissões obsoletas no banco (não removidas automaticamente): "
                + ", ".join(sorted(self.permissoes_obsoletas))
            )
        if self.papeis_obsoletos:
            linhas.append(
                "papéis obsoletos no banco (não removidos automaticamente, "
                "podem ter usuário vinculado): " + ", ".join(sorted(self.papeis_obsoletos))
            )
        return linhas


@dataclass(slots=True)
class RelatorioDePurga:
    removidos: list[str] = field(default_factory=list)
    #: papel obsoleto que ficou por ter conta vinculada, com quantas contas
    mantidos_em_uso: list[tuple[str, int]] = field(default_factory=list)

    def mensagens(self) -> list[str]:
        linhas: list[str] = []
        if self.removidos:
            linhas.append(f"papéis obsoletos removidos: {', '.join(sorted(self.removidos))}")
        else:
            linhas.append("nenhum papel obsoleto para remover")
        for papel, quantos in sorted(self.mantidos_em_uso):
            linhas.append(
                f"  {papel} mantido: {quantos} conta(s) ainda o usam. "
                "Migre essas contas para um papel do catálogo e rode de novo."
            )
        return linhas


async def purgar_obsoletos(session: AsyncSession) -> RelatorioDePurga:
    """Remove do banco os papéis que sumiram do catálogo.

    Ação explícita de operador, fora da sincronização automática: `sincronizar`
    preserva papel obsoleto de propósito, porque tirar acesso de alguém não pode
    ser efeito colateral de deploy. Aqui é o oposto — alguém decidiu.

    Invariante que torna a operação segura em qualquer ambiente: **papel com
    conta vinculada nunca é removido**. Removê-lo deixaria a pessoa logando e
    sem enxergar nada, que é um estado pior que o papel obsoleto — o sintoma
    seria "o sistema abriu vazio", sem pista da causa. Esses são reportados para
    a conta ser migrada primeiro.
    """
    relatorio = RelatorioDePurga()

    papeis = {r.code: r for r in (await session.scalars(select(RoleModel))).all()}
    obsoletos = {code: r for code, r in papeis.items() if code not in PAPEIS}
    if not obsoletos:
        return relatorio

    linhas_em_uso = (
        await session.execute(
            select(UserRoleModel.role_id, func.count())
            .where(UserRoleModel.role_id.in_([r.id for r in obsoletos.values()]))
            .group_by(UserRoleModel.role_id)
        )
    ).all()
    em_uso: dict[int, int] = {int(role_id): int(total) for role_id, total in linhas_em_uso}

    for code, papel in obsoletos.items():
        contas = int(em_uso.get(papel.id, 0))
        if contas:
            relatorio.mantidos_em_uso.append((code, contas))
            continue
        await session.execute(
            delete(RolePermissionModel).where(RolePermissionModel.role_id == papel.id)
        )
        await session.execute(delete(RoleModel).where(RoleModel.id == papel.id))
        relatorio.removidos.append(code)

    await session.flush()
    return relatorio


async def sincronizar(session: AsyncSession) -> RelatorioDeSincronizacao:
    """Aplica o catálogo no banco. Idempotente: rodar de novo não muda nada."""
    relatorio = RelatorioDeSincronizacao()

    permissoes = await _sincronizar_permissoes(session, relatorio)
    papeis = await _sincronizar_papeis(session, relatorio)
    await session.flush()
    await _sincronizar_concessoes(session, permissoes, papeis, relatorio)
    await session.flush()

    return relatorio


async def verificar(session: AsyncSession) -> Divergencia:
    """Leitura pura, para o readiness. Não escreve nada."""
    permissoes = {p.code: p for p in (await session.scalars(select(PermissionModel))).all()}
    papeis = {r.code: r for r in (await session.scalars(select(RoleModel))).all()}

    por_id = {p.id: code for code, p in permissoes.items()}
    papel_por_id = {r.id: code for code, r in papeis.items()}
    concedidas = {
        (papel_por_id[rp.role_id], por_id[rp.permission_id])
        for rp in (await session.scalars(select(RolePermissionModel))).all()
        if rp.role_id in papel_por_id and rp.permission_id in por_id
    }

    esperadas = {
        (papel, permissao)
        for papel, permissoes_do_papel in PAPEIS.items()
        for permissao in permissoes_do_papel
    }
    # só cobra concessão de papel que existe: papel ausente já é reportado à parte
    conhecidas = {par for par in esperadas if par[0] in papeis and par[1] in permissoes}

    # Papel obsoleto guarda as concessões dele por decisão de `sincronizar` —
    # apagar tiraria acesso de quem ainda o tem. O readiness precisa aplicar a
    # mesma régra, senão acusa como divergência algo que a sincronização nunca
    # vai resolver, e fica vermelho para sempre.
    sobrando = {par for par in concedidas - esperadas if par[0] in PAPEIS}

    return Divergencia(
        permissoes_faltando=tuple(sorted(set(PERMISSOES) - set(permissoes))),
        papeis_faltando=tuple(sorted(set(PAPEIS) - set(papeis))),
        concessoes_faltando=tuple(sorted(conhecidas - concedidas)),
        concessoes_a_mais=tuple(sorted(sobrando)),
    )


async def _sincronizar_permissoes(
    session: AsyncSession, relatorio: RelatorioDeSincronizacao
) -> dict[str, PermissionModel]:
    existentes = {p.code: p for p in (await session.scalars(select(PermissionModel))).all()}

    for code, descricao in PERMISSOES.items():
        atual = existentes.get(code)
        if atual is None:
            modelo = PermissionModel(code=code, description=descricao)
            session.add(modelo)
            existentes[code] = modelo
            relatorio.permissoes_criadas.append(code)
        elif atual.description != descricao:
            atual.description = descricao
            relatorio.descricoes_atualizadas.append(code)

    relatorio.permissoes_obsoletas = sorted(set(existentes) - set(PERMISSOES))
    return existentes


async def _sincronizar_papeis(
    session: AsyncSession, relatorio: RelatorioDeSincronizacao
) -> dict[str, RoleModel]:
    existentes = {r.code: r for r in (await session.scalars(select(RoleModel))).all()}

    for code in PAPEIS:
        atual = existentes.get(code)
        nome = NOMES_DOS_PAPEIS[code]
        if atual is None:
            modelo = RoleModel(code=code, name=nome, description="")
            session.add(modelo)
            existentes[code] = modelo
            relatorio.papeis_criados.append(code)
        elif atual.name != nome:
            atual.name = nome
            relatorio.nomes_atualizados.append(code)

    relatorio.papeis_obsoletos = sorted(set(existentes) - set(PAPEIS))
    return existentes


async def _sincronizar_concessoes(
    session: AsyncSession,
    permissoes: dict[str, PermissionModel],
    papeis: dict[str, RoleModel],
    relatorio: RelatorioDeSincronizacao,
) -> None:
    atuais = {
        (rp.role_id, rp.permission_id): rp
        for rp in (await session.scalars(select(RolePermissionModel))).all()
    }
    id_do_papel = {code: r.id for code, r in papeis.items()}
    id_da_permissao = {code: p.id for code, p in permissoes.items()}

    desejadas: set[tuple[int, int]] = set()
    for papel, permissoes_do_papel in PAPEIS.items():
        for permissao in permissoes_do_papel:
            desejadas.add((id_do_papel[papel], id_da_permissao[permissao]))

    for chave in desejadas - set(atuais):
        session.add(RolePermissionModel(role_id=chave[0], permission_id=chave[1]))
        relatorio.concessoes_adicionadas.append(_rotular(chave, papeis, permissoes))

    # o papel obsoleto mantém as concessões dele: quem ainda o tem não perde
    # acesso por deploy. Só se revoga o que pertence a papel do catálogo.
    ids_do_catalogo = {id_do_papel[papel] for papel in PAPEIS}
    sobrando = {chave for chave in set(atuais) - desejadas if chave[0] in ids_do_catalogo}
    for chave in sobrando:
        await session.execute(
            delete(RolePermissionModel).where(
                RolePermissionModel.role_id == chave[0],
                RolePermissionModel.permission_id == chave[1],
            )
        )
        relatorio.concessoes_revogadas.append(_rotular(chave, papeis, permissoes))


def _rotular(
    chave: tuple[int, int],
    papeis: dict[str, RoleModel],
    permissoes: dict[str, PermissionModel],
) -> tuple[str, str]:
    papel = next((code for code, r in papeis.items() if r.id == chave[0]), str(chave[0]))
    permissao = next((code for code, p in permissoes.items() if p.id == chave[1]), str(chave[1]))
    return papel, permissao
