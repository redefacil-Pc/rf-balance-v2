# RF Balance v2

Ecossistema de operação comercial, recebimentos, comissionamento e fechamento financeiro.

- Especificação normativa: [08-BLUEPRINT-TECNICO-RECONSTRUCAO-ECOSSISTEMA.md](08-BLUEPRINT-TECNICO-RECONSTRUCAO-ECOSSISTEMA.md)
- Plano de execução: [09-PLANO-IMPLEMENTACAO-FASEADO.md](09-PLANO-IMPLEMENTACAO-FASEADO.md)

Estado atual: **F1 a F5 concluídas no código e validadas localmente; F6
parcial**. A validação operacional do setor piloto em produção-staging e a
homologação do comissionamento pelo Financeiro permanecem como gates de
implantação, não como pendências de implementação.

**F1 — fundação**

- Ambiente Docker completo (api, worker, scheduler, web, MySQL, Redis, MinIO), `/health/ready` verde.
- Identidade e RBAC: login por cookie `HttpOnly` com token opaco e rotação ([ADR-0003](docs/adr/0003-sessao-por-cookie-httponly.md)), 33 permissões atômicas, 5 perfis de acesso (`ADMIN`, `FINANCEIRO`, `OPERACIONAL`, `LIDERANCA` e `CONSULTOR`), throttle de login e auditoria append-only.
- Frontend com Mantine: login, shell com navegação filtrada por permissão, rotas protegidas.

**F2 — organização** (empresas, unidades, colaboradores, papéis, vínculos)

- Papéis de colaborador com vigência em tabela associativa e intervalos fechados ([ADR-0013](docs/adr/0013-papeis-de-colaborador-e-intervalos-de-vigencia.md)): transferência fecha o vínculo anterior no dia anterior, sem sobreposição.
- PII cifrada com hash determinístico para busca e deduplicação ([ADR-0012](docs/adr/0012-criptografia-de-pii.md)); documento e PIX mascarados sem `collaborators:read_pii`.
- Telas de usuários, colaboradores (filtros na URL, paginação por cursor, funções com vigência e vínculo com conta), equipes (vínculo, transferência e consulta histórica) e empresas/unidades.

**F2 — propostas** (seção 7.4)

- `proposals` é o aggregate comercial único; a comissão da empresa (`operação * TPS / 100`) é calculada e conferida no servidor, e trafega como string decimal.
- Tolerância de quitação como política versionada ([ADR-0009](docs/adr/0009-tolerancia-de-quitacao-versionada.md)): a versão aplicada fica gravada na proposta, e sobrepagamento quita mas fica sinalizado.
- Alteração com controle otimista por `version` (409 em conflito), cancelamento terminal com motivo, Redmine único e documento do cliente cifrado com hash de busca.
- Tela de propostas com filtros na URL, paginação por cursor, cadastro, alteração, cancelamento, comprovantes e fluxo de envio/aprovação pelo financeiro.

**F2 — importador legado em dry-run** (seção 18)

- ACL sobre o schema real do v1 ([mapeamento](docs/architecture/legado-mapeamento.md)): lê por CSV extraído ou direto do MySQL legado, atrás de uma porta.
- Confere o que o legado afirma contra o que a v2 calcula — comissão e status — e totaliza operação e comissão por origem: é o relatório de divergência.
- Fila de exceção em `legacy_import_issues` para tudo que exigiria adivinhação: documento inválido, `role` fora do catálogo, BKO/finalização citados por nome que não resolve, e as estruturas duplicadas `sales`/`propostas`, que nunca viram proposta canônica sozinhas.
- **Não escreve** no modelo canônico: pedir carga real levanta erro explícito, e um teste prova que as tabelas continuam vazias. [Runbook](docs/runbooks/importacao-legado.md).

**Qualidade:** 155 testes unitários, 163 testes de integração (MySQL, Redis e
storage reais) e 103 testes de frontend, além de `mypy --strict` em 438
arquivos, Ruff, build do frontend e `alembic check` como bloqueios de qualidade.

**F3 — recebíveis concluída.** Recebimentos têm comprovante obrigatório,
horário efetivo, idempotência, conferência exclusiva do Financeiro, bloqueio de
autoconferência e estornos compensatórios totais ou parciais. Pagamento,
recálculo da proposta, auditoria e outbox formam uma única transação. O worker
despacha a outbox via Redis Streams conforme os [ADRs 0004 e
0005](docs/adr/README.md). Somente Financeiro e Operacional com função vigente
de Finalização podem declarar recebimento.

O relatório de encerramento e as evidências estão em
[docs/architecture/fechamento-f1-f3.md](docs/architecture/fechamento-f1-f3.md).

**F4 — motor de comissão concluída.** Rule sets e configurações de estratégia
versionados por vigência alimentam os motores do Consultor padrão, do Consultor
MEI Escalonado e das estratégias de grupo (líder comercial, líder MEI geral,
finalizador e líder de finalização). Cada cálculo grava snapshot com inputs,
outputs, hash, versão e regra aplicada; `commission_entries` é append-only e
estorno gera débito compensatório. Política individual por beneficiário permite
exclusão ou override de TPS. A memória de cálculo é consultável por recebimento
e por proposta. Veja
[docs/architecture/f4-motor-comissao.md](docs/architecture/f4-motor-comissao.md)
e o [roteiro de homologação](docs/11-ROTEIRO-HOMOLOGACAO-COMISSOES.md).

**F5 — períodos e fechamento concluída.** Períodos têm cutoff explícito e, uma
vez fechados, bloqueiam a geração de fechamento no domínio. Settlements são
gerados por beneficiário com desconto, bônus, adiamento e carryover, aceitam
lançamento manual de BKO e bônus de finalização tipificados, e registram
pagamento. A reabertura exige `periods:reopen` e motivo descritivo, preserva o
histórico de fechamento e recusa período com fechamento já pago — nesse caso a
correção é por compensação no período atual.

**F6 — relatórios parcial.** Dashboard, relatório financeiro geral, por
beneficiário, equipe e unidade com export PDF/XLSX, console de auditoria e
geração assíncrona de PDFs em lote com acompanhamento e ZIP estão entregues.
Faltam o seed volumétrico e o orçamento de p95 medido no CI.

As evidências e ressalvas de F4 a F6 estão em
[docs/architecture/fechamento-f4-f6.md](docs/architecture/fechamento-f4-f6.md).

## Começando

```bash
cp .env.example .env
```

Ajuste o `.env` e suba o ambiente — [runbook completo](docs/runbooks/ambiente-local.md):

```powershell
.\scripts\rfb.ps1 up
```

API em http://localhost:8000/docs, frontend em http://localhost:5173.

## Mapa do repositório

```text
rf-balance/
|-- apps/
|   |-- api/                 # FastAPI — monólito modular
|   |-- worker/              # jobs assíncronos e scheduler
|   `-- web/                 # React + TypeScript + Vite
|-- packages/
|   |-- api-client/          # client TypeScript gerado do OpenAPI
|   |-- design-system/       # componentes compartilhados
|   `-- contracts/           # schemas e eventos compartilhados
|-- infrastructure/
|   |-- compose/             # docker-compose por ambiente
|   |-- nginx/               # reverse proxy / servidor do estático
|   |-- mysql/               # configuração do MySQL local
|   |-- observability/       # otel-collector, dashboards
|   `-- terraform/           # se aplicável
|-- docs/
|   |-- architecture/        # diagramas, baseline de performance
|   |-- adr/                 # decisões arquiteturais
|   |-- runbooks/            # incidente, rollback, backup, recálculo
|   `-- business-rules/      # glossário e casos dourados
|-- scripts/                 # utilitários — sem senha ou dado real
`-- .github/workflows/       # CI/CD
```

## Regra de ouro deste repositório

**Um arquivo, uma responsabilidade.** Concretamente:

- Uma entidade de domínio por arquivo, com o nome da entidade: `domain/entities/proposal.py` → `class Proposal`.
- Um value object por arquivo: `domain/value_objects/money.py`.
- Um caso de uso por arquivo: `application/commands/register_receipt.py` contém o command e o seu handler — eles mudam sempre juntos, são uma unidade de comportamento.
- Um repositório por aggregate: `infrastructure/repositories/proposal_repository.py`.
- Um router por recurso: `api/routes/proposals.py`.
- Um componente React por arquivo, com o nome do componente.

O que **não** é "uma responsabilidade": arquivo `utils.py`, `helpers.py`, `common.py`, `misc.ts`. Se não dá nome ao que o arquivo faz, ele faz mais de uma coisa. Nomeie pela responsabilidade (`formatters/currency.ts`, `time/clock.py`).

Limite prático: arquivo passando de ~200 linhas ou classe com mais de uma razão para mudar é sinal de divisão pendente — não regra cega, mas gatilho de revisão.

## Convenções de nome

| Onde | Padrão | Exemplo |
|---|---|---|
| Python: arquivos e pastas | `snake_case` | `commission_entry.py` |
| Python: classes | `PascalCase` | `CommissionEntry` |
| TypeScript: componente | `PascalCase.tsx` | `ProposalTable.tsx` |
| TypeScript: hook | `useAlgo.ts` | `useProposalList.ts` |
| TypeScript: outros módulos | `kebab-case.ts` | `currency-formatter.ts` |
| Pasta de feature no front | `kebab-case` | `commission-rules/` |
| Tabela no banco | `snake_case` plural | `commission_entries` |
| Migração Alembic | `NNNN_descricao_curta.py` | `0007_add_settlements.py` |
| ADR | `NNNN-titulo-kebab.md` | `0002-mysql-versus-postgresql.md` |

## Fronteiras que o código não pode cruzar

Ver `docs/adr/` e a skill `rfb-arquitetura` em `.claude/skills/`. Em resumo:

- `domain/` não importa FastAPI, SQLAlchemy, Redis, Jinja2 ou biblioteca de PDF.
- Só o módulo dono escreve nas suas tabelas; acesso externo passa por porta em `application/ports/`.
- O grafo de dependências entre módulos está na seção 5 do blueprint. Seta ausente = import proibido.
- O frontend nunca calcula dinheiro.

## Skills do projeto

`.claude/skills/` contém as convenções carregadas automaticamente pelo Claude Code: `rfb-arquitetura`, `rfb-backend`, `rfb-frontend`, `rfb-banco-de-dados`.
