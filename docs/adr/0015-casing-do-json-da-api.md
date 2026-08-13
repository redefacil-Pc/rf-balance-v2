# 0015 — JSON da API em snake_case

- **Status:** aceito
- **Data:** 2026-08-11
- **Decisores:** Orlean
- **Fase afetada:** F1 (contrato da API)

## Contexto

O blueprint (seção 9.1) exige escolher `snake_case` ou `camelCase` **uma vez** e não misturar. A decisão precisa existir antes do primeiro endpoint, porque muda todo o contrato.

## Decisão

O JSON da API usa **`snake_case`**, igual ao banco e ao Python. O frontend consome os tipos gerados do OpenAPI, então não escreve nomes de campo à mão.

Esta decisão foi tomada por padrão técnico, sem consulta ao negócio — é reversível apenas antes de existir cliente externo.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| `camelCase` | Idiomático em TypeScript | Exige camada de conversão no backend, com risco de divergência entre DTO, log e auditoria | O ganho é estético e o client é gerado; não paga a camada de tradução |
| Misto por módulo | — | Contraria explicitamente o blueprint | — |

## Consequências

- DTOs Pydantic não declaram `alias_generator`.
- Campos de erro em Problem Details também em `snake_case` (`correlation_id`).
- Contract test do CI falha se aparecer chave em `camelCase`.

## Impacto financeiro ou de dados

Nenhum.
