# infrastructure/mysql

## `init/`

Roda uma única vez, na primeira inicialização do volume: cria a conta de
migração com DDL e restringe a conta da aplicação a DML (seção 12.4).

Em produção o equivalente é feito no banco gerenciado, por provisionamento.

## Onde está a configuração do servidor

Nas flags de `command:` do serviço `db` em
[docker-compose.yml](../compose/docker-compose.yml), **não** em um `.cnf`
montado.

Motivo: bind mount no Windows expõe o arquivo como world-writable, e o MySQL
**ignora silenciosamente** qualquer `.cnf` com essa permissão — o sintoma é o
aviso `World-writable config file ... is ignored` no log e a configuração
simplesmente não valer. Flag em `command:` não tem esse problema.

Em produção, esses parâmetros viram parameter group / configuração do banco
gerenciado. Os que não são negociáveis:

| Parâmetro | Valor | Por quê |
|---|---|---|
| `sql-mode` | inclui `STRICT_ALL_TABLES` | truncamento silencioso de `DECIMAL` seria perda de dinheiro |
| `default-time-zone` | `+00:00` | instantes são gravados em UTC; a conversão é da aplicação |
| `transaction-isolation` | `READ-COMMITTED` | evita gap lock desnecessário nas escritas concorrentes de recebimento |
| `innodb-flush-log-at-trx-commit` | `1` | durabilidade por transação em dado financeiro |
| `slow-query-log` + `long-query-time=0.5` | ligado | Trilha P: query lenta tem que aparecer em desenvolvimento |
