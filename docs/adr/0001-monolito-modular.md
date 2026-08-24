# 0001 — Monólito modular

- **Status:** aceito
- **Data:** 2026-08-24
- **Decisores:** equipe RF Balance
- **Fase afetada:** todas

## Contexto

Identidade, comercial, recebíveis, comissões e relatórios compartilham transações e evoluem com uma equipe única. Separá-los em serviços agora aumentaria a operação distribuída sem remover uma limitação observada.

## Decisão

Manter um monólito modular, com fronteiras explícitas entre `domain`, `application`, `infrastructure` e `api`, além de um worker implantável separadamente para tarefas assíncronas.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Microserviços | Escala e deploy independentes | Consistência distribuída e mais operação | Não há necessidade de escala independente comprovada |
| Monólito sem módulos | Menos estrutura inicial | Acoplamento crescente | Regras financeiras exigem donos e fronteiras claras |

## Consequências

- Módulos não escrevem diretamente nas tabelas de outros módulos.
- Extração para serviço só ocorre com necessidade operacional medida.
- Outbox preserva a possibilidade de integrações e extrações futuras.

## Impacto financeiro ou de dados

Operações financeiras relacionadas permanecem atômicas no mesmo banco.
