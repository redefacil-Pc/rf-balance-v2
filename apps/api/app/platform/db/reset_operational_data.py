"""Zera os dados operacionais para recomeçar um teste do zero.

    python -m app.platform.db.reset_operational_data

**Não roda em produção** e não roda sem confirmação explícita: apagar dado
financeiro por engano custa mais caro que digitar uma palavra a mais.

O que sobrevive, e por quê:

- `permissions`, `roles`, `role_permissions` — catálogo de acesso criado pelas
  migrations. Sem eles ninguém entra, nem o administrador.
- `commission_rule_sets`, `commission_rules`, `commission_strategy_configs` —
  as versões-base de regra, também vindas de migration. Apagá-las deixaria o
  motor sem regra vigente e todo cálculo passaria a falhar.
- `receiving_accounts` — o catálogo de contas de banco é configuração, não
  massa de teste. Use `--incluir-contas` para apagá-lo também.
- `alembic_version` — o schema não é recriado; só os dados saem.

Depois de rodar, recrie o administrador com:

    python -m app.platform.db.seed
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.platform.config.settings import get_settings

#: das folhas para as raízes — a ordem só importa se as FKs forem respeitadas,
#: e aqui elas são desligadas; manter a ordem legível ajuda a revisar a lista
TABELAS_OPERACIONAIS = (
    "stored_documents",
    "document_jobs",
    "data_integrity_checks",
    "commission_settlements",
    "commission_manual_entries",
    "commission_periods",
    "commission_entries",
    "commission_calculation_snapshots",
    "commission_rule_assignments",
    "commission_beneficiary_policies",
    "audit_events",
    "outbox_events",
    "login_attempts",
    "sessions",
    "legacy_import_issues",
    "legacy_import_runs",
    "proposal_attachments",
    "receipt_reversals",
    "receipts",
    "proposals",
    "team_assignments",
    "collaborator_roles",
    "collaborator_payment_keys",
    "collaborators",
    "units",
    "companies",
    "user_roles",
    "users",
)

#: preservadas por padrão: configuração que o operador cadastrou, não massa
CONFIGURACAO = ("receiving_accounts",)


async def executar(*, incluir_contas: bool) -> int:
    settings = get_settings()
    if settings.app.is_production:
        print("Recusado: este comando não roda em produção.")
        return 1

    alvos = [*TABELAS_OPERACIONAIS, *(CONFIGURACAO if incluir_contas else ())]
    # a conta de migração é a que tem DDL. TRUNCATE exige DROP, e é ele que
    # devolve o AUTO_INCREMENT para 1 — sem isso, a primeira proposta do teste
    # novo nasceria com o id seguinte ao da massa antiga
    engine = create_async_engine(settings.database.migration_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conexao:
            await conexao.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for tabela in alvos:
                await conexao.execute(text(f"TRUNCATE TABLE {tabela}"))
            # versões-base vêm de migration e precisam continuar de pé; o que
            # foi criado depois, pela tela de regras, é cadastro de teste
            await conexao.execute(text("DELETE FROM commission_rules WHERE rule_set_id <> 1"))
            await conexao.execute(text("DELETE FROM commission_rule_sets WHERE id <> 1"))
            await conexao.execute(text("DELETE FROM commission_strategy_configs WHERE id > 5"))
            await conexao.execute(
                text(
                    "UPDATE commission_rule_sets SET status='ACTIVE', valid_to=NULL, "
                    "activated_by=NULL WHERE id=1"
                )
            )
            await conexao.execute(
                text(
                    "UPDATE commission_strategy_configs SET status='ACTIVE', valid_to=NULL, "
                    "activated_by=NULL WHERE id <= 5"
                )
            )
            await conexao.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    finally:
        await engine.dispose()

    print(f"{len(alvos)} tabelas zeradas, com os ids reiniciando em 1.")
    if not incluir_contas:
        print("Catálogo de contas de recebimento preservado.")
    print("Recrie o administrador com: python -m app.platform.db.seed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--incluir-contas",
        action="store_true",
        help="apaga também o catálogo de contas de recebimento",
    )
    parser.add_argument(
        "--sim",
        action="store_true",
        help="confirma a exclusão; sem esta flag o comando apenas descreve o que faria",
    )
    args = parser.parse_args()

    if not args.sim:
        print("Nada foi apagado. Estas tabelas seriam zeradas:")
        for tabela in TABELAS_OPERACIONAIS:
            print(f"  - {tabela}")
        if args.incluir_contas:
            print(f"  - {CONFIGURACAO[0]}")
        print("\nRepita com --sim para confirmar.")
        return 0

    return asyncio.run(executar(incluir_contas=args.incluir_contas))


if __name__ == "__main__":
    raise SystemExit(main())
