# Legado `rf_balance` — schema real e mapeamento canônico

Base deste documento: DDL do backup `mysql_backup_rf_balance_2026-03-31_18-00-00`, lido em 12/08/2026. **Nenhum dado real foi copiado para este repositório**; as fixtures de teste são sintéticas.

Este documento é a fonte do importador (`app/modules/legacy`). Divergiu do legado real? Corrija aqui **e** no tradutor correspondente — o mapeamento não deve existir só na cabeça de quem escreveu.

## Tabelas de origem

| Tabela | Linhas (ordem de grandeza) | Destino canônico |
|---|---:|---|
| `consultants` | ~65 | `collaborators`, `collaborator_roles`, `collaborator_payment_keys` |
| `proposals` | ~58 | `proposals` (fonte principal) |
| `propostas` | vazia no backup lido | staging/ACL — nunca direto |
| `sales` | vazia no backup lido | staging/ACL — nunca direto |
| `payments` | ~76 | `receipts` (F3) |
| `consultor_lider` | ~74 | `team_assignments` |
| `users` | ~4 | `users`, `user_roles` |

`propostas` e `sales` estarem vazias **neste** backup não autoriza ignorá-las: o dump de produção do dia do cutover pode ter linhas, e o importador precisa continuar recusando a escolha automática entre as três estruturas.

## `consultants` → `collaborators`

| Origem | Destino | Observação |
|---|---|---|
| `id` | `legacy_id` (com `legacy_source = 'consultants'`) | preserva rastreabilidade (seção 18) |
| `name` | `full_name` | |
| `document` | `document_encrypted` + `document_hash` | CPF/CNPJ sem máscara na origem; validar dígito |
| `is_active` (`int`) | `is_active` (`bool`) | `1`/`0`; nulo tratado como inativo, com issue |
| `pix_key` + `pix_type` | `collaborator_payment_keys` | telefone vem formatado (`(79) 98103-1196`) |
| `role` (texto único) | `collaborator_roles` (linha com vigência) | ver abaixo |
| `unidade` (texto livre) | `units.code` | só `aracaju` observado |
| `company` (texto livre) | **não mapeado** | ver abaixo |

**`role` é campo de texto único** — o defeito que o [ADR-0013](../adr/0013-papeis-de-colaborador-e-intervalos-de-vigencia.md) corrige. Valores observados: `CONSULTOR`, `LIDER`, `BKO` — note que `BKO` existe no dado real embora o comentário do DDL prometa apenas `CONSULTOR` ou `LIDER`. Quem acumulava funções no v1 não tem como ser representado: o importador traz **um** papel por pessoa e registra issue quando o valor não está no catálogo.

Não há data de início de vigência na origem. O importador usa `created_at` do consultor como `valid_from` e emite issue de atenção: a vigência importada é uma **aproximação**, e vigência errada troca o beneficiário da comissão na F4.

**`company` não é a empresa do grupo.** Os valores observados (`Alfa Negócios Ltda`, `Almeida serviços`) são a razão social do MEI do próprio colaborador, não a empresa contratante. Mapeá-la para `companies` criaria uma empresa do grupo por colaborador. Fica sem destino até o negócio decidir se vira dado cadastral do colaborador ou nada; o importador registra o valor na issue para não perdê-lo.

## `proposals` → `proposals`

| Origem | Destino | Observação |
|---|---|---|
| `id` | `legacy_id` (`legacy_source = 'proposals'`) | |
| `redmine_id` | `external_id` | único quando preenchido |
| `consultant_id` | `consultant_id` | resolvido pelo `legacy_id` do colaborador |
| `proposal_date` | `business_date` | `DATE` na origem; `created_at` é outro conceito |
| `nome_cliente` | `customer_name` | |
| `cpf_cliente` | `customer_document_*` | sem máscara na origem |
| `valor_proposta` | `operation_amount` | `DECIMAL(15,2)` → `DECIMAL(18,2)` |
| `percentual_tps` | `tps_percentage` | `DECIMAL(5,2)` → `DECIMAL(9,6)` |
| `valor_total_comissao` | `company_commission_amount` | **recalculado e conferido** |
| `valor_total_pago` | `paid_amount_cached` | |
| `valor_pendente` | `outstanding_amount_cached` | recalculado pela política de tolerância |
| `status` | `status` | ver tabela de estados |
| `bko` (texto) | `bko_collaborator_id` | **nome livre**, não FK |
| `finalizacao` (texto) | `finalizer_collaborator_id` | **nome livre**, não FK |
| `finalized_at` | `settled_at` | |
| `nivel_aplicado`, `comissao_calculada`, `regra_comissao`, `calculation_details` | — | histórico de comissão: F4, não F2 |

**Estados:**

| Origem | Destino | Regra |
|---|---|---|
| `ABERTA` | `OPEN` | |
| `PENDENTE` | `PARTIALLY_PAID` | quando há valor pago; senão `OPEN`, com issue |
| `FINALIZADA` | `PAID` | conferido contra a política de tolerância |

O legado não tem estado de cancelamento em `proposals` (só `propostas` tem `CANCELADA`). Nenhuma proposta é importada como `CANCELLED`.

**`bko` e `finalizacao` são os pontos mais frágeis da importação.** São nomes digitados, e o importador resolve por nome exato contra os colaboradores já traduzidos. Sem correspondência, com mais de uma, ou com grafia divergente, o campo fica nulo e o registro vai para a fila de exceção — o importador não escolhe entre duas pessoas parecidas.

**Conferência de comissão:** o importador recalcula `operação * TPS / 100` e compara com `valor_total_comissao` da origem. Divergência de centavo é esperada e vira issue de atenção; divergência maior é bloqueio. É a checagem que revela regra implícita no v1 antes de a F4 depender dela.

## `propostas` e `sales` → staging/ACL

Estruturas paralelas, com campos que **parecem** os mesmos e não são:

| `proposals` | `propostas` | `sales` |
|---|---|---|
| `valor_proposta` | `valor_venda` | `valor_operacao` |
| `valor_total_comissao` | `valor_comissao_empresa` | `valor_comissionavel` |
| `percentual_tps` | `tps` | `tps_percentage` |
| `proposal_date` | `data_venda` (`DATETIME`) | `data_pag` |
| `cpf_cliente` | — (sem cliente) | `cpf` |
| `status` ABERTA/PENDENTE/FINALIZADA | `status` PENDENTE/PAGA/CANCELADA | `is_active` |

`propostas` não guarda cliente, então não há como deduplicar por documento: a comparação possível é (consultor, data, valor). Coincidiu, é **candidata a duplicata** e vai para a fila de exceção com as duas origens; não coincidiu, é registro órfão e também vai para a fila. Em nenhum caso o importador promove `propostas` ou `sales` a proposta canônica sozinho.

## Fila de exceção

Tudo o que o importador não resolve sem adivinhar vira linha em `legacy_import_issues`, com origem, id legado, código, severidade e o valor problemático. `BLOQUEIO` impede o registro de ser importado; `ATENCAO` deixa importar com o campo em branco ou aproximado.

| Código | Severidade | Quando |
|---|---|---|
| `documento-invalido` | bloqueio | CPF/CNPJ com dígito verificador errado |
| `documento-duplicado` | bloqueio | mesmo documento em dois consultores |
| `consultor-nao-encontrado` | bloqueio | `consultant_id` sem consultor correspondente |
| `valor-invalido` | bloqueio | operação ≤ 0 ou TPS fora de 0–100 |
| `comissao-divergente` | atenção/bloqueio | recálculo diverge da origem |
| `status-divergente` | atenção | status da origem diverge do recalculado |
| `papel-desconhecido` | atenção | `role` fora do catálogo |
| `vigencia-presumida` | atenção | `valid_from` derivado de `created_at` |
| `participante-nao-resolvido` | atenção | `bko`/`finalizacao` sem correspondência única |
| `redmine-duplicado` | bloqueio | mesmo `redmine_id` em duas propostas |
| `empresa-do-consultor-sem-destino` | atenção | `consultants.company` preenchida |
| `estrutura-duplicada` | atenção | candidata a duplicata entre `proposals`/`propostas`/`sales` |

## O que este importador não faz

- **Não escreve** nas tabelas canônicas. A F2 entrega o dry-run; a carga real é da F7, depois de o relatório de divergência ser aceito pelo negócio.
- Não importa `payments` (F3), regras de comissão (F4), períodos (F5) nem histórico de comissão calculada.
- Não corrige dado de origem. Registro problemático é relatado, não consertado por heurística.
