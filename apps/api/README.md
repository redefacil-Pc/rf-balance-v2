# apps/api — backend

Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, MySQL 8, Redis.

## Estrutura

```text
app/
|-- platform/            # infraestrutura transversal, sem regra de negócio
|   |-- config/          # settings por área, validadas no startup (fail-fast)
|   |-- db/              # engine, metadata, tipos customizados
|   |   `-- session/     # sessão e Unit of Work
|   |-- bus/             # outbox, dispatcher, publicação de eventos
|   |-- cache/           # abstração de cache (Redis)
|   |-- storage/         # object storage (S3/MinIO)
|   |-- observability/   # logging estruturado, métricas, tracing
|   |-- security/        # hashing, token, dependências de permissão
|   |-- http/            # middlewares, correlation id, paginação por cursor
|   |-- errors/          # Problem Details e mapeamento de exceções
|   `-- time/            # clock, timezone, business_date
|-- shared/
|   `-- domain/          # shared kernel: value objects usados por vários módulos
|                        # (DateRange, Documento, e Money a partir da F3)
|-- modules/             # um diretório por bounded context
`-- main.py              # composição da aplicação, nada além disso
```

`platform/` nunca importa de `modules/`. `modules/` importa de `platform/` e de
`shared/`.

**`shared/domain/` é regra de negócio, `platform/` é infraestrutura.** Um value
object só entra no shared kernel quando dois módulos realmente o usam — shared
kernel que cresce sem critério vira acoplamento global. Nada aqui importa
framework.

## Template de módulo

Todo módulo tem exatamente estas quatro camadas:

```text
modules/<modulo>/
|-- domain/
|   |-- entities/        # uma entidade/aggregate por arquivo
|   |-- value_objects/   # Money, Percentage, DateRange...
|   |-- policies/        # regras nomeáveis, specifications
|   `-- events/          # eventos de domínio
|-- application/
|   |-- commands/        # um caso de uso de escrita por arquivo (command + handler)
|   |-- queries/         # um caso de uso de leitura por arquivo
|   `-- ports/           # interfaces que o módulo exige do mundo externo
|-- infrastructure/
|   |-- models/          # models SQLAlchemy — um por tabela
|   `-- repositories/    # implementação das portas de persistência
`-- api/
    |-- routes/          # um router por recurso
    `-- schemas/         # DTOs de request/response Pydantic
```

Módulos existentes: `identity`, `organization`, `teams`, `commercial`, `receivables`, `commissions`, `settlements`, `periods`, `reporting`, `documents`, `audit`.

Extras justificados pelo blueprint:

- `commissions/domain/strategies/` — uma strategy por modalidade de comissão (consultor MEI, CLT, MEI escalonado, líder comercial, líder MEI geral, finalização, líder de finalização). Uma por arquivo.
- `commissions/domain/rules/` — faixas, vigência, validação de lacuna e sobreposição.
- `reporting/infrastructure/read_models/` e `projections/` — leitura otimizada e atualização por evento.
- `documents/infrastructure/templates/` e `renderers/` — Jinja2 e WeasyPrint.
- `identity/infrastructure/hashing/` — Argon2id/bcrypt isolado.

## Regras de arquivo

| Arquivo | Contém | Não contém |
|---|---|---|
| `api/routes/*.py` | autenticação, validação de DTO, criação de command, chamada do handler, resposta | query no ORM, cálculo, transação |
| `application/commands/*.py` | um command imutável + seu handler, com Unit of Work | SQL cru, detalhe de HTTP |
| `application/queries/*.py` | uma query + handler de leitura, sem transação de escrita | mutação |
| `domain/**` | regra de negócio pura | FastAPI, SQLAlchemy, Redis, PDF |
| `infrastructure/models/*.py` | um model SQLAlchemy | regra de negócio |
| `infrastructure/repositories/*.py` | acesso a dados de um aggregate | `commit()` |

`commit()` acontece **uma vez por caso de uso**, no handler, via Unit of Work.

## Testes

```text
tests/
|-- unit/           # domínio e strategies, sem I/O
|-- integration/    # handler + MySQL/Redis efêmeros; transação, rollback, idempotência
|-- contract/       # OpenAPI vs consumidores
|-- e2e/            # proposta -> recebimento -> comissão -> fechamento -> PDF
|-- fixtures/       # casos dourados anonimizados vindos da F0
`-- performance/    # orçamento p95 sobre dataset volumétrico
```

Metas de cobertura (seção 16.5 do blueprint): domínio financeiro ≥ 90%, application ≥ 80%, total ≥ 75%.

## Migrations

`migrations/versions/` — uma migração por mudança lógica, com `downgrade` real. Nunca `create_all`. Mudança destrutiva em duas fases (expand/contract).
