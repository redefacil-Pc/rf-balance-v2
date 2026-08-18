"""Pessoas de demonstração cobrindo os perfis e funções reais.

    python -m app.platform.db.seed_demo

Usa os **casos de uso da aplicação**, não SQL: assim as invariantes valem
(documento único e cifrado, vigência sem sobreposição, vínculo 1:1 com a conta,
auditoria). Semear por SQL produziria linha que a aplicação nunca aceitaria — e
o dado de teste passaria a mentir sobre o que o sistema permite.

Separado de `seed.py`, que cria as contas mínimas de operação: isto aqui é massa
de teste, existe só para ver as telas povoadas, e não roda em produção.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import date

from app.modules.audit.infrastructure.repositories.sql_audit_recorder import SqlAuditRecorder
from app.modules.identity.application.commands.create_user import CreateUser, CreateUserHandler
from app.modules.identity.infrastructure.hashing.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.identity.infrastructure.repositories.sql_user_repository import SqlUserRepository
from app.modules.organization.application.commands.create_collaborator import (
    CreateCollaborator,
    CreateCollaboratorHandler,
    PapelSolicitado,
)
from app.modules.organization.domain.value_objects.papel_de_colaborador import (
    PapelDeColaborador,
    RegimeTributario,
)
from app.modules.organization.infrastructure.repositories.sql_collaborator_repository import (
    SqlCollaboratorRepository,
)
from app.modules.organization.infrastructure.repositories.sql_company_repository import (
    SqlCompanyRepository,
)
from app.platform.config.settings import get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.security import pii_cipher as pii
from app.platform.time.clock import SystemClock
from app.shared.domain.documento import Documento

VIGENTE_DESDE = date(2026, 1, 1)


@dataclass(frozen=True, slots=True)
class Pessoa:
    nome: str
    documento: str
    funcao: str
    regime: RegimeTributario
    #: `None` = não acessa o sistema, como o BKO — entra só como cadastro
    perfis: tuple[str, ...] | None
    email: str = ""


PESSOAS: tuple[Pessoa, ...] = (
    Pessoa(
        "Ana Operacional",
        "529.982.247-25",
        "FINALIZACAO",
        RegimeTributario.MEI,
        ("OPERACIONAL",),
        "ana.operacional@rfbalance.local",
    ),
    Pessoa(
        "Bruno Lider",
        "390.533.447-05",
        "LIDER",
        RegimeTributario.MEI,
        ("LIDERANCA",),
        "bruno.lider@rfbalance.local",
    ),
    Pessoa(
        "Carla Consultora",
        "168.995.350-09",
        "CONSULTOR",
        RegimeTributario.MEI,
        ("CONSULTOR",),
        "carla.consultora@rfbalance.local",
    ),
    Pessoa(
        "Diego Consultor Escalonado",
        "111.444.777-35",
        "CONSULTOR_MEI_ESCALONADO",
        RegimeTributario.MEI,
        ("CONSULTOR",),
        "diego.mei@rfbalance.local",
    ),
    Pessoa(
        "Elena Lider MEI",
        "298.213.940-51",
        "LIDER_MEI_GERAL",
        RegimeTributario.MEI,
        ("LIDERANCA",),
        "elena.meigeral@rfbalance.local",
    ),
    Pessoa(
        "Fabio Lider Final",
        "693.994.290-40",
        "LIDER_FINALIZACAO",
        RegimeTributario.CLT,
        ("LIDERANCA",),
        "fabio.liderfinal@rfbalance.local",
    ),
    Pessoa("Gisele BKO", "021.965.940-08", "BKO", RegimeTributario.MEI, None),
    Pessoa(
        "Helio Financeiro",
        "144.171.100-77",
        "FINALIZACAO",
        RegimeTributario.CLT,
        ("FINANCEIRO",),
        "helio.financeiro@rfbalance.local",
    ),
)


async def executar(company_id: int = 1, unit_id: int | None = 1) -> int:
    settings = get_settings()
    if settings.app.is_production:
        print("seed de demonstração não roda em produção", file=sys.stderr)
        return 1

    engine = criar_engine(settings.database)
    fabrica = criar_fabrica_de_sessoes(engine)
    cipher = pii.criar(settings.pii.chave, settings.pii.pepper)
    clock = SystemClock(settings.app.app_timezone)

    linhas: list[str] = []
    try:
        async with fabrica() as sessao:
            if await SqlCompanyRepository(sessao).buscar_por_id(company_id) is None:
                print(f"empresa {company_id} não existe — crie uma antes", file=sys.stderr)
                return 1

        for pessoa in PESSOAS:
            # uma transação por pessoa: uma falha isolada não desfaz as demais
            async with UnitOfWork(fabrica) as uow:
                colaboradores = SqlCollaboratorRepository(uow.session)

                # idempotente pelo documento, que é a identidade da pessoa: o
                # e-mail pode mudar, o CPF não. Rodar de novo não duplica nem
                # estoura no meio da lista.
                digitos = Documento.normalizar(pessoa.documento).digitos
                if await colaboradores.existe_documento(cipher.hash_de_busca(digitos)):
                    linhas.append(f"{pessoa.nome:20} já existe — mantido")
                    continue

                audit = SqlAuditRecorder(uow.session, clock)
                criador = CreateCollaboratorHandler(
                    uow=uow,
                    colaboradores=colaboradores,
                    empresas=SqlCompanyRepository(uow.session),
                    cipher=cipher,
                    audit=audit,
                    clock=clock,
                )
                cadastro = CreateCollaborator(
                    company_id=company_id,
                    unit_id=unit_id,
                    full_name=pessoa.nome,
                    documento=pessoa.documento,
                    regime=pessoa.regime,
                    papeis=(
                        PapelSolicitado(
                            papel=PapelDeColaborador(pessoa.funcao), valid_from=VIGENTE_DESDE
                        ),
                    ),
                    email=pessoa.email or None,
                )

                if pessoa.perfis is None:
                    await criador.execute(cadastro)
                    linhas.append(f"{pessoa.nome:20} {pessoa.funcao:26} (sem conta de acesso)")
                    continue

                criado = await CreateUserHandler(
                    uow=uow,
                    users=SqlUserRepository(uow.session),
                    hasher=Argon2PasswordHasher(),
                    audit=audit,
                    collaborator_creator=criador,
                    collaborators=colaboradores,
                ).execute(
                    CreateUser(
                        email=pessoa.email,
                        full_name=pessoa.nome,
                        papeis=pessoa.perfis,
                        colaborador=cadastro,
                    )
                )
                linhas.append(
                    f"{pessoa.nome:20} {pessoa.funcao:26} {'+'.join(pessoa.perfis):12} "
                    f"{pessoa.email:38} senha: {criado.senha_provisoria}"
                )
    finally:
        await engine.dispose()

    print("\n".join(linhas))
    print("\nas senhas aparecem uma única vez; todas exigem troca no primeiro acesso")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(executar()))
