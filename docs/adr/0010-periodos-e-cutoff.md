# 0010 — Política de período e cutoff

- **Status:** aceito
- **Data:** 2026-08-24
- **Decisores:** equipe RF Balance
- **Fase afetada:** F5

## Contexto

Fechamentos precisam de uma janela explícita que impeça alterações retroativas silenciosas e fechamento antes do prazo operacional.

## Decisão

Persistir períodos não sobrepostos com início, fim, `cutoff_at` com fuso e estado. Fechamento só ocorre após o cutoff; período pago não reabre.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Fechar por mês implícito | Menos configuração | Não representa semanas ou exceções | Operação exige calendário explícito |
| Cutoff apenas na UI | Simples | API poderia contornar | Regra financeira deve estar no domínio |

## Consequências

- Reabertura não paga é auditada, motivada e protegida por lock.
- Edições de competência fechada são bloqueadas.
- Correção de pagamento ocorre por compensação atual.

## Impacto financeiro ou de dados

Datas, cutoff e autores permanecem armazenados para reconstruir cada fechamento.
