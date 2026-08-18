# 0005 — Redis Streams como transporte de eventos internos

- **Status:** aceito
- **Data:** 2026-08-14
- **Decisor:** Orlean
- **Fases afetadas:** F1, F3 e F6

## Decisão

Eventos da outbox são publicados no stream `rfbalance:domain-events`. Redis já
é dependência operacional para sessões, cache e locks, e Streams oferece IDs,
retenção e consumer groups sem introduzir um broker adicional nesta etapa.

A entrega é ao menos uma vez. `outbox_id` acompanha toda mensagem e é a chave
canônica de deduplicação dos consumidores.

## Consequências

- o ledger e os valores financeiros permanecem no MySQL, nunca no Redis;
- consumidores devem confirmar mensagens somente depois do próprio commit;
- retenção e tamanho do stream precisam ser monitorados;
- broker dedicado será reconsiderado se volume, isolamento ou operação exigirem.
