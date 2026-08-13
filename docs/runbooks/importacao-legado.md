# Runbook — importador legado em dry-run

Para que serve: ler o sistema atual, traduzir para o modelo canônico e produzir o **relatório de divergência**, sem escrever nada. É o que precisa estar aceito pelo negócio antes de qualquer carga real (F7).

O mapeamento campo a campo está em [legado-mapeamento.md](../architecture/legado-mapeamento.md).

## Antes de rodar

O dump do v1 tem PII real. Ele **não entra no repositório**: `data/` é gitignorado e existe só na máquina de quem roda. Se precisar compartilhar um relatório, compartilhe o resumo agregado, não os arquivos de origem.

## Opção 1 — a partir de CSV extraído (padrão)

Coloque um arquivo por tabela em `data/legado/`, com o cabeçalho igual ao nome das colunas do legado:

```text
data/legado/consultants.csv
data/legado/proposals.csv
data/legado/propostas.csv
data/legado/sales.csv
```

Tabela ausente é tratada como vazia — dá para começar só com `consultants.csv` e `proposals.csv`.

Para extrair de um dump `.sql`, restaure num MySQL descartável e exporte cada tabela:

```bash
mysql -u root -p rf_balance -e "SELECT * FROM consultants" --batch | sed 's/\t/,/g' > data/legado/consultants.csv
```

Depois:

```bash
make import-dry-run
```

O diretório é `/dados/legado` dentro do container, montado de `data/legado`. Para outro caminho: `make import-dry-run d=/dados/outro`.

## Opção 2 — direto do banco legado

Exige rota até o banco e um usuário **somente leitura**. O v1 continua sendo a verdade até o cutover; um importador com permissão de escrita no legado é acidente esperando acontecer.

```bash
# no .env
LEGACY_DATABASE_URL=mysql+asyncmy://leitor:senha@host:3306/rf_balance
```

```bash
make import-dry-run-mysql
```

## Lendo o resultado

O comando imprime, e grava em `legacy_import_runs`:

- **contagens** por origem: lidos, traduzidos, não traduzidos;
- **totais** de operação e de comissão, com a divergência entre o que o legado gravou e o que a v2 calcula;
- **distribuição por status** recalculado;
- **fila de exceção** agrupada por código.

Sai com código **1** quando há bloqueio. Em pipeline, isso mantém o processo vermelho enquanto existir registro que ninguém decidiu.

Para investigar um caso específico:

```sql
SELECT source_table, legacy_id, code, severity, detail
FROM legacy_import_issues
WHERE run_id = (SELECT MAX(id) FROM legacy_import_runs)
  AND severity = 'BLOQUEIO'
ORDER BY source_table, legacy_id;
```

## O que fazer com cada bloqueio

| Código | Onde se resolve |
|---|---|
| `documento-invalido` | corrigir o cadastro **no v1**, não no importador |
| `documento-duplicado` | decidir qual cadastro é o bom e inativar o outro no v1 |
| `redmine-duplicado` | corrigir o `redmine_id` repetido no v1 |
| `valor-invalido` | operação ≤ 0 ou TPS fora da faixa: corrigir na origem |
| `comissao-divergente` (bloqueio) | investigar a regra: o v1 gravou comissão que não é `operação * TPS / 100` |

Atenções não impedem a carga, mas cada uma é uma perda de informação consciente — em especial `vigencia-presumida` (a vigência da função é aproximada) e `participante-nao-resolvido` (BKO/finalização ficam vazios). Vale resolvê-las antes da F4, que é quando esses campos passam a decidir dinheiro.

## Repetir é seguro

Rodar de novo cria uma execução nova; nada é sobrescrito. Comparar duas execuções é como se acompanha a limpeza do dado ao longo das semanas — e o `uq_proposals_legacy`/`uq_collaborators_legacy` garante que, na carga real da F7, um registro do legado não entra duas vezes.

## O que este importador não faz

Não escreve em `collaborators` nem em `proposals`; pedir carga real levanta erro explícito. Não importa `payments` (F3), regras de comissão (F4) nem períodos (F5). E não corrige dado de origem por heurística: registro problemático é relatado, não consertado.
