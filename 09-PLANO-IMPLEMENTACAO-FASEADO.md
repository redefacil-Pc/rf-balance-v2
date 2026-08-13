# Plano de implementação faseado — RF Balance v2

**Versão:** 1.0
**Data:** 11/08/2026
**Base normativa:** `08-BLUEPRINT-TECNICO-RECONSTRUCAO-ECOSSISTEMA.md` (seções 12, 15, 18, 22, 23)
**Objetivo:** construir o ecossistema em fatias verticais entregáveis, rodando em Docker desde o primeiro dia, até substituir o sistema atual

---

## 1. Como este plano funciona

Três regras que valem para todas as fases:

1. **Docker desde a fase 0.** Nenhum comando de desenvolvimento roda fora de container. Se `docker compose up` não sobe o ambiente inteiro, a fase não está pronta. Não existe "depois containerizamos".
2. **Fatia vertical, não camada.** Cada fase entrega banco + API + tela + teste + observabilidade de um pedaço do domínio, usável de ponta a ponta. Não se constrói "todo o backend" e depois "todo o frontend".
3. **Duas trilhas transversais correm em paralelo às fases**, com tarefas dentro de cada uma:
   - **Trilha P — Performance** (seção 4): o problema de lentidão do v1 é tratado como requisito com orçamento medido, não como otimização no fim.
   - **Trilha S — Setores** (seção 5): a abertura para novos setores cadastrarem é tratada como modelo de permissão e escopo, não como "criar mais um login".

Estimativas em semanas assumem 2 desenvolvedores em tempo integral. São premissa, não compromisso — ajuste conforme o time real.

---

## 2. Visão geral das fases

| Fase | Entrega | Semanas (est.) | Pronto quando |
|---|---|---:|---|
| **F0** | Descoberta e congelamento semântico | 2 | Regras confirmadas, casos dourados extraídos do v1, ADRs 1–14 abertos |
| **F1** | Fundação em Docker: compose, CI, migrations, identidade/RBAC, audit/outbox, observabilidade, design system | 4 | Login real, rota protegida, auditoria gravando, `/health/ready` verde, CI bloqueando |
| **F2** | Organização e comercial: empresas, unidades, colaboradores, papéis, vínculos, propostas | 4 | Setor consegue cadastrar colaborador e proposta na v2; importador legado em dry-run |
| **F3** | Recebíveis: pagamentos idempotentes, estornos, state machine | 3 | Pagamento e estorno atômicos, teste de concorrência e de replay passando |
| **F4** | Motor de comissão: rule sets versionados, consultor, MEI escalonado, líderes, finalização/BKO, ledger | 5 | Cálculo determinístico, explicável, batendo com os casos dourados do v1 |
| **F5** | Períodos e fechamento: cutoff, settlements, aprovação, pagamento, ajustes, reabertura | 3 | Fechamento semanal completo, idempotente, com compensação em vez de edição |
| **F6** | Relatórios e documentos: read models, dashboard, relatórios, PDF/XLSX, jobs | 4 | Tela, API e PDF com totais idênticos; dashboard dentro do orçamento p95 |
| **F7** | Migração, shadow mode e cutover | 4 | Shadow mode sem divergência não classificada; cutover ensaiado com rollback |

Total: ~29 semanas. A ordem é a da seção 23 do blueprint e **não deve ser reordenada** — cada fase depende do invariante da anterior.

```text
F0 descoberta
 └─> F1 plataforma/segurança ──> F2 organização+propostas ──> F3 recebimentos
                                                                   │
                                                                   v
                              F5 períodos/settlements <── F4 ledger/motor comissão
                                       │                          │
                                       └────> F6 relatórios <─────┘
                                                   │
                                                   v
                                            F7 migração/cutover
```

---

## 3. Fase por fase

### F0 — Descoberta e congelamento semântico (2 semanas)

Antes de qualquer código. O maior risco do projeto não é técnico, é regra de negócio implícita no v1.

**Tarefas**

- Entrevistar financeiro e operação; escrever o glossário em `docs/business-rules/glossario.md`.
- Responder as 11 perguntas da seção 21 do blueprint (data de produção, tolerância, líder na proposta ou no pagamento, sobrepagamento, estorno retroativo, quem reabre período, retenção). **Cada resposta vira um exemplo executável**, não um parágrafo.
- Extrair do banco atual um conjunto de **casos dourados**: 30–50 propostas reais anonimizadas cobrindo os casos obrigatórios da seção 16.2 (faixas exatas, pagamento parcial, estorno, vínculo mudando na fronteira de data, regra por vigência). Guardar como fixtures.
- Levantar o baseline de performance do v1 (ver Trilha P, P0).
- Abrir os 14 ADRs da seção 20 em `docs/adr/`, com status `proposto`.

**Entregável:** `docs/business-rules/`, fixtures de casos dourados, ADRs abertos, baseline de performance documentado.

**Risco se pular:** o motor de comissão da F4 é reescrito duas vezes.

---

### F1 — Fundação em Docker (4 semanas)

Esta é a fase que responde ao "com Docker desde o início".

**Estrutura de repositório** (seção 19 do blueprint)

```text
rf-balance/
|-- apps/            api/  worker/  web/
|-- packages/        api-client/  design-system/  contracts/
|-- infrastructure/  compose/  nginx/  observability/
|-- docs/            architecture/  adr/  runbooks/  business-rules/
|-- scripts/
|-- .github/workflows/
`-- Makefile
```

**Containers** (seção 12.2)

| Serviço | Imagem/base | Observação |
|---|---|---|
| `web` | nginx:alpine + build Vite | serve estático, proxy `/api` em dev |
| `api` | python:3.12-slim, usuário não-root | FastAPI, **sem scheduler embutido** |
| `worker` | mesma imagem da `api` | jobs assíncronos |
| `scheduler` | mesma imagem da `api` | agenda única, com leader election |
| `db` | mysql:8.x fixado | container **só em local/CI**; produção usa gerenciado |
| `redis` | redis:7-alpine | fila, cache, lock curto |
| `minio` | minio + console | S3 local para PDFs/backups |
| `otel-collector` | opcional, profile `obs` | telemetria |

Princípios do Docker aqui, todos vindos das seções 12.4 e 13.1:

- **Versões fixadas por tag/digest** — nunca `:latest`.
- **Imagem sem root**, multi-stage, sem ferramenta de build no runtime.
- **Nenhum segredo em Dockerfile ou compose versionado.** Local usa `.env` fora do git (com `.env.example` versionado); produção usa secret manager.
- `db`, `redis` e `minio` **sem porta pública** — em local, expostas só para o host de dev; em produção, rede privada.
- `healthcheck` em todo serviço, e `depends_on: condition: service_healthy` na `api`.
- **Conta de banco separada para migration**, com privilégio maior; a app roda com privilégio mínimo.
- Volume nomeado para dados do MySQL; nada de arquivo definitivo dentro do container.
- Migração roda como **step explícito** (`make migrate` / job de deploy), nunca no entrypoint da API e **nunca `create_all`**.

**Esqueleto de `infrastructure/compose/docker-compose.yml`** (referência de partida)

```yaml
services:
  api:
    build: { context: ../.., dockerfile: apps/api/Dockerfile, target: runtime }
    env_file: [../../.env]
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://localhost:8000/health/live')"]
      interval: 10s
      timeout: 3s
      retries: 5
    ports: ["8000:8000"]

  worker:
    build: { context: ../.., dockerfile: apps/api/Dockerfile, target: runtime }
    command: ["python", "-m", "app.worker"]
    env_file: [../../.env]
    depends_on:
      redis: { condition: service_healthy }

  scheduler:
    build: { context: ../.., dockerfile: apps/api/Dockerfile, target: runtime }
    command: ["python", "-m", "app.scheduler"]
    env_file: [../../.env]

  web:
    build: { context: ../.., dockerfile: apps/web/Dockerfile }
    ports: ["5173:80"]
    depends_on: [api]

  db:
    image: mysql:8.4
    command: >
      --character-set-server=utf8mb4 --collation-server=utf8mb4_0900_ai_ci
      --slow-query-log=1 --long-query-time=0.5 --log-queries-not-using-indexes=1
    environment:
      MYSQL_DATABASE: rfbalance
      MYSQL_ROOT_PASSWORD_FILE: /run/secrets/db_root
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      retries: 20
    volumes: [dbdata:/var/lib/mysql]

  redis:
    image: redis:7-alpine
    healthcheck: { test: ["CMD", "redis-cli", "ping"], interval: 5s, retries: 10 }

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: [miniodata:/data]

volumes: { dbdata: {}, miniodata: {} }
```

O `--slow-query-log` com `long-query-time=0.5` já ligado em local é intencional: é a Trilha P começando na primeira semana.

**Demais tarefas da F1**

- Alembic configurado; primeira migração com `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `sessions`, `login_attempts`, `audit_events`, `outbox_events`, `idempotency_keys`.
- Identidade completa: login, refresh rotation, revogação, Argon2id, rate limit no login, **deny by default** nas rotas.
- RBAC por permissão atômica, com a matriz da seção 13.2 como ponto de partida — já modelado para novos setores (Trilha S).
- Audit e outbox funcionando com dispatcher no worker.
- Observabilidade: log JSON com `correlation_id`, `/health/live`, `/health/ready` (banco + migração esperada + Redis + storage), métricas da seção 14.2.
- Frontend: bootstrap, router, provider de auth derivado de `/auth/me`, design system inicial, geração do client TypeScript do OpenAPI.
- CI completo (seção 17): lint, type check, unit, integração com MySQL/Redis efêmeros, OpenAPI diff, build do front, audit de dependências, secret scan, `upgrade`+`downgrade` em banco vazio, build e scan de imagem.
- `Makefile`: `up`, `down`, `migrate`, `seed`, `test`, `lint`, `logs`, `psh`.

**Definition of Done:** um dev novo clona, copia `.env.example`, roda `make up && make migrate && make seed`, faz login na tela e a ação aparece em `audit_events`. CI vermelho bloqueia merge.

---

### F2 — Organização e comercial (4 semanas)

**Escopo:** `companies`, `units`, `collaborators`, `collaborator_roles` (papéis em tabela associativa, com vigência — nunca campo de texto), `collaborator_payment_keys`, `team_assignments`, `bank_accounts`, `proposals` canônico.

**Pontos de atenção**

- `team_assignments` sem sobreposição por consultor/tipo — garantido no banco **e** por verificação em `data_integrity_checks`, já que o MySQL não tem `EXCLUDE`.
- Consulta histórica: "quem era o líder deste consultor na data X" é query de primeira classe, não derivação de tela.
- `proposals` é o **único** aggregate comercial. `sales`/`propostas` do legado vão para staging/ACL, nunca direto.
- Importador legado em **dry-run**, com `legacy_source`/`legacy_id` e fila de exceção para registros ambíguos.
- Primeira fatia real da Trilha S: um setor piloto (sugestão: Operação) já cadastra colaborador e proposta na v2.

**Definition of Done:** setor piloto cadastra em produção-staging; importador roda em dry-run com relatório de divergência; consulta histórica de vínculo coberta por teste de fronteira de data.

---

### F3 — Recebíveis (3 semanas)

**Escopo:** `receipts`, `receipt_reversals`, state machine de proposta, reconciliação.

- Toda mutação numa Unit of Work: pagamento + totais + status + auditoria + outbox, um único commit.
- `Idempotency-Key` obrigatório; chave repetida devolve o mesmo resultado.
- Estorno é lançamento novo + vínculo, nunca `UPDATE` no original.
- Testes obrigatórios: dois pagamentos simultâneos preservam a soma; falha no audit/outbox reverte tudo; retry com a mesma chave não duplica.

**Definition of Done:** os casos 16.4 do blueprint passando, incluindo o de concorrência.

---

### F4 — Motor de comissão (5 semanas)

A fase mais crítica e a que mais depende da F0.

**Escopo:** `commission_rule_sets`, `commission_rules`, `commission_rule_assignments`, `commission_calculation_snapshots`, `commission_entries`, `manual_adjustments`.

**Sub-ordem interna** (não paralelizar):

1. rule sets + vigência + validação de lacuna/sobreposição;
2. consultor padrão (MEI e CLT);
3. proporcionalidade e pagamento parcial;
4. MEI Escalonado (produção e TPS);
5. líder comercial e líder MEI geral;
6. finalização, líder de finalização e BKO;
7. ledger imutável + explicação do cálculo.

**Regras duras**

- Cada modalidade é uma Strategy selecionada pela regra vigente. Zero `if papel == ...` espalhado.
- Todo cálculo grava snapshot de input/output — recálculo tem que ser reprodutível e explicável na tela.
- `commission_entries` é append-only; correção é lançamento compensatório.
- **Aqui está o ganho de performance principal:** a comissão é calculada na *escrita* (ao confirmar pagamento) e lida do ledger. O v2 nunca calcula comissão em tempo de leitura de relatório.

**Definition of Done:** os casos dourados da F0 produzem, no v2, exatamente os valores do v1 — ou a divergência é classificada e assinada pelo financeiro como correção intencional.

---

### F5 — Períodos e fechamento (3 semanas)

**Escopo:** `accounting_periods` (converte o `week_resets` do legado em períodos explícitos), `settlements`, `settlement_items`, `payout_transactions`, ajustes manuais, reabertura.

- Período fechado é **imutável**: bloqueio no domínio, não só na UI.
- Um settlement por beneficiário/período/versão; um item não pertence a dois settlements ativos.
- Fechamento executado duas vezes não duplica.
- Reabertura exige permissão específica e o ADR de dupla aprovação decidido na F0.

---

### F6 — Relatórios e documentos (4 semanas)

**Escopo:** read models, dashboard, relatórios (individual, equipe, unidade, geral, operacional), HTML/PDF/XLSX/ZIP, `document_jobs`, `stored_documents`.

- Tela e PDF consomem **o mesmo DTO**. Divergência de total entre tela, API, PDF e export é bug bloqueante.
- Relatório lê projeção; **não** recalcula comissão em SQL.
- Lote é job assíncrono, idempotente, retomável, com progresso visível e dead-letter.
- Read model reconcilia com o ledger — verificação periódica em `data_integrity_checks`.
- Orçamento a cumprir: dashboard cached p95 < 2 s, relatório interativo p95 < 5 s.

---

### F7 — Migração e cutover (4 semanas)

Segue os 12 passos da seção 18 do blueprint. O que precisa de disciplina:

1. Extrair legado → normalizar/anonimizar → carregar staging.
2. Reconciliar contagens e totais (a lista da "Reconciliação mínima").
3. **Shadow mode:** o v2 calcula sobre os dados reais em paralelo ao v1, sem servir tráfego. Comparar por proposta, pessoa e período.
4. Classificar cada divergência: erro do v2, erro do v1, ou mudança intencional de regra. Nenhuma divergência fica sem classificação.
5. Ensaiar cutover em staging, com rollback cronometrado.
6. Congelar escrita no antigo → delta final → trocar tráfego → monitorar com o v1 ainda restaurável.

O mapeamento tabela-a-tabela está na seção 18 do blueprint e é a especificação do importador. `legacy_source` e `legacy_id` em tudo.

---

## 4. Trilha P — Performance (transversal)

Você relatou que o v1 é lento para trazer dados. Em sistema de comissionamento a causa quase sempre é a mesma família de problemas: **agregação e cálculo feitos em tempo de leitura**, sobre tabelas sem índice de acesso, sem paginação, com N+1. O v2 já nasce com a arquitetura que evita isso — mas só se as medidas abaixo entrarem fase por fase.

### P0 — Baseline (na F0, antes de codar)

Sem número de partida não há como provar melhora.

- Ligar slow query log no v1 por 1–2 semanas de uso real e coletar as **20 queries mais lentas e as 20 mais frequentes**.
- Medir o tempo de resposta das 10 telas mais usadas (dashboard, relatório individual, lista de propostas), em horário de pico.
- Registrar o volume real: nº de propostas, pagamentos, lançamentos de comissão, e crescimento mensal.
- Guardar em `docs/architecture/baseline-performance-v1.md`.

### P1 — Decisões estruturais (F1–F4)

O que efetivamente resolve lentidão, em ordem de impacto:

1. **Cálculo na escrita, leitura no ledger.** Comissão, produção e totais são materializados quando o pagamento é confirmado. Relatório faz `SELECT` de valor pronto, não `SUM` com regra de negócio. Este item sozinho costuma responder pela maior parte da lentidão em sistemas assim.
2. **Read models por caso de uso.** Dashboard e relatórios pesados leem tabela/view projetada, atualizada por evento de outbox. A projeção é desenhada para o `WHERE` da tela, não genérica.
3. **Paginação por cursor obrigatória.** `WHERE (business_date, id) < (:d, :i)` — nunca `OFFSET` alto, nunca "carregar tudo e filtrar no cliente".
4. **Índices por caminho de acesso**, definidos junto com a query: `(collaborator_id, period_id)`, `(proposal_id, business_date)`, `(status, business_date)`, `(unit_id, period_id)`. Índice composto na ordem do uso real.
5. **Projeção de colunas.** DTO seleciona campos; sem `SELECT *`, sem carregar aggregate inteiro para exibir três colunas.
6. **N+1 eliminado explicitamente** com `selectinload`/`joinedload` — e detectado por teste que conta queries.
7. **Cache Redis apenas para dado reconstruível** (dashboard, listas de referência), com invalidação por evento. Nunca cachear valor financeiro autoritativo.
8. **Pool de conexões dimensionado** e monitorado (métrica de pool na seção 14.2).

### P2 — Disciplina contínua (todas as fases)

- **Seed volumétrico desde a F1:** o ambiente de dev/CI carrega dados sintéticos no volume real projetado para 3 anos, não 50 linhas. Lentidão precisa aparecer em desenvolvimento, não em produção.
- **`EXPLAIN` obrigatório** em toda query de listagem nova; sem `filesort`/`temporary` em tabela grande. Entra no checklist de PR.
- **Orçamento de performance no CI:** teste de smoke que falha se CRUD p95 > 500 ms, dashboard > 2 s, relatório > 5 s no dataset volumétrico. Regressão vira build vermelho, não reclamação de usuário.
- **Slow query log ligado em todos os ambientes** (`long_query_time=0.5`), com alerta.
- **Métricas de p50/p95/p99 por rota, cache hit rate e tempo de cálculo de relatório** no painel desde a F1.
- Teste de carga antes do cutover (F7), no volume real + margem.

### P3 — O que *não* fazer

- Não trocar MySQL por PostgreSQL agora. É ADR separado (seção 11.1); migrar banco e domínio juntos multiplica risco e não é a causa da lentidão.
- Não colocar cache na frente de query lenta para esconder o problema. Corrige-se o caminho de acesso primeiro.
- Não desnormalizar por intuição. Read model desenhado > coluna redundante improvisada.

---

## 5. Trilha S — Abrir para mais setores (transversal)

"Mais setores usarem e cadastrarem" é, tecnicamente, três coisas: modelo de permissão granular, escopo de dados, e onboarding controlado.

### S1 — Modelo (F1)

- Permissão **atômica** (`proposals:write`, `receipts:approve`, `collaborators:read`), agrupada em papéis. Setor novo = novo papel composto de permissões existentes, sem alterar código.
- **Escopo de dados** como conceito de primeira classe: unidade, equipe, próprio colaborador. Aplicado como Specification na query (SQL), nunca filtrado no cliente.
- Papel de colaborador em `collaborator_roles` com vigência — uma pessoa acumula funções sem enum combinatório.
- Deny by default: rota nova nasce fechada.

### S2 — Cadastro por setor (F2)

- Cada setor cadastra dentro do seu escopo, com campos obrigatórios validados no backend.
- PII e chave PIX mascaradas por permissão — setor comercial não vê dado bancário.
- Toda ação administrativa auditada com ator, setor e `correlation_id`.
- Fila de aprovação onde o blueprint exige (estorno, ajuste manual, reabertura de período).

### S3 — Ondas de onboarding (F2 → F7)

| Onda | Setor | Entra em qual fase | O que passa a fazer |
|---|---|---|---|
| 1 | Operação | F2 | cadastro de colaborador e proposta |
| 2 | Financeiro | F3–F5 | recebimento, estorno, fechamento, pagamento |
| 3 | Gestão/Liderança | F6 | dashboard, relatório de equipe/unidade, exportação |
| 4 | Auditoria/Compliance | F6 | consulta de log, cálculo e histórico, sem mutação |
| 5 | Setores novos | pós-F7 | papel composto + escopo, sem código novo |

Cada onda precisa de: matriz de permissão assinada pelo negócio, runbook de suporte, treinamento curto, e teste de autorização por rota (seção 16.3: sem token 401, sem permissão 403, perfil correto sucesso, PII mascarada).

---

## 6. Decisões que travam fases

O plano não avança sem estas respostas. Todas são da seção 21 do blueprint.

| Decisão | Trava qual fase |
|---|---|
| Data de produção e de atribuição do líder | F4 |
| Tolerância de quitação (R$ 10 / R$ 100) e sobrepagamento | F3, F4 |
| `CONFIRMED` vs `SETTLED` têm o mesmo efeito? | F3 |
| Líder recebe sobre venda própria? CLT acumula? | F4 |
| MEI Escalonado acumula produção reconhecida ou integral? | F4 |
| Estorno retroativo: altera período antigo ou compensa no atual? | F5 |
| Quem reabre período e com qual aprovação | F5 |
| Retenção de PDF, PII, auditoria e backup | F1 (modelagem), F6 |
| Cookie vs bearer token | F1 |
| Worker: Celery vs Dramatiq vs RQ | F1 |
| Casing do JSON na API | F1 |

Decisões de F1 são urgentes: mudam código de plataforma.

---

## 7. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Regra do v1 descoberta só na F4 | retrabalho do motor | casos dourados na F0, shadow mode na F7 |
| Estruturas duplicadas do legado (`sales`/`propostas`) importadas erradas | dado financeiro corrompido | staging/ACL + fila de exceção, importador nunca escolhe sozinho |
| Lentidão reaparecer na v2 | perda de confiança no projeto | Trilha P: seed volumétrico + orçamento p95 no CI desde a F1 |
| Cutover sem volta | operação parada | ensaio cronometrado, delta final, v1 restaurável, rollback documentado |
| Escopo crescendo por setor novo no meio da fase | atraso em cascata | ondas de onboarding fixas (S3); setor novo pós-F7 é configuração |
| Divergência de total entre tela e PDF | disputa com financeiro | DTO único, teste comparando tela/API/PDF/export |

---

## 8. Próximo passo concreto

Duas coisas podem começar já, em paralelo:

1. **F0**: agendar as entrevistas e extrair os casos dourados do banco atual.
2. **F1 (scaffold)**: criar a estrutura de repositório, os Dockerfiles multi-stage, o compose acima, o Makefile e o CI — isso não depende das respostas de negócio.

Para a Trilha P eu preciso de acesso (ou de um dump anonimizado) ao banco e ao código do v1, para diagnosticar as queries lentas de verdade em vez de trabalhar por hipótese.
