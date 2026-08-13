---
name: rfb-arquitetura
description: Decisões de arquitetura de software do RF Balance — fronteiras de módulos, bounded contexts, dependências permitidas, Clean/Hexagonal, CQRS leve, Outbox, Unit of Work, state machines e escrita de ADRs. Use ao criar um módulo novo, mover código entre camadas, decidir onde uma regra mora, avaliar acoplamento entre contextos, revisar um design, ou quando alguém propõe microserviço, fila, cache ou banco novo.
---

# Arquitetura — RF Balance

Referência normativa: `08-BLUEPRINT-TECNICO-RECONSTRUCAO-ECOSSISTEMA.md`, seções 4, 5 e 6.
Em conflito entre este arquivo e o blueprint, o blueprint vence — e atualize este arquivo.

## Postura padrão

**Monólito modular primeiro.** API, worker e banco em processos/containers separados; módulos com fronteira explícita dentro do mesmo deploy. Não propor microserviço, broker dedicado ou banco separado sem ADR aprovado — o domínio ainda compartilha transação forte entre proposta, recebimento, comissão e auditoria.

**Backend é a única fonte de verdade financeira.** Nenhum valor de produção, comissão ou fechamento é calculado no frontend, em SQL ad-hoc de relatório, ou em template de PDF. Tela e PDF consomem o mesmo DTO.

## Módulos e donos de dados

| Módulo | Responsabilidade | Dono dos dados |
|---|---|---|
| `identity` | Usuários, sessão, RBAC, revogação | `users`, `roles`, `permissions`, `sessions` |
| `organization` | Colaboradores, papéis, empresas, unidades, PIX | `collaborators`, `companies`, `units` |
| `teams` | Vínculos temporais consultor-líder | `team_assignments` |
| `commercial` | Propostas e dados do cliente/operação | `proposals` |
| `receivables` | Pagamentos, estornos, conciliação | `receipts`, `receipt_reversals` |
| `commissions` (rules) | Regras e versões de comissionamento | `commission_rule_sets`, `commission_rules` |
| `commissions` (engine) | Cálculo determinístico e lançamentos | `commission_entries`, snapshots |
| `settlements` | Fechamento e pagamento real | `settlements`, `settlement_items` |
| `periods` | Semanas, cortes, fechamentos | `accounting_periods` |
| `reporting` | Read models, dashboard, relatórios | views / materialized / cache |
| `documents` | HTML, PDF, ZIP, arquivos | `document_jobs`, object storage |
| `audit` | Logs imutáveis e trilha explicativa | `audit_events` |

Regra dura: **só o módulo dono escreve nas suas tabelas.** Outro módulo precisa do dado? Vai por porta da camada `application`, nunca por `select` cruzado nem por import de ORM alheio.

## Dependências permitidas

```text
identity ────────────────┐
organization ──> teams   |
      |            |     |
      v            v     v
commercial ──> receivables ──> commissions(engine)
                      |               |
commissions(rules) ───┘               v
periods ─────────────────────────> settlements
      |                                |
      +-----------> reporting <--------+
                        |
                        v
                    documents

toda mutação relevante ──> audit / outbox
```

Seta ausente = dependência proibida. Ciclo = erro de design, não "exceção pragmática". Se `commercial` parece precisar de `settlements`, o que falta é um evento ou um read model em `reporting`.

## Camadas dentro do módulo

```text
module/
|-- domain/          # entidades, value objects, policies, eventos
|-- application/     # commands, queries, use cases, portas
|-- infrastructure/  # SQLAlchemy, Redis, storage, filas, integrações
`-- api/             # controllers, DTOs, autorização HTTP
```

`domain/` não importa FastAPI, SQLAlchemy, Redis, Jinja2 nem biblioteca de PDF. Se um import desses aparecer em `domain/`, a regra está na camada errada.

## Onde a regra mora

- Invariante de uma entidade só (proposta não aceita valor negativo) → `domain/`, na própria entidade.
- Regra que envolve várias entidades ou é política de negócio nomeável (rateio marginal, atribuição histórica de líder) → domain service em `domain/`.
- Orquestração, transação, autorização, idempotência → use case em `application/`.
- Tradução de payload HTTP, código de status, serialização → `api/`.
- Detalhe de banco, chave de cache, formato de arquivo → `infrastructure/`.

Condicional financeira dentro de controller ou de query de relatório é bug arquitetural, mesmo que o resultado esteja correto hoje.

## DDD pragmático

- Aggregates: `Proposal`, `Settlement`, `AccountingPeriod`, `RuleSet`.
- Entities: `Receipt`, `TeamAssignment`, `CommissionEntry`.
- Value objects: `Money`, `Percentage`, `DateRange`, `Document`, `RuleVersion`.
- Domain events: pagamento confirmado, proposta quitada, período fechado.

Não criar aggregate, repositório e use case para CRUD simples (catálogo de bancos, lista de produtos). Custo sem regra é cerimônia.

## Padrões obrigatórios

**Unit of Work** — um pagamento confirma numa única transação: registro do pagamento, totais da proposta, status, lançamentos de comissão derivados, auditoria, evento de outbox. Falha em qualquer etapa → rollback de tudo. Nunca commit parcial "para não perder o pagamento".

**Outbox** — evento para worker/cache/documento é gravado em `outbox_events` na *mesma* transação do negócio; um dispatcher publica depois e marca como processado. Não publicar em Redis dentro da transação nem depois do commit sem outbox.

**CQRS leve** — commands passam por autorização e transação; queries usam projeções e não mutam nada. Mesmo banco, por enquanto. Relatório pesado vira view/tabela materializada atualizada por evento.

**Strategy + Factory para comissão** — cada modalidade (consultor MEI, CLT, MEI escalonado, líder comercial, líder MEI geral, finalização, líder de finalização) é uma strategy selecionada por regra vigente. Nunca `if papel == ...` espalhado.

**Specification/Policy** — elegibilidade e filtro de escopo como objetos compostos, reaproveitados entre command, query e relatório.

**State machine explícita** — status de proposta, período e settlement têm transições declaradas; transição não declarada é rejeitada no domínio, não só na UI.

**Regra versionada, nunca condicional** — mudança de comissionamento é novo `commission_rule_set` com vigência, e o cálculo persiste snapshot do input/output. Recálculo tem que ser explicável e reprodutível.

## Tempo e dinheiro (vale em todas as camadas)

- Instantes em UTC com timezone; exibição e data operacional em `America/Sao_Paulo`.
- `business_date` é distinto de `occurred_at`.
- `DECIMAL`/`Decimal`, nunca `float`, em persistência e cálculo.
- `ROUND_HALF_UP`, duas casas, só nos pontos de arredondamento definidos.

## ADR

Toda escolha estrutural virou ADR em `docs/adr/NNNN-titulo.md`: contexto, decisão, alternativas consideradas, consequências, status. Temas que exigem ADR próprio: MySQL vs PostgreSQL, escolha do worker (Celery/Dramatiq/RQ), Redis Streams vs broker dedicado, snake_case vs camelCase na API, estratégia de token, quebra de módulo em serviço.

## Checklist de revisão

1. Módulo novo/alterado respeita o grafo de dependências?
2. `domain/` está livre de framework?
3. Toda mutação financeira está dentro de UoW com auditoria e outbox?
4. Regra nova é versionada, ou entrou como condicional?
5. Cálculo produz snapshot explicável?
6. Query de relatório recalcula algo que o engine já calculou?
7. A decisão precisa de ADR e ele existe?
