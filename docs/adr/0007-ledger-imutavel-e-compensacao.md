# 0007 — Ledger imutável e compensação

- **Status:** aceito
- **Data:** 2026-08-24
- **Decisores:** equipe RF Balance
- **Fase afetada:** F4 e F5

## Contexto

Editar um crédito histórico apaga a explicação do valor anteriormente calculado e torna fechamentos irreconciliáveis.

## Decisão

Manter `commission_entries` append-only. Estornos e correções geram débitos ou créditos compensatórios ligados à origem; nunca alteram o lançamento original.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Atualizar o crédito | Implementação curta | Apaga histórico | Incompatível com auditoria financeira |
| Recalcular tudo | Resultado atual simples | Muda período fechado | Não preserva o que foi pago |

## Consequências

- Cada cálculo guarda snapshot, versão, entradas, saídas e hash.
- Idempotência impede compensação duplicada.
- Período pago é corrigido no período atual.

## Impacto financeiro ou de dados

O saldo é a soma do ledger; reconciliação sempre alcança crédito original e compensações.
