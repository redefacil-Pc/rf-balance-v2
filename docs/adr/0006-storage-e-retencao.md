# 0006 — Storage S3 compatível e política de retenção

- **Status:** aceito
- **Data:** 2026-08-24
- **Decisores:** equipe RF Balance
- **Fase afetada:** F1 e operação

## Contexto

Comprovantes, relatórios e backups não devem ocupar o banco relacional. O desenvolvimento precisa reproduzir a API usada em produção.

## Decisão

Usar storage compatível com S3, MinIO apenas localmente, buckets privados e prefixos por finalidade. Backups têm retenção configurável, verificação SHA-256 e réplica local independente.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Arquivos no banco | Transação única | Banco e backup crescem rapidamente | Binários não são dados transacionais consultáveis |
| Disco local único | Simples | Perda junto com o host | Não atende recuperação de desastre |

## Consequências

- Objetos nunca são públicos; acesso ocorre pela API autorizada.
- Retenção padrão de backup é 30 dias e pode ser maior por ambiente.
- Restore drill periódico valida que cópia e credenciais são utilizáveis.

## Impacto financeiro ou de dados

Metadados SHA-256 e manifests permitem recusar restaurações corrompidas.
