# Blueprint técnico para reconstrução do ecossistema RF Balance

**Versão:** 1.0  
**Data:** 11/08/2026  
**Objetivo:** permitir a recriação completa, segura e eficiente do RF Balance  
**Referência funcional:** comportamento observado no sistema atual, com correções arquiteturais propostas  
**Público:** produto, engenharia, QA, DevOps, segurança, dados e suporte

## 1. Objetivo e resultado esperado

Este documento é a especificação-base para reconstruir o RF Balance como um ecossistema completo de operação comercial, recebimentos, comissionamento e fechamento financeiro.

A nova implementação deve:

- preservar as funcionalidades úteis do sistema atual;
- manter o backend como fonte única de verdade financeira;
- eliminar estruturas duplicadas como `sales`, `propostas` e `proposals`;
- garantir atomicidade em propostas, pagamentos, estornos e fechamentos;
- tratar regras de comissão como configuração versionada, e não como condicionais espalhadas;
- oferecer rastreabilidade completa de quem fez o quê, quando e com qual regra;
- proteger dados pessoais e financeiros por autenticação e autorização no backend;
- permitir geração síncrona e em lote de relatórios/PDFs;
- simplificar operação, deploy, testes e evolução.

O produto final será inicialmente um **monólito modular**, com API, worker e banco separados em processos/containers. Os módulos terão fronteiras explícitas para poderem virar serviços independentes no futuro, sem assumir desde já o custo de microserviços.

## 2. Escopo funcional completo

O ecossistema cobre os seguintes blocos:

1. identidade, sessão e controle de acesso;
2. cadastro de colaboradores;
3. empresas, unidades e contas bancárias;
4. vínculos temporais entre consultores e líderes;
5. cadastro e manutenção de propostas;
6. recebimentos parciais, totais e estornos;
7. cálculo de comissão de consultor MEI e CLT;
8. cálculo MEI Escalonado por produção e TPS;
9. comissão de líder comercial;
10. comissão de líder MEI geral por unidade;
11. comissão de finalização e líder de finalização;
12. lançamentos manuais de BKO e finalização;
13. fechamento e pagamento real de comissões;
14. reset/fechamento semanal;
15. dashboard, métricas e rankings;
16. relatórios individuais, de equipe, unidade, geral e operacional;
17. geração de HTML, PDF e ZIP em lote;
18. auditoria, histórico e recálculo controlado;
19. backup, observabilidade e rotinas operacionais.

## 3. Perfis e atores

### 3.1 Usuários do sistema

| Perfil | Responsabilidade principal |
|---|---|
| Administrador | Usuários, permissões, regras, cadastros e operação total |
| Financeiro | Pagamentos, fechamentos, ajustes, descontos e relatórios financeiros |
| Operação | Propostas, pagamentos e manutenção operacional permitida |
| Gestor | Dashboard, relatórios, equipes e exportações |
| Auditor | Consulta de dados, logs, cálculos e histórico, sem mutação |
| Restrito | Consulta dos módulos explicitamente liberados |
| Worker do sistema | PDFs, lotes, recálculos, backups e rotinas agendadas |

### 3.2 Colaboradores comissionados

Colaborador não é obrigatoriamente um usuário de acesso. É uma entidade operacional/financeira.

Papéis observados:

- `CONSULTOR`;
- `CONSULTOR_MEI_ESCALONADO`;
- `LIDER`;
- `CONSULTOR_LIDER`, se a operação exigir acumular os dois papéis;
- `LIDER_MEI_GERAL`;
- `BKO`;
- `FINALIZACAO`;
- `LIDER_FINALIZACAO`.

Regimes:

- `MEI`;
- `CLT`.

Na reconstrução, recomenda-se modelar papéis em uma tabela associativa `collaborator_roles`, em vez de um único campo de texto. Isso permite que uma pessoa exerça mais de uma função sem criar um enum combinatório.

## 4. Princípios arquiteturais

### 4.1 Monólito modular primeiro

O domínio ainda compartilha transações fortes entre proposta, recebimento, comissão e auditoria. Separar isso cedo em microserviços adicionaria consistência eventual, mensageria e operação distribuída sem benefício comprovado.

O desenho recomendado é:

```text
Navegador
   |
   v
Reverse proxy / TLS / WAF
   |
   +----------------------+
   |                      |
   v                      v
Frontend SPA          API modular
                          |
           +--------------+---------------+
           |              |               |
           v              v               v
        MySQL 8         Redis          Object Storage
           ^              ^               ^
           |              |               |
           +----------- Worker -----------+
                       PDFs/lotes/jobs
```

### 4.2 Fonte única de verdade

- Valores financeiros são calculados no backend.
- O frontend nunca recalcula produção, comissão ou fechamento.
- PDF e tela consomem o mesmo DTO de relatório.
- Regras aplicadas são persistidas como snapshot/versionamento.
- Toda mutação financeira produz auditoria.

### 4.3 Consistência transacional

Uma operação de pagamento deve confirmar, em uma única transação:

1. registro do pagamento;
2. atualização dos totais da proposta;
3. mudança de status;
4. lançamentos de comissão derivados;
5. auditoria;
6. evento de integração/outbox.

Se qualquer etapa falhar, tudo deve sofrer rollback.

### 4.4 Tempo e dinheiro

- Armazenar instantes em UTC com timezone.
- Exibir e interpretar datas operacionais em `America/Sao_Paulo`.
- Separar `business_date` de `occurred_at`.
- Usar `DECIMAL/NUMERIC`, nunca `float`, para persistência e cálculo.
- Arredondar dinheiro com `ROUND_HALF_UP` e duas casas apenas nos pontos definidos.

## 5. Bounded contexts e módulos

| Módulo | Responsabilidade | Dono dos dados |
|---|---|---|
| Identity & Access | Usuários, sessão, RBAC, revogação | `users`, `roles`, `permissions`, `sessions` |
| Organization | Colaboradores, papéis, empresas, unidades, PIX | `collaborators`, `companies`, `units` |
| Team Management | Vínculos temporais consultor-líder | `team_assignments` |
| Commercial | Propostas e dados do cliente/operação | `proposals` |
| Receivables | Pagamentos, estornos e conciliação | `receipts`, `receipt_reversals` |
| Commission Rules | Regras e versões de comissionamento | `commission_rule_sets`, `commission_rules` |
| Commission Engine | Cálculo determinístico e lançamentos | `commission_entries`, snapshots |
| Settlement | Fechamento e pagamento real de comissão | `settlements`, `settlement_items` |
| Period Management | Semanas, cortes e fechamentos | `accounting_periods` |
| Reporting | Read models, dashboard e relatórios | views/materialized views/cache |
| Documents | HTML, PDF, ZIP e arquivos | `document_jobs`, object storage |
| Audit & Compliance | Logs imutáveis e trilha explicativa | `audit_events` |
| Operations | Backup, health, jobs e integridade | metadados operacionais |

Dependências permitidas:

```text
Identity ───────────────┐
Organization ──> Teams  |
      |             |   |
      v             v   v
Commercial ──> Receivables ──> Commission Engine
                       |              |
Commission Rules ──────┘              v
Period Management ───────────────> Settlement
      |                                |
      +----------> Reporting <---------+
                       |
                       v
                   Documents

Todas as mutações relevantes ──> Audit/Outbox
```

## 6. Design patterns recomendados

### 6.1 Clean/Hexagonal Architecture

Cada módulo deve ter quatro áreas:

```text
module/
|-- domain/          # entidades, value objects, policies e eventos
|-- application/     # commands, queries, use cases e portas
|-- infrastructure/  # SQLAlchemy, Redis, storage, filas e integrações
`-- api/             # controllers, DTOs e autorização HTTP
```

O domínio não importa FastAPI, SQLAlchemy, Redis ou bibliotecas de PDF.

### 6.2 DDD pragmático

Usar DDD onde existe regra real:

- aggregates: `Proposal`, `Settlement`, `AccountingPeriod`, `RuleSet`;
- entities: `Receipt`, `TeamAssignment`, `CommissionEntry`;
- value objects: `Money`, `Percentage`, `DateRange`, `Document`, `RuleVersion`;
- domain services: comissão proporcional, rateio marginal, atribuição histórica de líder;
- domain events: pagamento confirmado, proposta quitada, período fechado.

Não criar abstrações DDD para CRUD simples como catálogo de bancos.

### 6.3 Command Query Separation/CQRS leve

- Commands alteram estado e passam por autorização/transação.
- Queries usam projeções otimizadas e não alteram estado.
- Não é necessário banco separado inicialmente.
- Relatórios pesados podem usar views/materialized tables atualizadas por eventos.

### 6.4 Strategy + Factory para comissão

```text
CommissionStrategy
|-- StandardConsultantStrategy
|-- ScaledMeiStrategy
|-- CommercialLeaderStrategy
|-- GeneralMeiLeaderStrategy
|-- FinalizationStrategy
|-- FinalizationLeaderStrategy
`-- ManualAdjustmentStrategy
```

Uma `CommissionStrategyFactory` escolhe a estratégia pelo papel, regime, data de vigência e versão da regra.

### 6.5 Specification/Policy

Políticas reutilizáveis:

- `EligibleReceiptSpecification`;
- `LeaderAssignmentAtDateSpecification`;
- `CommissionRuleEffectiveAtSpecification`;
- `CanClosePeriodPolicy`;
- `CanModifyFinancialResourcePolicy`;
- `ProposalSettlementStatusPolicy`.

Isso evita filtros diferentes entre dashboard e relatório.

### 6.6 Unit of Work

Use cases financeiros recebem uma `UnitOfWork`:

```python
with uow:
    proposal = uow.proposals.get_for_update(proposal_id)
    receipt = proposal.register_receipt(command)
    uow.receipts.add(receipt)
    uow.commissions.add_all(engine.calculate(receipt))
    uow.audit.append(...)
    uow.outbox.append(...)
    uow.commit()
```

Repositórios não executam `commit`; somente a Unit of Work controla a transação.

### 6.7 State Machine

Estados devem ser enum e ter transições explícitas.

Proposta:

```text
OPEN --recebimento parcial--> PARTIALLY_PAID
OPEN/PARTIALLY_PAID --quitação--> PAID
PAID --estorno--> PARTIALLY_PAID ou OPEN
qualquer estado permitido --cancelamento--> CANCELLED
```

Fechamento de comissão:

```text
DRAFT -> REVIEWED -> APPROVED -> PAID
              |          |
              v          v
           REOPENED    PARTIALLY_PAID
```

Job:

```text
PENDING -> RUNNING -> SUCCEEDED
                  -> PARTIAL
                  -> FAILED
                  -> CANCELLED
```

### 6.8 Outbox Pattern

Eventos destinados a worker/cache/documentos são gravados em `outbox_events` na mesma transação do negócio. Um dispatcher publica no Redis/stream e marca o evento como processado.

Isso impede perder um job de PDF ou recálculo após confirmar uma transação.

### 6.9 Adapter e Anti-Corruption Layer

Integrações com Redmine, email, object storage, banco e geradores de PDF ficam atrás de portas. Importação de dados legados usa uma ACL para converter `sales/propostas` no modelo canônico sem contaminar o domínio novo.

## 7. Funcionalidades detalhadas

### 7.1 Identidade, autenticação e usuários

### Funcionalidades

- login por email e senha;
- access token curto;
- refresh token rotativo;
- logout/revogação;
- criação e edição de usuário por administrador;
- ativação/inativação;
- redefinição de senha;
- associação de papéis e permissões;
- histórico de login e alterações administrativas;
- proteção contra força bruta.

### Regras

- não existe cadastro público com escolha de privilégio;
- primeiro administrador é criado por comando de bootstrap único;
- senha nunca é armazenada em texto;
- refresh token é armazenado apenas como hash;
- desativar usuário revoga todas as sessões;
- autorização ocorre no backend em todas as rotas;
- operações sensíveis exigem permissão, não apenas “usuário autenticado”.

### Permissões sugeridas

```text
users.read, users.write
collaborators.read, collaborators.write
proposals.read, proposals.write, proposals.delete
receipts.read, receipts.write, receipts.reverse
rules.read, rules.write, rules.activate
periods.read, periods.close, periods.reopen
settlements.read, settlements.write, settlements.approve, settlements.pay
reports.read, reports.export
audit.read
operations.backup
```

### 7.2 Empresas, unidades e colaboradores

### Funcionalidades

- CRUD de empresas e unidades;
- cadastro de colaborador;
- CPF/CNPJ, nome, empresa, unidade e regime;
- uma ou mais funções operacionais;
- chave PIX e tipo;
- override individual de percentual;
- ativação/inativação com data e motivo;
- consulta de histórico cadastral;
- filtro por papel, regime, unidade, empresa e situação.

### Regras

- documento normalizado e único;
- PIX é dado sensível e deve ser mascarado em consultas sem permissão financeira;
- papel e regime são versionáveis quando afetam cálculo histórico;
- inativação encerra vínculos ativos ou exige confirmação transacional;
- colaborador inativo não recebe novos vínculos/propostas;
- alterações não mudam snapshots históricos já fechados.

### 7.3 Vínculo consultor-líder

### Funcionalidades

- vincular consultor a líder com início de vigência;
- transferir consultor, encerrando o vínculo anterior;
- consultar equipe atual e histórica;
- remover/corrigir vínculo com motivo e auditoria;
- obter líder válido na data de negócio ou primeiro recebimento.

### Invariantes

- um consultor tem no máximo um líder comercial ativo por tipo de vínculo;
- intervalos do mesmo tipo não se sobrepõem;
- `start_date <= end_date`;
- consultor e líder precisam estar ativos na criação;
- papéis precisam ser compatíveis;
- transferência fecha o anterior em `new_start - 1 day`, se intervalos forem inclusivos;
- a convenção de inclusividade deve ser única e testada.

### Consulta histórica

```text
assignment.start_date <= reference_date
AND (assignment.end_date IS NULL OR assignment.end_date >= reference_date)
```

### 7.4 Propostas

### Funcionalidades

- criar proposta;
- cadastrar cliente, documento, valor, TPS, data de negócio e Redmine;
- associar consultor, BKO e finalização por ID;
- pagamento inicial opcional;
- editar campos permitidos;
- listar, paginar, ordenar e filtrar;
- consultar detalhes e pagamentos;
- cancelar/excluir conforme política;
- recálculo controlado;
- exportar propostas.

### Campos canônicos

```text
id
external_id/redmine_id
consultant_id
business_date
customer_name
customer_document_encrypted/hash_for_search
operation_amount
tps_percentage
company_commission_amount
paid_amount_cached
outstanding_amount_cached
status
bko_collaborator_id
finalizer_collaborator_id
commission_snapshot_id
version
created_at/created_by
updated_at/updated_by
settled_at/cancelled_at
```

### Regras

- valor da operação > 0;
- TPS entre 0 e 100;
- comissão da empresa = operação × TPS / 100;
- Redmine/external ID único quando preenchido;
- documento deve ser validado e normalizado;
- alteração de valor/TPS recalcula somente se o período ainda estiver aberto;
- período fechado exige correção compensatória, não edição destrutiva;
- controle otimista por `version` evita sobrescrita concorrente.

### Tolerância observada

O sistema atual considera quitada uma proposta com diferença de até R$ 10,00 abaixo ou R$ 100,00 acima da comissão da empresa. Na reconstrução, isso deve ser uma `SettlementTolerancePolicy` versionada e configurável, pois é uma regra financeira e não deve ficar como constante duplicada.

### 7.5 Recebimentos e estornos

### Funcionalidades

- registrar recebimento parcial/total;
- data e hora efetiva;
- tipo: PIX, TED, boleto ou catálogo configurável;
- banco/conta de destino;
- referência da tarefa/Redmine;
- observação e operador;
- confirmar, liquidar ou deixar pendente;
- editar metadados quando permitido;
- estornar total ou parcialmente;
- consultar por proposta e período;
- conciliar com conta bancária.

### Estados canônicos

- `PENDING`: não afeta caixa/comissão;
- `CONFIRMED`: afeta caixa e comissão;
- `SETTLED`: conciliado, afeta caixa e comissão;
- `REVERSED`: efeito compensado por estorno;
- `CANCELLED`: não produz efeito.

Uma única `EligibleReceiptSpecification` deve ser usada por proposta, dashboard, comissão e relatório.

### Atomicidade e idempotência

- endpoint aceita `Idempotency-Key`;
- chave + usuário + operação possuem constraint única;
- proposta é carregada com lock;
- valor confirmado é consolidado no mesmo commit;
- estorno cria lançamento negativo/compensatório; não apaga o original;
- nenhum pagamento financeiro é removido fisicamente após confirmado.

### Evento

```json
{
  "event": "receivable.receipt_confirmed.v1",
  "aggregate_id": 123,
  "occurred_at": "2026-08-11T13:00:00Z",
  "payload": {
    "proposal_id": 45,
    "amount": "1000.00",
    "business_date": "2026-08-11"
  }
}
```

### 7.6 Motor de comissionamento

### Pipeline

```text
Receipt elegível
-> carrega proposta e snapshot organizacional
-> resolve período contábil
-> resolve conjunto de regras vigente
-> seleciona Strategy
-> calcula entradas detalhadas
-> valida soma/arredondamento
-> persiste CommissionEntry imutável
-> emite evento para read models/settlement
```

### Regra padrão observada

Base:

```text
company_commission = operation_amount × TPS / 100
```

Faixas padrão do consultor, configuráveis:

| TPS | Percentual do consultor sobre a comissão da empresa |
|---|---:|
| >= 35% | 12% |
| 30% a 34,99% | 10% |
| 25% a 29,99% | 8% |
| < 25% | 6% |

Comissão proporcional ao recebimento:

```text
eligible_ratio = min(receipt_amount / company_commission, 1)
consultant_commission_for_receipt = consultant_total_commission × eligible_ratio
```

Para múltiplos recebimentos, o motor deve limitar a base acumulada ao saldo elegível restante para impedir pagamento acima de 100%.

### CLT

O sistema atual permite tabela CLT separada, embora os defaults coincidam com MEI. A reconstrução deve manter regras por regime e data. Percentual zero é válido para perfis que não recebem determinada comissão.

### Override individual

É permitido percentual individual para TPS >= 35%. Deve possuir:

- vigência;
- motivo;
- aprovador;
- auditoria;
- efeito apenas em períodos abertos/futuros.

### Snapshot obrigatório

Cada cálculo persiste:

- rule set/version;
- estratégia;
- base da empresa;
- base do beneficiário;
- percentuais;
- segmentos;
- acumulado anterior/posterior;
- valor final;
- origem (pagamento, estorno, manual, recálculo);
- hash dos inputs relevantes.

### 7.7 MEI Escalonado

### Conceito

Cruza produção mensal acumulada e TPS. Se uma proposta ultrapassa o limite de uma faixa, ela é dividida marginalmente em segmentos.

Exemplo conceitual:

```text
acumulado antes: R$ 70.000
proposta:         R$ 20.000
limite faixa 1:   R$ 75.000

segmento 1: R$ 5.000 na faixa 1
segmento 2: R$ 15.000 na faixa 2
```

Para cada segmento:

```text
company_commission_segment = production_segment × TPS / 100
consultant_commission_segment = company_commission_segment × rule_percentage / 100
```

### Requisitos

- regras com `production_min/max`, `tps_min/max`, percentual e versão;
- proibir lacunas e sobreposições na ativação;
- rateio determinístico e ordenado;
- acumulado calculado por produção reconhecida/paga, conforme política;
- estorno cria segmentos reversos vinculados aos originais;
- modo de exibição semanal/mensal com vigência;
- faixas de produção continuam mensais, salvo nova regra formal;
- recálculo em lote com dry-run e relatório de diferenças.

### 7.8 Líder comercial

### Regra padrão observada

- vínculo é resolvido pela data do primeiro pagamento da proposta;
- apenas TPS >= 25% gera comissão para líder MEI;
- percentual padrão: 3% sobre a parcela da comissão da empresa liberada pelo recebimento;
- líder CLT tem percentual padrão zero;
- vendas próprias do líder podem ser incluídas/excluídas por política explícita.

Tabela padrão:

| Perfil | TPS | Percentual |
|---|---|---:|
| Líder MEI | >= 25% | 3% |
| Líder MEI | < 25% | 0% |
| Líder CLT | qualquer | 0% |

O líder histórico deve ser persistido na entrada de comissão para que alterações futuras de vínculo não mudem o passado.

### 7.9 Líder MEI geral

### Conceito observado

O líder MEI geral recebe comissão sobre unidades associadas. A base configurável padrão é 35% da produção e os níveis decrescem conforme o volume:

| Nível | Produção | Percentual sobre a base |
|---|---:|---:|
| 1 | 0 a 500.000 | 1,20% |
| 2 | 500.000 a 1.000.000 | 1,00% |
| 3 | 1.000.000 a 1.600.000 | 0,80% |
| 4 | 1.600.000 a 2.400.000 | 0,60% |
| 5 | 2.400.000 a 3.400.000 | 0,40% |
| 6 | 3.400.000 a 4.400.000 | 0,30% |
| 7 | 4.400.000 a 5.400.000 | 0,20% |

Todas as faixas, unidades e bases devem ser versionadas. A ativação deve rejeitar lacunas, conflitos e líderes/unidades inativos.

### 7.10 Finalização e líder de finalização

### Finalização

Regra observada:

```text
se produção < 70.000: comissão = 0
se produção >= 70.000:
    comissão = 500 + (produção - 70.000) × 0,0045
```

Pode existir bônus manual por pessoa/período. O bônus deve ser um lançamento separado, não alteração do cálculo base.

### Líder de finalização

Regra padrão observada:

```text
commission = team_production × 0,90%
net_commission = commission - approved_discount
```

O percentual é configurável por regime/papel. Desconto exige motivo, autor, aprovador e nunca pode apagar o valor bruto.

### 7.11 BKO e ajustes manuais

### Funcionalidades

- lançar comissão manual de BKO por data/período;
- consultar total do período;
- impedir comissão manual para BKO CLT, se a regra permanecer;
- lançar bônus de finalização;
- lançar desconto de líder de finalização;
- manter histórico de revisões/aprovações.

### Modelo recomendado

Usar `manual_adjustments` com:

```text
beneficiary_id
adjustment_type
period_id
amount (positivo ou negativo conforme tipo)
reason
requested_by
approved_by
status
created_at/approved_at
```

Evitar tabelas diferentes para cada tipo se todas compartilham o mesmo lifecycle.

### 7.12 Períodos, reset e fechamento semanal

### Funcionalidades

- criar períodos semanais;
- definir início, fim e cutoff exato;
- listar semanas atuais/anteriores;
- revisar prévia;
- fechar período;
- reabrir mediante permissão e motivo;
- congelar snapshot do fechamento;
- impedir edição retroativa direta.

### Modelo

```text
AccountingPeriod
id
type = WEEKLY|MONTHLY
start_date
end_date
cutoff_at
timezone
status = OPEN|REVIEW|CLOSED|REOPENED
closed_at/closed_by
reopened_at/reopened_by/reason
version
```

### Regras

- períodos do mesmo tipo não se sobrepõem;
- pagamentos na data de corte usam `occurred_at` para decidir a pertença;
- fechar gera/atualiza settlements em uma transação/job controlado;
- dados fechados ficam imutáveis; correções são compensatórias;
- fechamento é idempotente.

### 7.13 Fechamento e pagamento de comissões

### Funcionalidades

- gerar fechamento por beneficiário/período;
- exibir calculado, pago, adiado, estornado e descontado;
- marcar como revisado/aprovado;
- pagamento integral/parcial;
- adiar saldo;
- aplicar acumulado futuro;
- registrar forma, data e referência de pagamento;
- exportar relatório de pagamento;
- reembolsar/estornar com trilha.

### Modelo contábil recomendado

`CommissionEntry` é o razão imutável do cálculo. `SettlementItem` seleciona as entradas incluídas no fechamento. `PayoutTransaction` representa dinheiro efetivamente pago.

```text
CommissionEntry -> SettlementItem -> Settlement -> PayoutTransaction
     cálculo          composição       aprovação       pagamento real
```

Assim, “calculado”, “a pagar” e “pago” nunca são confundidos.

### 7.14 Dashboard e métricas

### Indicadores

- produção semanal/mensal;
- faturamento recebido;
- comissão da empresa;
- comissão prevista e efetiva de consultores;
- comissão de líderes;
- comissão BKO/finalização;
- faturamento líquido;
- propostas abertas, parciais e quitadas;
- pendência financeira;
- TPS médio e distribuição;
- ranking de consultores e líderes;
- metas e projeções;
- tendências temporais.

### Arquitetura

Dashboard consulta read models, não executa milhares de cálculos em tempo real. Eventos de pagamento/comissão atualizam projeções. Deve existir endpoint de reconciliação que compara projeção com fonte transacional.

### 7.15 Relatórios

### Escopos

- individual;
- equipe/líder;
- unidade;
- empresa;
- geral;
- financeiro executivo;
- inadimplência;
- BKO;
- finalização;
- líder de finalização;
- auditoria de cálculo e entidade.

### Saídas

- JSON para tela;
- HTML para preview;
- PDF individual;
- ZIP de PDFs por consultor/líder;
- XLSX/CSV de dados tabulares;
- job em lote com progresso e download.

### Regra arquitetural

O mesmo `ReportViewModel` alimenta tela, HTML, PDF e exportação. Filtros, totais e arredondamentos não podem ser reimplementados no template ou frontend.

### 7.16 Auditoria e recálculo

### Auditoria

Registrar:

- ator e sessão;
- ação;
- entidade e ID;
- antes/depois com redaction de segredos;
- timestamp UTC;
- IP/user agent/correlation ID;
- motivo;
- regra/versão usada;
- origem: UI, API, job, migration ou suporte.

Logs financeiros devem ser append-only e protegidos contra alteração por usuários comuns.

### Recálculo

Fluxo seguro:

```text
selecionar escopo
-> dry-run
-> gerar diff antigo/novo
-> aprovação
-> criar entradas compensatórias
-> atualizar read models
-> publicar relatório de execução
```

Nunca sobrescrever silenciosamente histórico fechado.

## 8. Modelo de dados canônico

### 8.1 Identidade

| Tabela | Finalidade |
|---|---|
| `users` | Conta de acesso |
| `roles` | Papéis de acesso |
| `permissions` | Capacidades atômicas |
| `user_roles` | Associação usuário-papel |
| `role_permissions` | Associação papel-permissão |
| `sessions` | Refresh tokens, expiração e revogação |
| `login_attempts` | Rate limit e investigação |

### 8.2 Organização

| Tabela | Finalidade |
|---|---|
| `companies` | Empresas |
| `units` | Unidades vinculadas à empresa |
| `collaborators` | Pessoa operacional/financeira |
| `collaborator_roles` | Funções com vigência |
| `collaborator_payment_keys` | PIX protegido/versionado |
| `team_assignments` | Vínculo temporal consultor-líder |
| `bank_accounts` | Contas de destino |

### 8.3 Comercial e recebíveis

| Tabela | Finalidade |
|---|---|
| `customers` | Cliente deduplicado, se necessário |
| `proposals` | Aggregate comercial canônico |
| `receipts` | Recebimentos e lançamentos compensatórios |
| `receipt_reversals` | Relação de estorno com original |
| `idempotency_keys` | Proteção de comandos repetidos |

### 8.4 Comissionamento

| Tabela | Finalidade |
|---|---|
| `commission_rule_sets` | Cabeçalho da versão de regras |
| `commission_rules` | Faixas genéricas por estratégia |
| `commission_rule_assignments` | Papel/regime/pessoa/unidade e vigência |
| `commission_calculation_snapshots` | Input/output explicável |
| `commission_entries` | Razão imutável de créditos/débitos |
| `manual_adjustments` | Ajustes com aprovação |

### 8.5 Períodos e fechamento

| Tabela | Finalidade |
|---|---|
| `accounting_periods` | Semanas/meses e cutoff |
| `settlements` | Fechamento por beneficiário/período |
| `settlement_items` | Entradas incluídas |
| `payout_transactions` | Pagamento real |

### 8.6 Plataforma

| Tabela | Finalidade |
|---|---|
| `audit_events` | Auditoria append-only |
| `outbox_events` | Entrega confiável de eventos |
| `document_jobs` | Estado de PDF/ZIP/exportação |
| `stored_documents` | Metadados de arquivos |
| `data_integrity_checks` | Resultado de verificações periódicas |

### 8.7 Constraints essenciais

- `users.email` único e normalizado;
- `collaborators.document_hash` único;
- `proposals.external_id` único quando não nulo;
- `receipts.idempotency_key` único no escopo;
- `team_assignments` sem sobreposição por consultor/tipo;
- regras sem lacuna/sobreposição dentro do mesmo conjunto;
- um settlement por beneficiário/período/versão;
- um item não pode pertencer a dois settlements ativos;
- `amount != 0` em entradas contábeis;
- FKs com política de delete explícita;
- financeiro usa soft-delete/cancelamento, nunca cascade destrutivo.

## 9. Contratos de API

### 9.1 Convenções

- prefixo `/api/v1`;
- JSON em `snake_case` ou `camelCase`, escolhido uma vez;
- datas `YYYY-MM-DD`;
- instantes ISO 8601 UTC;
- dinheiro como string decimal em APIs críticas (`"1234.56"`);
- paginação por cursor para listas grandes;
- `Idempotency-Key` em comandos financeiros;
- `ETag`/`version` para concorrência otimista;
- `X-Correlation-ID` em request/response;
- erros no padrão Problem Details (`application/problem+json`);
- OpenAPI gerado e validado no CI.

### 9.2 Superfícies sugeridas

| Grupo | Operações principais |
|---|---|
| `/auth` | login, refresh, logout, me |
| `/users` | listar, criar, editar, papéis, revogar sessões |
| `/companies` e `/units` | CRUD organizacional |
| `/collaborators` | CRUD, ativação, papéis, histórico |
| `/team-assignments` | vincular, transferir, encerrar, histórico |
| `/proposals` | criar, editar, listar, detalhes, cancelar, exportar |
| `/proposals/{id}/receipts` | registrar, listar, confirmar e estornar |
| `/commission-rules` | versões, faixas, validação, ativação |
| `/commission-calculations` | preview, explicar e dry-run |
| `/periods` | listar, criar, fechar, reabrir |
| `/settlements` | gerar, revisar, aprovar, pagar, adiar, estornar |
| `/dashboard` | overview, rankings, tendências e metas |
| `/reports` | consultas por escopo e exportações |
| `/document-jobs` | criar, acompanhar e baixar |
| `/audit-events` | consulta por entidade/ator/período |
| `/admin` | integridade, recálculo e operações controladas |

### 9.3 Exemplo de erro

```json
{
  "type": "https://rfbalance/errors/period-closed",
  "title": "Período fechado",
  "status": 409,
  "detail": "A proposta pertence a um período já fechado.",
  "instance": "/api/v1/proposals/123",
  "correlation_id": "01J...",
  "errors": []
}
```

### 9.4 Versionamento de contrato

- alterações aditivas permanecem em v1;
- remoções/semântica incompatível exigem v2 ou janela de depreciação;
- frontend usa client TypeScript gerado do OpenAPI;
- contract tests impedem divergência entre backend e frontend.

## 10. Frontend

### 10.1 Stack sugerida

- React + TypeScript + Vite;
- React Router;
- TanStack Query para estado remoto;
- React Hook Form + Zod;
- biblioteca de componentes acessíveis;
- client gerado do OpenAPI;
- Playwright para E2E;
- Vitest + Testing Library para componentes.

### 10.2 Organização por feature

```text
src/
|-- app/                  # bootstrap, router, providers
|-- features/
|   |-- auth/
|   |-- collaborators/
|   |-- teams/
|   |-- proposals/
|   |-- receipts/
|   |-- commission-rules/
|   |-- settlements/
|   |-- dashboard/
|   |-- reports/
|   `-- audit/
|-- shared/
|   |-- api/              # client gerado/interceptors
|   |-- components/
|   |-- formatters/
|   |-- hooks/
|   `-- types/
`-- main.tsx
```

Cada feature contém `pages`, `components`, `queries`, `mutations`, `schemas` e testes.

### 10.3 Rotas

```text
/login
/dashboard
/collaborators
/collaborators/:id
/teams
/proposals
/proposals/new
/proposals/:id
/commission-rules
/periods
/settlements
/reports
/audit
/admin/users
/admin/operations
```

### 10.4 Estado

- servidor: TanStack Query;
- formulário: React Hook Form;
- UI local: `useState`/context pequeno;
- autenticação: provider derivado de `/auth/me`;
- não duplicar payload financeiro em store global;
- invalidação por query keys após mutações;
- jobs usam polling com backoff ou Server-Sent Events.

### 10.5 Segurança do cliente

- preferir refresh token em cookie HttpOnly/Secure/SameSite;
- access token apenas em memória ou cookie conforme arquitetura;
- CSP restritiva;
- nenhuma autorização depende de esconder botão;
- mascarar PII por permissão;
- sanitizar conteúdo usado em HTML/PDF;
- não logar tokens ou payloads sensíveis.

### 10.6 UX obrigatória

- confirmação para ação financeira;
- feedback de idempotência/reenvio;
- indicação de período fechado;
- diff antes de recálculo;
- estados vazios, erro e loading;
- filtros refletidos na URL;
- acessibilidade WCAG 2.1 AA;
- exportações assíncronas com progresso.

## 11. Backend

### 11.1 Stack

- Python 3.12+;
- FastAPI;
- Pydantic v2 com `ConfigDict`;
- SQLAlchemy 2;
- Alembic;
- MySQL 8 para compatibilidade inicial;
- Redis para fila, locks curtos e cache;
- worker Celery, Dramatiq ou RQ — escolher um;
- Jinja2 + WeasyPrint para PDFs oficiais.

PostgreSQL é uma alternativa superior para constraints de intervalos e recursos analíticos, mas migrar banco e domínio ao mesmo tempo aumenta risco. A opção eficiente é reconstruir primeiro sobre MySQL 8 e tratar migração de SGBD como ADR separado.

### 11.2 Estrutura

```text
backend/
|-- app/
|   |-- modules/
|   |   |-- identity/
|   |   |-- organization/
|   |   |-- teams/
|   |   |-- commercial/
|   |   |-- receivables/
|   |   |-- commissions/
|   |   |-- settlements/
|   |   |-- periods/
|   |   |-- reporting/
|   |   |-- documents/
|   |   `-- audit/
|   |-- platform/         # config, db, bus, observability
|   `-- main.py
|-- migrations/
|-- tests/
|   |-- unit/
|   |-- integration/
|   |-- contract/
|   `-- e2e/
`-- pyproject.toml
```

### 11.3 Regras para controllers

Controller apenas:

1. autentica/autoriza;
2. valida DTO;
3. cria command/query;
4. chama handler;
5. converte resultado em response.

Não consulta ORM diretamente nem calcula comissão.

### 11.4 Jobs

Jobs assíncronos:

- PDF/ZIP em lote;
- exportação XLSX grande;
- recálculo massivo;
- atualização/reconciliação de read models;
- backup;
- verificação de integridade;
- limpeza de documentos expirados.

Cada job precisa de idempotência, retry exponencial, timeout, progresso, erro persistido e dead-letter policy.

## 12. Infraestrutura

### 12.1 Ambientes

- `local`: Docker Compose e dados sintéticos;
- `test`: banco efêmero em CI;
- `staging`: réplica funcional sem PII real ou com dados anonimizados;
- `production`: rede privada, TLS, backups e observabilidade.

### 12.2 Containers

| Container | Papel |
|---|---|
| `web` | Nginx/CDN do frontend |
| `api` | FastAPI sem scheduler embutido |
| `worker` | Jobs assíncronos |
| `scheduler` | Agenda única de tarefas |
| `db` | MySQL gerenciado ou container apenas local |
| `redis` | fila/cache/locks |
| `object-storage` | S3/MinIO para PDFs/backups |
| `otel-collector` | telemetria, se adotado |

### 12.3 Topologia de produção

```text
Internet
  |
CDN/WAF/TLS
  |
Load Balancer / Reverse Proxy
  |-------------------|
Frontend estático     API replicas
                         |
             private network/subnet
          |          |          |
       MySQL      Redis      Workers
          |                     |
       backups             Object Storage
```

Banco, Redis e storage não devem ter porta pública.

### 12.4 Configuração e segredos

- variáveis não sensíveis por environment/config map;
- segredos em secret manager;
- nunca em Dockerfile, Compose versionado ou frontend;
- rotação documentada;
- `SECRET_KEY` distinta por ambiente;
- credenciais de banco com menor privilégio;
- conta separada para migration;
- validação fail-fast no startup.

Variáveis principais:

```text
APP_ENV
DATABASE_URL
REDIS_URL
JWT_PRIVATE_KEY/JWT_PUBLIC_KEY
ACCESS_TOKEN_TTL
REFRESH_TOKEN_TTL
OBJECT_STORAGE_ENDPOINT/BUCKET
OTEL_EXPORTER_OTLP_ENDPOINT
SENTRY_DSN ou equivalente
BACKUP_BUCKET/RETENTION
APP_TIMEZONE=America/Sao_Paulo
```

### 12.5 Health checks

- `/health/live`: processo responde, sem dependências;
- `/health/ready`: banco, migração esperada, Redis e storage essenciais;
- worker publica heartbeat;
- scheduler possui singleton/leader election.

### 12.6 Backup e disaster recovery

- backup diário completo;
- binlog/PITR quando disponível;
- criptografia em trânsito e repouso;
- retenção diária/semanal/mensal;
- cópia em região/conta separada;
- teste automático de integridade;
- restauração ensaiada trimestralmente;
- runbook com RPO/RTO.

Meta inicial sugerida:

- RPO <= 24h; ideal <= 15 min com binlog;
- RTO <= 4h; ideal <= 1h.

## 13. Segurança

### 13.1 Controles obrigatórios

- deny by default nas rotas;
- RBAC no backend;
- rate limiting no login e comandos caros;
- Argon2id ou bcrypt com custo revisado;
- refresh rotation e revogação;
- TLS obrigatório;
- CSP/HSTS/Referrer-Policy/Permissions-Policy;
- proteção de PII por criptografia/masking;
- logs sem segredos;
- dependências auditadas;
- imagens de container sem root e com versões fixadas;
- CSRF se autenticação usar cookie;
- CORS com allowlist exata;
- validação de upload/exportação;
- auditoria de ações administrativas.

### 13.2 Matriz resumida

| Recurso | Admin | Financeiro | Operação | Gestor | Auditor |
|---|---:|---:|---:|---:|---:|
| Usuários | RW | - | - | - | R |
| Colaboradores | RW | R | RW limitado | R | R |
| Propostas | RW | R | RW | R | R |
| Recebimentos | RW | RW | C/R limitado | R | R |
| Estornos | RW | RW/aprovação | - | R | R |
| Regras | RW/ativar | R | - | R | R |
| Fechamento | RW/aprovar | RW | - | R | R |
| Relatórios | R/export | R/export | R limitado | R/export | R |
| Auditoria | R | R | próprio/limitado | R | R |
| Backup | executar | - | - | - | histórico |

Permissões finais devem ser confirmadas pelo negócio.

### 13.3 LGPD e retenção

- classificar CPF/CNPJ, PIX, emails e dados bancários;
- limitar finalidade e acesso;
- mascarar em UI/logs;
- documentar retenção;
- anonimizar ambientes não produtivos;
- suportar exportação/retificação conforme base legal;
- não apagar registros financeiros sujeitos a retenção legal; anonimizar quando aplicável.

## 14. Observabilidade

### 14.1 Logs estruturados

JSON com:

```text
timestamp
level
service/module
environment
correlation_id
user_id
route/use_case
aggregate_id
duration_ms
outcome
error_code
```

### 14.2 Métricas

- requests, latência p50/p95/p99 e erros;
- pool/conexões do banco;
- jobs pendentes, duração, retry e falha;
- PDFs gerados e tamanho;
- logins falhos;
- fechamentos pendentes;
- divergências de integridade;
- tempo de cálculo de relatório;
- cache hit rate.

### 14.3 Tracing

OpenTelemetry entre proxy, API, worker, banco e storage. O `correlation_id` deve chegar ao audit event e ao job.

### 14.4 Alertas

- erro 5xx sustentado;
- readiness falhando;
- fila acumulada;
- backup ausente/falhou;
- migration divergente;
- integridade financeira divergente;
- crescimento anormal de login falho;
- storage próximo do limite.

## 15. Requisitos não funcionais

### Disponibilidade e desempenho iniciais

- disponibilidade mensal: 99,5%;
- API de CRUD p95 < 500 ms;
- dashboard cached p95 < 2 s;
- relatório interativo p95 < 5 s;
- job de lote não bloqueia API;
- paginação obrigatória;
- operações financeiras idempotentes.

### Escalabilidade

- API stateless e horizontal;
- worker escalável por fila;
- índices por período, status, beneficiário e proposta;
- read models para agregações;
- object storage para arquivos;
- cache somente para dados reconstruíveis;
- sem sessão local ou arquivo definitivo no container.

### Acessibilidade e compatibilidade

- WCAG 2.1 AA;
- browsers corporativos suportados documentados;
- layout responsivo;
- PDFs com fontes incorporadas e testes de snapshot.

## 16. Estratégia de testes

### 16.1 Pirâmide

1. testes unitários de domínio;
2. testes de integração com banco real compatível;
3. contract tests API/OpenAPI;
4. testes de componente frontend;
5. E2E dos fluxos principais;
6. testes de carga e segurança.

### 16.2 Casos obrigatórios de domínio

- limites exatos de TPS;
- limites exatos de faixas de produção;
- proposta cruzando uma ou várias faixas;
- múltiplos pagamentos parciais;
- pagamento acima/abaixo da tolerância;
- pagamento pendente não afetando resultado;
- estorno parcial/total;
- arredondamento e soma dos segmentos;
- vínculo que muda na fronteira de data;
- período com cutoff no mesmo dia;
- líder CLT/MEI;
- colaborador inativo;
- regra que muda por vigência;
- recálculo produzindo compensação;
- idempotência e concorrência.

### 16.3 Testes de autorização

Para cada rota:

- sem token -> 401;
- token inválido/expirado -> 401;
- autenticado sem permissão -> 403;
- perfil correto -> sucesso;
- acesso a PII é mascarado conforme permissão.

### 16.4 Testes de integração financeira

- dois pagamentos simultâneos preservam soma;
- falha no audit/outbox reverte a transação;
- retry com mesma idempotency key não duplica;
- fechamento executado duas vezes não duplica;
- relatório, tela e PDF possuem os mesmos totais;
- read model reconcilia com ledger.

### 16.5 Metas

- domínio financeiro: >= 90%;
- application/use cases: >= 80%;
- total backend: >= 75%;
- frontend crítico: >= 70%;
- 100% dos comandos financeiros com integração e autorização.

## 17. CI/CD

### Pipeline de pull request

```text
format/lint
-> type check
-> unit tests
-> integration tests com MySQL/Redis efêmeros
-> OpenAPI diff/contract tests
-> frontend build
-> npm/pip audit + secret scan
-> migration upgrade/downgrade em banco vazio
-> container build + vulnerability scan
```

### Deploy

```text
build imutável
-> staging
-> smoke/E2E
-> backup/checkpoint
-> migration expand
-> deploy API/worker
-> health/readiness
-> migration contract posterior
-> monitoramento e rollback
```

Usar estratégia expand/contract para migrations compatíveis. Nunca depender de `create_all` em produção.

### Versionamento

- SemVer para aplicação;
- migration IDs lineares/merge revisado;
- rule sets com versão de negócio independente;
- imagens por digest/tag imutável;
- changelog com impacto financeiro.

## 18. Estratégia de reconstrução e migração

### Fase 0 — Descoberta e congelamento semântico

- entrevistar financeiro/operação;
- confirmar regras e exceções;
- definir glossário;
- produzir casos dourados com propostas reais anonimizadas;
- decidir tolerância, data de atribuição do líder e elegibilidade de pagamento;
- registrar ADRs.

### Fase 1 — Fundação

- repositório limpo;
- CI/CD;
- config/secret manager;
- banco/migrations;
- observabilidade;
- identidade/RBAC;
- audit/outbox;
- design system frontend.

### Fase 2 — Organização e comercial

- empresas/unidades;
- colaboradores/papéis;
- vínculos temporais;
- propostas canônicas;
- importador legado em dry-run.

### Fase 3 — Recebíveis

- pagamentos idempotentes;
- estornos;
- state machine;
- reconciliação;
- testes concorrentes.

### Fase 4 — Motor de comissão

- rule sets/versionamento;
- consultor padrão;
- proporcionalidade;
- MEI Escalonado;
- líderes;
- finalização/BKO;
- ledger e explicação do cálculo.

### Fase 5 — Períodos e fechamento

- semanas/cutoff;
- settlements;
- aprovação/pagamento;
- ajustes manuais;
- reabertura/compensação.

### Fase 6 — Relatórios e documentos

- read models;
- dashboard;
- relatórios;
- PDF/HTML/XLSX;
- jobs e storage.

### Fase 7 — Migração e paralelismo

1. extrair legado;
2. normalizar/anonimizar para testes;
3. carregar staging;
4. reconciliar contagens e totais;
5. executar cálculo novo em shadow mode;
6. comparar por proposta/pessoa/período;
7. corrigir diferenças classificadas;
8. ensaiar cutover;
9. congelar escrita antiga;
10. delta final;
11. trocar tráfego;
12. monitorar e manter rollback.

### Reconciliação mínima

- número de colaboradores/propostas/pagamentos;
- soma de operação e comissão da empresa;
- soma recebida por período;
- status e pendência por proposta;
- comissão por beneficiário/regra;
- vínculos históricos;
- settlements e pagamentos reais;
- hash/contagem de auditoria migrada.

### Mapeamento legado para o modelo canônico

| Origem atual | Destino proposto | Estratégia |
|---|---|---|
| `users` | `users`, `user_roles` | Migrar contas ativas; exigir troca/rotação conforme política de segurança |
| `consultants` | `collaborators`, `collaborator_roles`, payment keys | Separar cadastro, funções e PIX; normalizar empresa/unidade |
| `consultor_lider` | `team_assignments` | Validar sobreposição, vigência e pessoas inativas |
| `proposals` | `proposals` canônico | Fonte principal; preservar IDs por `legacy_id` |
| `payments` | `receipts` | Normalizar status, timezone, tipo e estornos |
| `sales` | staging/ACL | Não migrar automaticamente como proposta sem regra de reconciliação |
| `propostas` | staging/ACL | Estrutura legada; deduplicar contra `proposals` antes de importar |
| `mei_commission_ranges`, `clt_commission_ranges` | `commission_rule_sets/rules` | Criar versão inicial com vigência explícita |
| `scaled_mei_commission_ranges`, `scaled_mei_rule_modes` | regras escalonadas versionadas | Validar lacunas e sobreposições |
| `scaled_commission_entries` | `commission_entries` | Migrar como ledger histórico, preservando origem/segmento |
| `leader_commission_ranges` e `lider_niveis` | regras de líder versionadas | Identificar qual estrutura é realmente autoritativa |
| `mei_general_leader_*` | regras/assignments por unidade | Migrar base, níveis e unidades com vigência |
| `monthly_commissions`, `weekly_commissions` | read models ou ledger histórico | Não tratar agregados como fonte se puderem ser reconstruídos |
| `commission_payments` | `settlements`, `payout_transactions` | Separar fechamento de pagamento real e saldos |
| tabelas manuais BKO/finalização/desconto | `manual_adjustments` | Preservar tipo, período, valor e autoria disponível |
| `week_resets` | `accounting_periods` | Converter reset/cutoff em períodos explícitos |
| `proposal_logs` e audit tables | `audit_events` | Unificar schema, preservar payload original em metadata |
| `bank_accounts` | `bank_accounts` | Normalizar e associar empresa/unidade quando aplicável |
| `report_batch_jobs` | `document_jobs` | Migrar apenas jobs ainda necessários; arquivos para object storage |

Toda migração deve manter `legacy_source` e `legacy_id`. Registros ambíguos vão para uma fila de exceção com motivo; o importador não deve escolher silenciosamente entre estruturas duplicadas.

## 19. Estrutura de repositório sugerida

```text
rf-balance/
|-- apps/
|   |-- api/
|   |-- worker/
|   `-- web/
|-- packages/
|   |-- api-client/          # TypeScript gerado
|   |-- design-system/
|   `-- contracts/           # schemas/eventos compartilhados
|-- infrastructure/
|   |-- compose/
|   |-- nginx/
|   |-- terraform/           # se aplicável
|   `-- observability/
|-- docs/
|   |-- architecture/
|   |-- adr/
|   |-- runbooks/
|   `-- business-rules/
|-- scripts/                 # sem senhas/dados reais
|-- .github/workflows/ ou equivalente
|-- Makefile/Taskfile
`-- README.md
```

Pode-se manter frontend/backend em pastas separadas, desde que contratos sejam gerados e o pipeline seja único.

## 20. ADRs que precisam ser registrados

1. monólito modular versus microserviços;
2. MySQL versus PostgreSQL;
3. cookie versus bearer token;
4. Celery versus alternativa de fila;
5. Redis Streams/lista versus broker dedicado;
6. S3/MinIO e política de retenção;
7. ledger imutável e compensação;
8. data usada para produção e atribuição de líder;
9. tolerância de quitação;
10. política de período/cutoff;
11. tratamento de histórico fechado;
12. estratégia de criptografia de PII;
13. modelo de papéis de colaborador;
14. read models síncronos versus eventuais.

## 21. Decisões que o negócio deve confirmar

- produção entra pela data do primeiro pagamento, data de negócio ou outra regra?
- pagamento `CONFIRMED` e `SETTLED` têm o mesmo efeito?
- tolerância de R$ 10 abaixo/R$ 100 acima permanece?
- sobrepagamento vira crédito, pendência ou quitação?
- líder é definido na data da proposta ou primeiro pagamento?
- líder recebe sobre venda própria?
- CLT recebe comissão de consultor/líder em quais casos?
- MEI Escalonado acumula produção reconhecida ou integral?
- estorno retroativo altera período antigo ou gera compensação no atual?
- quem pode reabrir período e com qual dupla aprovação?
- prazo de retenção de PDFs, PII, auditoria e backups?

Essas respostas devem virar exemplos executáveis e regras versionadas.

## 22. Definition of Done do ecossistema

O sistema reconstruído estará pronto quando:

- houver um único modelo canônico de proposta e pagamento;
- todas as rotas forem autenticadas por padrão;
- RBAC tiver testes por operação;
- pagamentos/estornos forem atômicos e idempotentes;
- motor de comissão for determinístico, versionado e explicável;
- períodos fechados forem imutáveis e correções compensatórias;
- tela, API, PDF e exportação apresentarem totais idênticos;
- read models reconciliarem com o ledger;
- dados legados passarem pela reconciliação definida;
- migrations funcionarem do zero e a partir da versão anterior;
- CI bloquear lint, tipos, testes, secrets e vulnerabilidades críticas;
- backups tiverem restauração testada;
- logs, métricas, tracing e alertas estiverem ativos;
- runbooks de incidente, rollback, backup e recálculo existirem;
- nenhuma credencial ou PII real estiver versionada;
- requisitos de desempenho, acessibilidade e cobertura forem atendidos.

## 23. Ordem recomendada de implementação

```text
Segurança e plataforma
-> organização e vínculos
-> propostas
-> recebimentos atômicos
-> ledger/motor de comissão
-> períodos e settlements
-> read models/dashboard
-> relatórios/documentos
-> migração e cutover
```

Essa ordem prioriza as invariantes que sustentam todo o restante. Relatórios devem ser construídos depois que proposta, recebimento, regra, ledger e período já tiverem semântica estável.

## 24. Referências internas

- `01-ARQUITETURA-GERAL.md`: arquitetura do sistema atual;
- `04-MODELAGEM-BANCO-DADOS.md`: tabelas atuais;
- `05-FUNCIONALIDADES-SISTEMA.md`: inventário funcional atual;
- `06-FLUXO-USO-SISTEMA.md`: jornada operacional;
- `07-DIAGNOSTICO-COMPLETO-SISTEMA-2026-08-11.md`: riscos e estado verificado antes da reconstrução.

Este blueprint deve ser mantido como documento vivo. Cada decisão confirmada pelo negócio deve atualizar a seção correspondente e, quando estrutural, gerar um ADR versionado.
