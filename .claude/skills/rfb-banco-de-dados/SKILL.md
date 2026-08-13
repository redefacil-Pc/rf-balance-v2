---
name: rfb-banco-de-dados
description: Banco de dados do RF Balance — MySQL 8 com SQLAlchemy 2 e Alembic. Use ao criar ou alterar tabela, coluna, índice, constraint ou FK, escrever migração, modelar entidade nova, otimizar query lenta, criar view/read model de relatório, tratar DECIMAL e datas, ou revisar integridade e soft-delete de dados financeiros.
---

# Banco de dados — RF Balance

MySQL 8 (InnoDB, `utf8mb4`), SQLAlchemy 2 declarativo, Alembic para toda mudança de schema. PostgreSQL é alternativa superior para constraints de intervalo e analytics, mas a troca de SGBD é ADR separado — **não** migrar banco e domínio ao mesmo tempo.

Fronteiras de propriedade das tabelas: skill `rfb-arquitetura`. Só o módulo dono escreve nas suas tabelas.

## Convenções

- Tabela em `snake_case` plural: `commission_entries`. Coluna em `snake_case`.
- PK `id` (`BIGINT UNSIGNED AUTO_INCREMENT`); ULID/UUID como `external_id` quando exposto.
- FK nomeada `fk_<tabela>_<coluna>`, índice `ix_<tabela>_<colunas>`, único `uq_<tabela>_<colunas>`.
- `created_at` / `updated_at` em toda tabela mutável; `created_by` / `updated_by` onde há ator.
- Booleano como `BOOLEAN` (tinyint), nunca `'S'/'N'`.
- Enum de domínio como `VARCHAR` + validação no domínio (ou tabela de referência), não `ENUM` do MySQL — evita migração dolorosa.

## Dinheiro, tempo e precisão

- Dinheiro: `DECIMAL(18,2)`; taxa/percentual: `DECIMAL(9,6)`. **Nunca** `FLOAT`/`DOUBLE`, nem em coluna de relatório.
- No Python, `Numeric(18, 2, asdecimal=True)` → `Decimal`. Arredondamento `ROUND_HALF_UP` só nos pontos definidos.
- Instantes: `DATETIME(6)` em UTC (`occurred_at`). Data operacional: `DATE` (`business_date`) em `America/Sao_Paulo`. As duas coisas são colunas diferentes e não se derivam uma da outra.
- Vigência temporal: `valid_from` / `valid_to` (`valid_to` nulo = vigente).

## Tabelas canônicas

Identidade: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `sessions`, `login_attempts`.
Organização: `companies`, `units`, `collaborators`, `collaborator_roles`, `collaborator_payment_keys`, `team_assignments`, `bank_accounts`.
Comercial/recebíveis: `customers`, `proposals`, `receipts`, `receipt_reversals`, `idempotency_keys`.
Comissionamento: `commission_rule_sets`, `commission_rules`, `commission_rule_assignments`, `commission_calculation_snapshots`, `commission_entries`, `manual_adjustments`.
Períodos/fechamento: `accounting_periods`, `settlements`, `settlement_items`, `payout_transactions`.
Plataforma: `audit_events`, `outbox_events`, `document_jobs`, `stored_documents`, `data_integrity_checks`.

Não recriar `sales`, `propostas` ou `proposals` duplicados — `proposals` é o aggregate único.

## Constraints essenciais

- `users.email` único e normalizado (lower/trim na escrita).
- `collaborators.document_hash` único — documento é armazenado com hash, não em claro para busca.
- `proposals.external_id` único quando não nulo.
- `receipts.idempotency_key` único no escopo.
- `team_assignments` sem sobreposição por consultor/tipo — sem `EXCLUDE` no MySQL, garantir com único parcial/coluna derivada **e** verificação em `data_integrity_checks`.
- Regras sem lacuna nem sobreposição dentro do mesmo `rule_set`.
- Um settlement por beneficiário/período/versão.
- Um item não pertence a dois settlements ativos.
- `amount != 0` em lançamento contábil (`CHECK`).
- FK sempre com política de delete **explícita**.

## Imutabilidade e exclusão

- `commission_entries`, `audit_events` e `payout_transactions` são **append-only**: correção é lançamento compensatório, nunca `UPDATE`/`DELETE`.
- Dado financeiro usa cancelamento/soft-delete (`canceled_at`, `canceled_by`, motivo). `ON DELETE CASCADE` em cadeia financeira é proibido.
- Estorno é registro novo em `receipts` + vínculo em `receipt_reversals`, não alteração do original.

## Migrações Alembic

- Uma migração por mudança lógica, com `down_revision` correto e `downgrade` real (ou justificativa explícita de irreversibilidade).
- Nunca editar migração já aplicada em produção; criar a próxima.
- Mudança destrutiva (drop de coluna/tabela) em **duas fases**: primeiro parar de usar e fazer deploy, depois remover.
- Backfill de dados vai em migração de dados separada, em lote com limite, não num `UPDATE` de tabela inteira.
- Tabela grande: usar `ALGORITHM=INPLACE`/online DDL quando possível; medir antes em base restaurada.
- `/health/ready` valida a migração esperada — versão do banco e da app não divergem.

## Índices e performance

- Indexar o que é filtrado/ordenado de verdade: `(proposal_id, business_date)`, `(collaborator_id, period_id)`, `(status, business_date)`.
- Índice composto na ordem de seletividade e de uso real do `WHERE`.
- Sem índice redundante (prefixo de outro já existente).
- Query nova de listagem passa por `EXPLAIN`; sem `filesort` em tabela grande de listagem.
- Paginação por cursor (`WHERE (business_date, id) < (:d, :i)`), não `OFFSET` alto.
- N+1 do SQLAlchemy resolvido com `selectinload`/`joinedload` explícito.

## Read models e relatórios

- Relatório lê projeção/view, e **não recalcula** comissão em SQL. O número vem de `commission_entries`.
- View ou tabela materializada atualizada por evento de outbox; documentar a fonte e a latência aceitável.
- Tela e PDF consomem o mesmo read model.

## Segurança e LGPD

- PIX/documento: coluna protegida e versionada (`collaborator_payment_keys`), com histórico de troca auditado.
- Banco, Redis e storage sem porta pública; credencial só em variável de ambiente/secret, nunca em Dockerfile, Compose versionado ou seed.
- Backup com restore testado — backup não verificado não conta. Retenção conforme política LGPD.

## Checklist antes de entregar

1. Dinheiro em `DECIMAL`, nunca float?
2. `occurred_at` (UTC) e `business_date` separados?
3. Invariante do blueprint virou constraint no banco, não só validação em Python?
4. FK com política de delete explícita e sem cascade destrutivo?
5. Tabela contábil ficou append-only?
6. Migração tem `downgrade` e é segura em tabela grande?
7. Índice novo justificado por `EXPLAIN`?
8. Nenhuma regra de comissão foi implementada em SQL de relatório?
