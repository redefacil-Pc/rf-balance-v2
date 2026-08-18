# 0004 — Execução assíncrona sem Celery nesta etapa

- **Status:** aceito
- **Data:** 2026-08-14
- **Decisor:** Orlean
- **Fases afetadas:** F1, F3 e F6

## Decisão

O sistema usará o worker próprio do monólito modular para entregar a outbox e,
nas fases seguintes, executar handlers idempotentes. Celery, Dramatiq e RQ não
serão adicionados enquanto não houver necessidade comprovada de recursos que o
runner atual não ofereça.

O banco continua sendo a fonte de verdade da outbox. O worker publica no
transporte escolhido pelo ADR-0005 com semântica **ao menos uma vez**; portanto,
todo consumidor deve ser idempotente.

## Consequências

- menos infraestrutura e uma única forma de observar retries;
- falha após publicar e antes de marcar a outbox pode duplicar entrega;
- jobs longos da F6 devem possuir checkpoint, progresso e chave idempotente;
- a decisão deve ser revista se surgirem workflows, roteamento ou escalonamento
  que tornem o runner próprio mais complexo que uma biblioteca consolidada.
