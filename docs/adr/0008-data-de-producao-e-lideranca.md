# 0008 — Data efetiva para produção e liderança

- **Status:** aceito
- **Data:** 2026-08-24
- **Decisores:** equipe RF Balance
- **Fase afetada:** F4

## Contexto

Datas de cadastro não representam necessariamente a competência financeira. Função, regra e liderança podem mudar entre proposta e recebimento.

## Decisão

Usar `receipt.business_date` como competência do cálculo e como data de resolução das funções e vínculos de liderança. Para líder comercial, o marco de elegibilidade é o primeiro recebimento elegível da proposta.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Data de criação | Automática | Reflete digitação, não produção | Atribui regra e líder incorretos em lançamentos retroativos |
| Data da proposta | Estável | Ignora quando o caixa ocorreu | Comissão nasce do recebimento reconhecido |

## Consequências

- Consultas históricas resolvem vigências na data efetiva.
- Data futura é rejeitada.
- Alterar competência após fechamento exige compensação.

## Impacto financeiro ou de dados

Snapshots registram a data e os beneficiários resolvidos para reprodução do cálculo.
