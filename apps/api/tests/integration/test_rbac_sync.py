"""Sincronização do RBAC contra o banco real.

O bug que originou este módulo: uma permissão nova no catálogo não chegava ao
banco, e o sintoma era 403 em vez de erro. Os testes cobrem os dois lados —
aplicar o catálogo e *detectar* que ele não foi aplicado.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import delete, func, select

from app.modules.identity.domain.permission_catalog import PAPEIS, PERMISSOES
from app.modules.identity.infrastructure import rbac_sync
from app.modules.identity.infrastructure.models.permission_model import PermissionModel
from app.modules.identity.infrastructure.models.role_model import RoleModel
from app.modules.identity.infrastructure.models.role_permission_model import RolePermissionModel
from app.modules.identity.infrastructure.models.user_model import UserModel
from app.modules.identity.infrastructure.models.user_role_model import UserRoleModel
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes

pytestmark = pytest.mark.integration


@pytest.fixture
async def sessao() -> Any:
    engine = criar_engine(get_settings().database)
    fabrica = criar_fabrica_de_sessoes(engine)
    try:
        async with fabrica() as session:
            yield session
    finally:
        await engine.dispose()


async def test_sincronizacao_aplica_o_catalogo_inteiro(sessao: Any) -> None:
    relatorio = await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    assert len(relatorio.permissoes_criadas) == len(PERMISSOES)
    assert len(relatorio.papeis_criados) == len(PAPEIS)
    assert (await rbac_sync.verificar(sessao)).sincronizado


async def test_sincronizacao_e_idempotente(sessao: Any) -> None:
    await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    segunda = await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    assert not segunda.mudou


async def test_permissao_faltando_e_detectada_e_recriada(sessao: Any) -> None:
    """O bug original: catálogo andou, banco não."""
    await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    alvo = await sessao.scalar(
        select(PermissionModel).where(PermissionModel.code == "proposals:approve")
    )
    await sessao.execute(
        delete(RolePermissionModel).where(RolePermissionModel.permission_id == alvo.id)
    )
    await sessao.execute(delete(PermissionModel).where(PermissionModel.id == alvo.id))
    await sessao.commit()

    divergencia = await rbac_sync.verificar(sessao)
    assert not divergencia.sincronizado
    assert "proposals:approve" in divergencia.permissoes_faltando
    assert "proposals:approve" in divergencia.resumo()

    await rbac_sync.sincronizar(sessao)
    await sessao.commit()
    assert (await rbac_sync.verificar(sessao)).sincronizado


async def test_concessao_faltando_e_detectada_e_reposta(sessao: Any) -> None:
    await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    papel = await sessao.scalar(select(RoleModel).where(RoleModel.code == "FINANCEIRO"))
    permissao = await sessao.scalar(
        select(PermissionModel).where(PermissionModel.code == "proposals:approve")
    )
    await sessao.execute(
        delete(RolePermissionModel).where(
            RolePermissionModel.role_id == papel.id,
            RolePermissionModel.permission_id == permissao.id,
        )
    )
    await sessao.commit()

    divergencia = await rbac_sync.verificar(sessao)
    assert ("FINANCEIRO", "proposals:approve") in divergencia.concessoes_faltando

    await rbac_sync.sincronizar(sessao)
    await sessao.commit()
    assert (await rbac_sync.verificar(sessao)).sincronizado


async def test_concessao_indevida_e_revogada(sessao: Any) -> None:
    """Só adicionar não basta: permissão tirada do código tem de sair do banco,
    senão o acesso continua valendo depois do deploy que o removeu."""
    await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    papel = await sessao.scalar(select(RoleModel).where(RoleModel.code == "CONSULTOR"))
    permissao = await sessao.scalar(
        select(PermissionModel).where(PermissionModel.code == "settlements:approve")
    )
    sessao.add(RolePermissionModel(role_id=papel.id, permission_id=permissao.id))
    await sessao.commit()

    divergencia = await rbac_sync.verificar(sessao)
    assert ("CONSULTOR", "settlements:approve") in divergencia.concessoes_a_mais

    relatorio = await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    assert ("CONSULTOR", "settlements:approve") in relatorio.concessoes_revogadas
    assert (await rbac_sync.verificar(sessao)).sincronizado


async def test_purga_remove_papel_obsoleto_sem_conta(sessao: Any) -> None:
    await rbac_sync.sincronizar(sessao)
    obsoleto = RoleModel(code="PAPEL_ANTIGO", name="Papel Antigo", description="")
    sessao.add(obsoleto)
    await sessao.flush()
    permissao = await sessao.scalar(
        select(PermissionModel).where(PermissionModel.code == "proposals:read")
    )
    sessao.add(RolePermissionModel(role_id=obsoleto.id, permission_id=permissao.id))
    await sessao.commit()

    relatorio = await rbac_sync.purgar_obsoletos(sessao)
    await sessao.commit()

    assert "PAPEL_ANTIGO" in relatorio.removidos
    assert await sessao.scalar(select(RoleModel).where(RoleModel.code == "PAPEL_ANTIGO")) is None
    # as concessões vão junto, sem deixar linha órfã apontando para papel morto
    sobrou = await sessao.scalar(
        select(func.count())
        .select_from(RolePermissionModel)
        .where(RolePermissionModel.role_id == obsoleto.id)
    )
    assert sobrou == 0


async def test_purga_nao_remove_papel_com_conta_vinculada(sessao: Any) -> None:
    """A invariante que torna a purga segura: remover papel em uso deixaria a
    pessoa logando e sem enxergar nada — pior que o papel obsoleto, porque o
    sintoma não aponta a causa."""
    await rbac_sync.sincronizar(sessao)
    obsoleto = RoleModel(code="PAPEL_EM_USO", name="Papel Em Uso", description="")
    usuario = UserModel(
        email="ocupante@rfbalance.local",
        full_name="Ocupante",
        password_hash="x",
        is_active=True,
        must_change_password=False,
    )
    sessao.add_all([obsoleto, usuario])
    await sessao.flush()
    sessao.add(UserRoleModel(user_id=usuario.id, role_id=obsoleto.id))
    await sessao.commit()

    relatorio = await rbac_sync.purgar_obsoletos(sessao)
    await sessao.commit()

    assert ("PAPEL_EM_USO", 1) in relatorio.mantidos_em_uso
    assert "PAPEL_EM_USO" not in relatorio.removidos
    assert await sessao.scalar(select(RoleModel).where(RoleModel.code == "PAPEL_EM_USO"))


async def test_purga_e_idempotente_e_nao_toca_no_catalogo(sessao: Any) -> None:
    await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    primeira = await rbac_sync.purgar_obsoletos(sessao)
    await sessao.commit()
    segunda = await rbac_sync.purgar_obsoletos(sessao)
    await sessao.commit()

    assert not primeira.removidos and not segunda.removidos
    # os papéis do catálogo continuam todos lá
    restantes = {r.code for r in (await sessao.scalars(select(RoleModel))).all()}
    assert set(PAPEIS) <= restantes
    assert (await rbac_sync.verificar(sessao)).sincronizado


async def test_papel_obsoleto_e_reportado_mas_preservado(sessao: Any) -> None:
    """Apagar papel derrubaria o acesso de quem ainda o tem — isso é decisão de
    operador. E como a sincronização não mexe nele, o readiness também não pode
    acusá-lo, senão fica vermelho para sempre."""
    await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    obsoleto = RoleModel(code="PAPEL_ANTIGO", name="Papel Antigo", description="")
    sessao.add(obsoleto)
    await sessao.flush()
    permissao = await sessao.scalar(
        select(PermissionModel).where(PermissionModel.code == "proposals:read")
    )
    sessao.add(RolePermissionModel(role_id=obsoleto.id, permission_id=permissao.id))
    await sessao.commit()

    relatorio = await rbac_sync.sincronizar(sessao)
    await sessao.commit()

    assert "PAPEL_ANTIGO" in relatorio.papeis_obsoletos
    # continua lá, com as concessões dele
    assert await sessao.scalar(select(RoleModel).where(RoleModel.code == "PAPEL_ANTIGO"))
    assert (await rbac_sync.verificar(sessao)).sincronizado
