# Fechamento de F1, F2 e F3

**Data:** 14/08/2026  
**Estado:** implementação concluída; homologação operacional pendente.

Este registro separa conclusão técnica de implantação. O sistema está pronto
para iniciar a configuração das regras de comissionamento (F4), mas ainda deve
passar pelo setor piloto em produção-staging antes de uso produtivo.

## F1 — fundação

- ambiente Docker com API, web, MySQL, Redis, MinIO, worker e scheduler;
- identidade, sessão segura, RBAC, auditoria append-only e proteção de PII;
- outbox transacional com dispatcher `FOR UPDATE SKIP LOCKED`, retry e entrega
  ao menos uma vez por Redis Streams;
- scheduler com lease no Redis e execução por líder único;
- health checks e métricas HTTP no formato Prometheus;
- CI com lint, tipos, testes, migrations, contrato, build e scans.

## F2 — organização e comercial

- empresas, unidades, colaboradores, contas, funções vigentes e equipes;
- prevenção e verificação periódica de sobreposição de vínculos;
- proposta canônica, controle otimista, escopo por RBAC e participantes
  validados pela função vigente na data de negócio;
- tolerância de quitação versionada e cache financeiro reconciliado;
- importador legado em dry-run com relatório de divergência e fila de exceção.

## F3 — recebíveis

- declaração dentro da proposta, com comprovante obrigatório, data e horário
  efetivos e chave idempotente reutilizada em retry;
- conferência financeira integrada à aprovação da proposta e fluxo avulso para
  recebimentos posteriores;
- limite acumulado de sobrepagamento e bloqueio de data/hora futura;
- estornos compensatórios totais ou parciais, preservando histórico e saldo
  líquido por recebimento;
- pagamento, totais, estado, auditoria e outbox no mesmo commit;
- testes de concorrência, replay e rollback por falha de outbox.

## Evidências locais

Executadas em containers em 14/08/2026:

| Gate | Resultado |
|---|---:|
| Ruff | aprovado |
| mypy strict | 398 arquivos sem erro |
| testes unitários | 130 aprovados |
| testes de integração | 142 aprovados em 299,58 s |
| testes de frontend | 74 aprovados |
| build de frontend | aprovado |
| Alembic check | nenhuma operação pendente |

O worker publicou eventos no stream configurado, o scheduler adquiriu a
liderança e os verificadores de integridade encerraram sem divergências no
ambiente local.

## Gates externos

Estes itens não podem ser comprovados por testes locais e devem compor a
homologação:

1. setor piloto cadastra colaborador, proposta e recebimento em
   produção-staging;
2. Financeiro confere o fluxo, inclusive pagamento parcial e estorno;
3. monitoramento, backup e retenção do storage são confirmados no provedor do
   ambiente;
4. CI do repositório remoto permanece verde no commit candidato.

F4 não deve alterar os invariantes acima. A comissão deve consumir os eventos e
valores autoritativos de recebimento, com regra versionada e ledger imutável.
