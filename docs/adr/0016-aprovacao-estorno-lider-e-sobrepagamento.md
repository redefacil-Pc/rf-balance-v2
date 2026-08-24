# 0016 — Aprovação de período, estorno, liderança e sobrepagamento

- **Status:** aceito
- **Data:** 2026-08-21
- **Decisor:** Orlean
- **Fases afetadas:** F2, F3, F4 e F5

## Decisão

1. A reabertura de período fechado exige duas aprovações de usuários distintos com
   `periods:reopen`. A primeira solicitação mantém o período bloqueado em
   `REOPENING_PENDING`; a segunda efetiva `OPEN`. Período com fechamento pago não reabre.
2. Estorno não altera nem apaga comissão já reconhecida. Ele vira desconto no
   fechamento corrente ou nas semanas seguintes. A parcela que não couber no saldo da
   semana permanece identificada como saldo de estorno e é carregada até ser absorvida.
3. Liderança não realiza venda e não pode ser indicada como consultor de proposta,
   mesmo quando houver acúmulo histórico das funções no cadastro.
4. Sobrepagamento não possui limite de negócio para declaração. O Financeiro pode
   aprovar o valor, a proposta fica identificada como `OVERPAID` e a produção/comissão
   permanece limitada a 100% da base elegível; o excedente não gera comissão adicional.

## Consequências

- Solicitação e segunda aprovação de reabertura ficam registradas separadamente na auditoria.
- Desconto manual e desconto originado por estorno permanecem separados no banco e
  aparecem consolidados no fechamento.
- O backend, e não apenas o seletor do frontend, impede venda atribuída a líder.
- O comprovante e o valor excedente seguem o mesmo fluxo de conferência financeira dos
  demais recebimentos.
