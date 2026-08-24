# 0014 — Read models síncronos

- **Status:** aceito
- **Data:** 2026-08-24
- **Decisores:** equipe RF Balance
- **Fase afetada:** F6

## Contexto

Dashboard e relatório financeiro precisam refletir o commit confirmado sem janela de divergência. O volume atual cabe em consultas indexadas com orçamento de p95.

## Decisão

Construir leituras financeiras de forma síncrona no mesmo MySQL. Usar processamento assíncrono somente para artefatos pesados, como PDF e ZIP, que guardam progresso e podem ser retomados.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Projeções eventuais | Leitura barata | Usuário vê valor atrasado | Inadequado durante conferência financeira |
| Relatórios todos síncronos | Menos worker | Requests longos e frágeis | Lotes de documentos excedem tempo HTTP |

## Consequências

- Índices e testes de performance protegem dashboard e relatório.
- Jobs de documentos são idempotentes e observáveis.
- Projeções eventuais exigirão ADR substituto quando volume justificar.

## Impacto financeiro ou de dados

Tela, XLSX e PDF compartilham a mesma consulta e os mesmos recortes autoritativos.
