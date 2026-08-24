# 0002 — MySQL como banco transacional

- **Status:** aceito
- **Data:** 2026-08-24
- **Decisores:** equipe RF Balance
- **Fase afetada:** todas

## Contexto

O legado, a experiência operacional e a infraestrutura disponível usam MySQL. O sistema exige transações, locks, índices compostos e valores decimais exatos, todos atendidos pelo MySQL 8.4.

## Decisão

Usar MySQL 8.4 como banco transacional autoritativo, com SQLAlchemy assíncrono e migrações Alembic.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| PostgreSQL | Recursos SQL avançados | Migração operacional adicional | Não entrega ganho necessário ao domínio atual |
| Dois bancos | Especialização por módulo | Consistência e backup mais complexos | Prematuro para o volume atual |

## Consequências

- Produção usa `READ COMMITTED`, modo SQL estrito e UTC.
- Dinheiro usa `DECIMAL`, nunca ponto flutuante.
- Troca de banco exige ADR substituto e plano de reconciliação.

## Impacto financeiro ou de dados

Migrações são verificadas com upgrade, downgrade e novo upgrade no CI.
