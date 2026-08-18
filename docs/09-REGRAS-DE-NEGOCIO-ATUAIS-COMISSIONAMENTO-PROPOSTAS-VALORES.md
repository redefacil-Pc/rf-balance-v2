# Regras de negócio atuais — comissionamento, propostas e valores

**Data do levantamento:** 14/08/2026  
**Objetivo:** documentar o comportamento que o RF Balance executa hoje para servir de especificação funcional na construção do novo sistema.  
**Escopo:** propostas, recebimentos, produção, faturamento, comissão de consultores e líderes, MEI Escalonado, finalização, BKO, ajustes e pagamento de comissões.

> Este documento descreve o comportamento encontrado no backend e confirmado por testes automatizados. Ele não é uma proposta de arquitetura. Quando o código possui duas interpretações para o mesmo conceito, ambas são registradas e a diferença é marcada como ponto de decisão para a nova implementação.

## 1. Fontes e grau de confiança

Foram usadas como fonte principal:

- serviços de domínio e casos de uso do backend;
- endpoints efetivamente registrados;
- modelos e migrations atuais;
- testes automatizados de comissão, tolerância, pagamentos e MEI Escalonado;
- relatórios financeiros e regras de reset semanal.

As tabelas de percentuais são configuráveis. Como os containers e o banco local não estavam em execução no momento deste levantamento, os valores abaixo são os **defaults atuais do código/migrations**. Em produção, os registros ativos do banco podem ter sido alterados e devem ser exportados antes da migração.

## 2. Glossário financeiro

| Termo no sistema | Significado efetivo |
|---|---|
| Valor da proposta/operação | Valor total contratado com o cliente. Campo `valor_proposta`. |
| TPS | Percentual que transforma o valor da operação em comissão da empresa. Campo `percentual_tps`. |
| Comissão da empresa | `valor_proposta × TPS ÷ 100`. Também chamada `valor_total_comissao`. É o valor que o cliente deve pagar à empresa, não a comissão do consultor. |
| Valor pago/recebido | Soma dos lançamentos financeiros vinculados à proposta. Nos relatórios, normalmente entram apenas pagamentos `CONFIRMED` ou `SETTLED`. |
| Faturamento do período | Soma bruta dos pagamentos elegíveis ocorridos no período. |
| Produção reconhecida | Parte do valor da operação liberada proporcionalmente ao pagamento recebido. |
| Comissão total do consultor | Direito teórico do consultor quando 100% da comissão da empresa for recebida. Campo `comissao_calculada`. |
| Comissão a pagar no período | Parte da comissão do consultor liberada pelos pagamentos elegíveis do período. |
| Saldo pendente da proposta | Valor absoluto entre comissão da empresa e total pago: `abs(valor_total_comissao - valor_total_pago)`. |
| Comissão bruta do fechamento | Comissão calculada no período antes dos controles de pagamento, desconto e adiamento. |
| Comissão líquida/a pagar | Resultado após pagamento, adiamento, desconto, acumulado e carryover. |

## 3. Fórmulas fundamentais

### 3.1 Comissão da empresa

```text
comissao_empresa = arredondar_centavos(valor_proposta × percentual_tps ÷ 100)
```

Exemplo:

```text
valor_proposta = R$ 100.000,00
TPS = 35%
comissao_empresa = R$ 35.000,00
```

### 3.2 Proporção recebida

```text
proporcao_recebida = min(valor_recebido_elegivel ÷ comissao_empresa, 1)
```

O limite de 1 impede que sobrepagamentos liberem mais de 100% da produção ou da comissão teórica.

### 3.3 Produção reconhecida

```text
producao_reconhecida = valor_proposta × proporcao_recebida
```

Exemplo: uma operação de R$ 10.000,00 tem comissão da empresa de R$ 3.500,00. Se foram recebidos R$ 1.750,00, a proporção é 50% e a produção reconhecida é R$ 5.000,00.

### 3.4 Comissão proporcional do consultor padrão

```text
comissao_consultor_periodo = comissao_consultor_total × proporcao_recebida_no_periodo
```

O fechamento usa os pagamentos do período. Uma proposta criada em mês anterior entra no período atual se recebeu pagamento elegível no período atual.

## 4. Cadastro da proposta

### 4.1 Campos e validações

Uma proposta exige:

- consultor existente;
- data de negócio opcional; quando ausente, o modelo usa a data atual de Brasília;
- valor da operação maior que zero;
- TPS entre 0 e 100, inclusive;
- nome do cliente entre 3 e 200 caracteres;
- CPF/CNPJ contendo exatamente 11 ou 14 dígitos após retirar a máscara;
- BKO opcional;
- responsável de finalização opcional;
- ID Redmine opcional, com no máximo 50 caracteres.

Normalizações aplicadas:

- CPF/CNPJ é persistido apenas com dígitos;
- BKO e finalização têm espaços externos removidos e sequências internas de espaços consolidadas;
- Redmine tem espaços externos removidos; string vazia vira `null`.

### 4.2 Duplicidade

- `redmine_id`, quando preenchido, possui restrição única no banco;
- a criação também verifica duplicidade pela combinação nome do cliente + CPF/CNPJ + valor da operação + Redmine;
- conflito de Redmine na edição retorna conflito de duplicidade.

### 4.3 Valores calculados ao criar

Na criação são calculados e gravados como snapshot:

- comissão da empresa;
- percentual e comissão total do consultor;
- percentual e comissão teórica do líder;
- descrição textual da regra;
- detalhes JSON do cálculo;
- segmentos, faixa e versão da regra quando for MEI Escalonado.

A proposta nasce `aberta`, com total pago zero e pendência igual à comissão da empresa, salvo quando um pagamento inicial é criado junto.

### 4.4 Pagamento inicial

A API permite criar a proposta com pagamento inicial, tipo, banco, data e hora. Esse pagamento passa pelas mesmas regras de saldo e status dos demais pagamentos.

Comportamento legado relevante: se a data textual do pagamento inicial não puder ser interpretada, o endpoint atual pode substituí-la pela data/hora corrente em vez de rejeitar. Isso é uma falha conhecida e não deve ser reproduzido no sistema novo.

### 4.5 Edição da proposta

Podem ser alterados consultor, cliente, documento, valor, TPS, BKO, finalização, Redmine e metadados do pagamento mais recente.

Quando valor, TPS ou consultor mudam, o sistema:

1. recalcula a comissão da empresa;
2. seleciona a tabela do regime atual do consultor;
3. recalcula a comissão do consultor e o snapshot do líder;
4. recalcula o saldo mantendo o total já pago;
5. recalcula o status e `finalized_at`;
6. recalcula os segmentos do MEI Escalonado, se aplicável.

Não existe hoje bloqueio geral que impeça alterar valor/TPS de proposta já paga ou pertencente a período fechado. No sistema novo isso deverá ser uma decisão explícita.

## 5. Recebimentos da proposta

### 5.1 Regras de inclusão

Para criar um pagamento:

- valor deve ser maior que zero;
- proposta deve existir;
- data e hora não podem estar no futuro, usando o calendário de Brasília;
- quando a hora efetiva é informada, sua data deve ser igual a `data_pagamento`;
- uma proposta já `finalizada` não aceita novo pagamento;
- o pagamento não pode exceder o saldo pendente em mais de R$ 100,00.

Metadados disponíveis: tipo (`PIX`, `TED`, `Boleto` ou texto aceito pelo schema), banco, conta de destino, task/Redmine, observação e usuário que lançou.

### 5.2 Status dos pagamentos

Os valores usados nos relatórios e comissões periódicas são, em regra:

```text
status normalizado em {CONFIRMED, SETTLED}
```

Porém, o schema atual aceita qualquer texto e a consolidação do total da proposta não filtra os mesmos status em todos os caminhos. Portanto:

- uma proposta pode somar um pagamento `PENDING` no total pago/status;
- relatórios e comissões podem ignorar esse mesmo pagamento;
- esta é uma inconsistência atual, não uma regra desejada.

O novo sistema deve definir um único predicado de pagamento elegível e reutilizá-lo em proposta, dashboard, comissão e relatório.

### 5.3 Status da proposta e tolerância

Se `total_pago = 0`, o status é `aberta`.

Nos demais casos calcula-se:

```text
diferenca = total_pago - comissao_empresa
```

| Situação | Status |
|---|---|
| Pagamento exato | `finalizada` |
| Até R$ 10,00 abaixo, inclusive | `finalizada` |
| Mais de R$ 10,00 abaixo | `pendente` |
| Até R$ 100,00 acima, inclusive | `finalizada` |
| Mais de R$ 100,00 acima | não deveria ser aceito na inclusão; se existir, o cálculo resulta `pendente` |

O saldo persistido é sempre absoluto. Assim, uma proposta com R$ 50,00 pagos a mais aparece finalizada e com `valor_pendente = R$ 50,00`, embora esse valor represente excesso, não dívida.

### 5.4 Estorno de recebimento

O estorno da proposta:

- exige valor maior que zero;
- não aceita data/hora futura;
- não pode exceder o total já pago;
- é salvo como um pagamento negativo, normalmente com status `REFUNDED`;
- reduz o total pago;
- recalcula saldo e status;
- pode reabrir uma proposta finalizada como pendente ou aberta;
- dispara recálculo do MEI Escalonado afetado.

Nos relatórios que filtram apenas `CONFIRMED` e `SETTLED`, o lançamento negativo `REFUNDED` não entra diretamente. Esta diferença deve ser tratada com cuidado na migração.

## 6. Consultor padrão

### 6.1 Faixas padrão configuráveis

> **Decisão operacional corrigida em 17/08/2026:** regime e função são eixos
> independentes. `MEI`/`CLT` identifica o vínculo do colaborador. A função
> `CONSULTOR` seleciona esta estratégia padrão e a função
> `CONSULTOR_MEI_ESCALONADO` seleciona a estratégia escalonada, em ambos os
> casos independentemente do regime cadastrado.

As faixas configuráveis da função Consultor padrão são:

| Faixa TPS | Percentual do consultor sobre a comissão da empresa |
|---|---:|
| TPS >= 35% | 12% |
| 30% <= TPS <= 34,99% | 10% |
| 25% <= TPS <= 29,99% | 8% |
| TPS <= 24,99% | 6% |

Fórmula do direito total:

```text
comissao_consultor_total = comissao_empresa × percentual_da_faixa ÷ 100
```

Exemplo com operação de R$ 100.000,00:

| TPS | Comissão empresa | Faixa consultor | Comissão total consultor |
|---:|---:|---:|---:|
| 35% | R$ 35.000,00 | 12% | R$ 4.200,00 |
| 30% | R$ 30.000,00 | 10% | R$ 3.000,00 |
| 25% | R$ 25.000,00 | 8% | R$ 2.000,00 |
| 24,99% | R$ 24.990,00 | 6% | R$ 1.499,40 |

As faixas ativas são lidas do banco e prevalecem sobre esses defaults. Percentuais e limites aceitam configuração entre 0 e 100; faixas ativas não podem se sobrepor.

### 6.2 Override individual

Um consultor pode ter `override_tps_35_percentage`. Quando preenchido:

- aplica-se somente a propostas com TPS >= 35%;
- substitui o percentual da tabela;
- não altera as faixas abaixo de 35%;
- fica registrado no snapshot do cálculo.

### 6.3 Liberação no período

A comissão total calculada no cadastro é apenas o teto da proposta. O que entra no fechamento é proporcional ao pagamento elegível:

```text
comissao_a_pagar = comissao_consultor_total ×
                   min(pagamento_aproveitavel ÷ comissao_empresa, 1)
```

O pagamento aproveitável é limitado ao saldo ainda não reconhecido da comissão da empresa, evitando comissionar sobre mais de 100%.

### 6.4 Exclusão individual por configuração

A variável `NO_COMMISSION_CONSULTANT_IDS` pode conter IDs de consultores que não recebem comissão. Para esses IDs, os relatórios zeram a comissão do consultor, embora os pagamentos e a produção continuem existindo.

## 7. Consultor Escalonado (`CONSULTOR_MEI_ESCALONADO`)

### 7.1 Conceito

O percentual do consultor é definido pelo cruzamento de:

- TPS da proposta; e
- produção mensal acumulada reconhecida pelos pagamentos.

Somente a comissão do consultor muda. A comissão do líder segue sua regra própria.

### 7.2 Matriz padrão

| Produção mensal acumulada | TPS >= 35% | TPS 30–34,99% | TPS 25–29,99% | TPS < 25% |
|---|---:|---:|---:|---:|
| Faixa 1: R$ 0 a R$ 75.000,00 | 8% | 6% | 4% | 2% |
| Faixa 2: acima de R$ 75.000,00 até R$ 175.000,00 | 10% | 8% | 6% | 4% |
| Faixa 3: acima de R$ 175.000,00 | 11,5% | 9,5% | 7,5% | 5,5% |

Na migration original os mínimos foram gravados como 0, 75.000 e 175.000. A lógica de rateio trata os limites como contínuos; configurações/testes recentes também usam 75.000,01 e 175.000,01 para consultas pontuais.

### 7.3 Produção que avança a faixa

A faixa avança apenas com produção reconhecida por pagamentos `CONFIRMED` ou `SETTLED` no mês:

```text
producao_reconhecida_pagamento = valor_proposta ×
                                 pagamento_aproveitavel ÷ comissao_empresa
```

Uma proposta não paga não avança a faixa. Um pagamento parcial avança apenas a parcela proporcional.

Os pagamentos são processados em ordem de:

1. `data_pagamento`;
2. `payment_datetime`, senão `created_at`, senão início do dia;
3. ID do pagamento.

### 7.4 Rateio marginal ao cruzar faixa

Se a produção reconhecida atravessar um limite, ela é dividida em segmentos. Cada segmento usa a alíquota da faixa em que caiu:

```text
comissao_empresa_segmento = producao_segmento × TPS ÷ 100
comissao_consultor_segmento = comissao_empresa_segmento × aliquota_segmento ÷ 100
```

Exemplo com TPS 35%, acumulado anterior de R$ 70.000,00 e nova produção reconhecida de R$ 20.000,00:

- R$ 5.000,00 ficam na faixa 1 a 8%;
- R$ 15.000,00 ficam na faixa 2 a 10%;
- a comissão final é a soma das comissões dos dois segmentos.

### 7.5 Período e reset

- as faixas sempre acumulam e resetam por mês civil;
- o modo `SEMANAL` ou `MENSAL` muda o período de exibição/fechamento dos valores;
- o modo não altera o acúmulo mensal das faixas;
- sem configuração, o modo padrão é `SEMANAL`;
- mudança de modo só pode ser agendada para data futura.

### 7.6 Vigência das regras

As faixas possuem `valid_from`, `valid_until`, versão, ordenação e status ativo. Para cada pagamento devem valer as faixas ativas na data do pagamento.

Observação: o endpoint atual de edição das faixas não executa toda a validação de lacunas e sobreposições que seria necessária. O motor falha se não encontrar uma faixa compatível.

## 8. Líder comercial (`LIDER`)

### 8.1 Vínculo que recebe

O líder é o vínculo do consultor vigente na data do **primeiro pagamento elegível da proposta**, e não necessariamente na data de cadastro da proposta nem na data de cada parcela.

Consulta atual:

```text
vinculo.start_date <= data_primeiro_pagamento
AND (vinculo.end_date IS NULL OR vinculo.end_date >= data_primeiro_pagamento)
```

Se não houver vínculo nessa data, não há comissão de líder.

### 8.2 Percentuais padrão

| Regime do líder | TPS da proposta | Percentual sobre a parcela recebida da comissão da empresa |
|---|---:|---:|
| MEI | >= 25% | 3% |
| MEI | < 25% | 0% |
| CLT | qualquer TPS | 0% |

As faixas são configuráveis por papel e regime. O cálculo usa os valores ativos no banco.

```text
comissao_lider_pagamento = pagamento_aproveitavel × percentual_lider ÷ 100
```

Como `pagamento_aproveitavel` é a parcela da comissão da empresa efetivamente liberada, isso equivale a aplicar o percentual sobre a comissão da empresa paga no período.

### 8.3 Produção e quantidade exibidas

- `volume_valido`: valor integral, contado uma vez, das propostas com TPS >= 25% que tiveram pagamento no período;
- `volume_total`: valor integral, contado uma vez, de todas as propostas da equipe com pagamento no período;
- a produção detalhada do período é proporcional ao pagamento;
- `propostas_count` no retorno atual conta linhas de pagamento, não necessariamente propostas únicas.

### 8.4 Divergência do snapshot da proposta

O calculador usado ao cadastrar a proposta salva `percentual_lider = 3%` e uma comissão teórica de 3% independentemente da TPS. O fechamento real do líder, porém, aplica 0% abaixo de TPS 25 e 0% para líder CLT.

Para o novo sistema, a regra autoritativa de valor a pagar é a do fechamento descrita nesta seção. Não se deve usar `proposal.comissao_lider` como verdade financeira sem reavaliar elegibilidade.

## 9. Líder MEI geral (`LIDER_MEI_GERAL`)

### 9.1 Abrangência

O líder MEI geral recebe sobre as unidades explicitamente associadas a ele. Unidades aceitas atualmente:

- Aracaju;
- Estância;
- São Paulo.

Se não houver unidades associadas, o sistema usa a unidade cadastrada no próprio líder como fallback.

Somente pagamentos de propostas de consultores MEI nas unidades cobertas entram. Pagamentos elegíveis são `CONFIRMED`/`SETTLED` e propostas canceladas ficam fora.

### 9.2 Base e níveis padrão

A base configurável padrão é 35% da produção proporcional reconhecida:

```text
base_total = producao_das_unidades × 35%
```

O cálculo é marginal/progressivo: cada parcela da produção usa o percentual de seu nível sobre a parte proporcional da base.

| Nível | Parcela de produção | Percentual sobre a base correspondente |
|---|---:|---:|
| 1 | R$ 0 a R$ 500.000 | 1,20% |
| 2 | R$ 500.000 a R$ 1.000.000 | 1,00% |
| 3 | R$ 1.000.000 a R$ 1.600.000 | 0,80% |
| 4 | R$ 1.600.000 a R$ 2.400.000 | 0,60% |
| 5 | R$ 2.400.000 a R$ 3.400.000 | 0,40% |
| 6 | R$ 3.400.000 a R$ 4.400.000 | 0,30% |
| 7 | R$ 4.400.000 a R$ 5.400.000 | 0,20% |

Não há faixa padrão acima de R$ 5.400.000,00; a parcela excedente não recebe percentual enquanto a configuração não for ampliada.

## 10. Finalização (`FINALIZACAO`)

### 10.1 Quem recebe

A proposta guarda o nome da pessoa de finalização. O relatório agrupa nomes removendo espaços externos, consolidando espaços internos e ignorando maiúsculas/minúsculas.

### 10.2 Base do período

Apesar do nome `total_produzido`, a base da finalização é a comissão da empresa recebida no período:

```text
base_finalizacao = soma dos pagamentos das propostas atribuídas à pessoa
```

O código limita cada lançamento individual a `min(valor_pago, comissao_empresa_da_proposta)`, mas não mantém um teto acumulado por proposta nesse relatório. Pagamentos duplicados ou excessivos podem, portanto, supercontar a base. Propostas `pendente` e `finalizada` entram; `aberta` e `cancelada` ficam fora.

Exceção relevante: esse relatório não filtra o status do pagamento. Hoje um lançamento `PENDING`, `REFUNDED` ou outro texto também pode afetar a base de finalização se estiver vinculado a uma proposta pendente/finalizada e sua data cair no período. O relatório de líder de finalização herda o mesmo comportamento.

### 10.3 Fórmula

```text
se base_finalizacao < R$ 70.000,00:
    comissao_base = R$ 0,00

se base_finalizacao >= R$ 70.000,00:
    comissao_base = R$ 500,00
                  + (base_finalizacao - R$ 70.000,00) × 0,45%

comissao_total = comissao_base + bonus_manual_do_periodo
```

No limite exato de R$ 70.000,00, a comissão é R$ 500,00.

O bônus manual é identificado por nome normalizado + início/fim exatos do período.

## 11. Líder de finalização (`LIDER_FINALIZACAO`)

### 11.1 Formação da equipe

- pessoas com papel `FINALIZACAO` são vinculadas a um `LIDER_FINALIZACAO` por vínculo temporal;
- o vínculo precisa intersectar o período solicitado;
- o total do time é a soma da base de finalização das pessoas vinculadas;
- TPS baixo não bloqueia esta comissão.

### 11.2 Fórmula padrão

```text
comissao_bruta = total_time × 0,90%
comissao_liquida = max(comissao_bruta - desconto_manual, 0)
```

O percentual de 0,90% é configurável por papel/regime e, por padrão, vale para MEI e CLT.

O desconto considerado é o registro mais recente com mesmo consultor, mesmo início e `period_end <= fim solicitado`. O valor líquido nunca fica negativo.

## 12. BKO

- o relatório operacional conta propostas por nome de BKO;
- a comissão financeira de BKO é manual, por colaborador e data efetiva;
- apenas BKO MEI (ou cadastro legado sem regime) recebe lançamento manual;
- BKO CLT é rejeitado no endpoint de gravação e ignorado na soma;
- somente valores positivos entram no total a pagar;
- no fechamento semanal, entram lançamentos cuja `effective_date` esteja dentro do período.

## 13. Período, data de competência e reset semanal

### 13.1 Regra geral de competência

Produção, faturamento e comissões são atribuídos principalmente pela data do pagamento, não pela data da proposta.

Consequências:

- proposta antiga com parcela paga agora produz faturamento, produção e comissão agora;
- parcelas em semanas diferentes liberam comissão em semanas diferentes;
- o primeiro pagamento fixa o líder comercial histórico usado para todas as parcelas da proposta.

### 13.2 Pagamentos elegíveis no período

Condição usual:

```text
data_inicio <= data_pagamento <= data_fim
AND status IN (CONFIRMED, SETTLED)
AND proposta != cancelada
```

### 13.3 Corte por reset

O reset pode guardar data e hora exatas. No dia do corte:

- pagamentos anteriores ao horário ficam fora do novo período;
- pagamentos no mesmo instante ou posteriores entram;
- se o reset for registrado às 23:59 ou depois na própria data, o início efetivo é o dia seguinte;
- sem reset manual, a abertura usada no controle de fechamento cai na sexta-feira mais recente.

O modo mensal do MEI Escalonado não elimina o acúmulo mensal das faixas; o reset semanal também não zera esse acumulado.

## 14. Fechamento e pagamento das comissões

### 14.1 Registro por pessoa e período

`commission_payments` representa o controle do total de comissão de uma pessoa em um período, não um pagamento por proposta. Estados:

- `pending`;
- `paid`;
- `deferred`;
- `refunded`.

O sistema seleciona o registro mais recente de cada consultor com mesmo `period_start` e `period_end <= fim solicitado`. Isso existe para tolerar alterações históricas do fim da semana.

### 14.2 Controles disponíveis

- marcar como pago: define `paid_amount`, zera `deferred_amount` e salva data/método/referência;
- marcar como adiado: define `deferred_amount`;
- aplicar desconto: define `discount_amount`;
- marcar estorno de comissão: somente consultor/MEI Escalonado, exige uma proposta pertencente ao mesmo consultor;
- aplicar acumulado/bônus: reutiliza tecnicamente o campo `refunded_amount`, sem proposta vinculada.

### 14.3 Fórmula líquida atual

```text
bruto_com_carryover = comissao_corrente + carryover_adiado_anterior

total_a_pagar = max(
    bruto_com_carryover
    - valor_pago
    - valor_adiado
    - desconto
    + valor_acumulado,
    0
)
```

No modelo atual, `valor_acumulado` e `valor_estornado` são aliases do mesmo campo `refunded_amount`. Por isso o valor chamado “estornado” é somado ao saldo a pagar. Essa sobrecarga semântica precisa ser separada no novo sistema.

### 14.4 Carryover adiado

- busca-se o registro mais recente anterior ao início do período atual;
- só há carryover se esse registro estiver com status `deferred` e valor adiado positivo;
- o carryover é somado ao bruto do período atual;
- um pagamento no período atual pode quitar comissão corrente e carryover conjuntamente.

### 14.5 Resumo de pendência

```text
pendente = max(
    total_commission
    - paid_amount
    - deferred_amount
    - discount_amount
    + accumulated_amount,
    0
)
```

Não há hoje validação forte impedindo que pago, adiado ou descontado excedam a comissão total.

## 15. Faturamento líquido do relatório

O resumo financeiro calcula:

```text
faturamento_liquido = faturamento_bruto
                      - comissoes_consultores_calculadas
                      - comissao_BKO
                      - comissoes_lideres
                      - comissao_finalizacao
                      - comissao_lider_finalizacao
```

Esse cálculo usa as comissões brutas calculadas para o período, não necessariamente o caixa efetivamente pago aos beneficiários após adiamentos e descontos.

## 16. Arredondamento e limites

- valores monetários são armazenados com duas casas decimais;
- o calculador padrão usa `Decimal.quantize(0.01)`;
- o MEI Escalonado usa `ROUND_HALF_UP` explicitamente;
- percentuais intermediários podem ser guardados com quatro casas em cálculos proporcionais;
- cada segmento do MEI Escalonado arredonda comissão da empresa e comissão do consultor para centavos antes da soma;
- sobrepagamento nunca libera mais de 100% nos relatórios proporcionais, salvo a ressalva específica do relatório de finalização.

## 17. Exemplo completo — consultor padrão e líder

Dados:

```text
operação: R$ 100.000,00
TPS: 30%
comissão empresa: R$ 30.000,00
consultor: faixa de 10%
líder MEI: faixa de 3%
pagamento recebido no período: R$ 12.000,00
```

Cálculo:

```text
proporção recebida = 12.000 ÷ 30.000 = 40%
produção reconhecida = 100.000 × 40% = R$ 40.000,00
comissão total consultor = 30.000 × 10% = R$ 3.000,00
comissão consultor do período = 3.000 × 40% = R$ 1.200,00
comissão líder do período = 12.000 × 3% = R$ 360,00
faturamento bruto do período = R$ 12.000,00
```

A proposta permanece `pendente`, pois faltam R$ 18.000,00 da comissão da empresa.

## 18. Exemplo completo — finalização

Uma finalizadora teve R$ 80.000,00 de comissão da empresa recebida nas propostas atribuídas a ela durante o período e possui bônus manual de R$ 300,00:

```text
fixo ao atingir 70 mil = R$ 500,00
excedente = R$ 10.000,00
comissão sobre excedente = 10.000 × 0,45% = R$ 45,00
comissão base = R$ 545,00
bônus manual = R$ 300,00
total = R$ 845,00
```

## 19. Matriz resumida por beneficiário

| Beneficiário | Base | Regra padrão | Competência |
|---|---|---|---|
| Consultor padrão (MEI ou CLT) | Comissão empresa recebida | Faixa TPS 12/10/8/6% | Data do pagamento |
| Consultor Escalonado (MEI ou CLT) | Comissão empresa por segmento | Matriz produção mensal × TPS | Data/ordem do pagamento; faixa mensal |
| Líder comercial MEI | Comissão empresa recebida de vinculados | 3% se TPS >= 25%; 0% abaixo | Data do pagamento; vínculo no primeiro pagamento |
| Líder comercial CLT | Comissão empresa recebida de vinculados | 0% padrão | Data do pagamento |
| Líder MEI geral | 35% da produção proporcional das unidades | Níveis marginais 1,20% a 0,20% | Data do pagamento |
| Finalização | Comissão empresa recebida das propostas atribuídas | R$ 500 após 70 mil + 0,45% do excedente + bônus | Data do pagamento |
| Líder de finalização | Base total das finalizadoras vinculadas | 0,90% menos desconto | Data do pagamento/período |
| BKO MEI | Lançamento manual | Valor informado | Data efetiva do lançamento |
| BKO CLT | — | Não recebe manualmente | — |

## 20. Inconsistências atuais que não devem virar regra acidental

Estas diferenças existem hoje e precisam de decisão antes da implementação nova:

1. **Status de pagamento:** proposta soma pagamentos que relatórios podem ignorar.
2. **Snapshot de líder:** proposta grava 3% para qualquer TPS; fechamento zera abaixo de 25% e para líder CLT.
3. **Saldo absoluto:** sobrepagamento aparece como “pendente”, sem distinguir crédito de dívida.
4. **Tolerância e comissão:** a resposta da proposta considera comissão integral do consultor quando o status é `finalizada`, inclusive por tolerância de até R$ 10 abaixo; o fechamento semanal continua calculando proporcionalmente ao pagamento recebido.
5. **`refunded_amount`:** representa tanto estorno quanto acumulado/bônus e é somado ao saldo líquido.
6. **Finalização:** não filtra status do pagamento, limita cada pagamento isoladamente e não limita o acumulado da proposta a 100%.
7. **Pagamentos/estornos não atômicos:** criação do lançamento e atualização da proposta usam commits separados em alguns fluxos.
8. **Edição retroativa:** valor/TPS/consultor podem ser alterados sem uma política forte de período fechado.
9. **Faixas escalonadas:** atualização não valida completamente lacunas e sobreposições.
10. **Contagem do líder:** alguns campos chamados quantidade de propostas contam pagamentos.
11. **Pagamento inicial inválido:** uma data malformada pode ser silenciosamente substituída pela data atual.
12. **Autorização:** nem todas as operações financeiras seguem proteção uniforme no backend atual.

## 21. Regras que devem ser parametrizadas no novo sistema

Não devem ficar fixas no código:

- faixas TPS de consultor por regime;
- override individual e sua vigência;
- matriz do MEI Escalonado e vigência;
- modo semanal/mensal do MEI Escalonado;
- percentual e TPS mínimo de líder comercial;
- base e níveis do líder MEI geral;
- unidades cobertas pelo líder MEI geral;
- gatilho, fixo e percentual da finalização;
- percentual do líder de finalização;
- tolerâncias de R$ 10 abaixo e R$ 100 acima;
- conjunto de status de pagamento elegíveis;
- calendário, início de semana e cutoff;
- pessoas sem comissão;
- tipos de ajuste, desconto, bônus e carryover.

Cada configuração financeira deve ter versão, início/fim de vigência, autor, motivo e snapshot nos lançamentos calculados.

## 22. Dados mínimos a migrar

Para reproduzir os cálculos, devem ser preservados:

- proposta, data de negócio, valor, TPS e comissão da empresa;
- consultor e seu papel/regime vigente;
- BKO e finalização;
- todos os pagamentos com valor, status, data, hora e ordem;
- todos os estornos;
- vínculos de consultor-líder com datas;
- faixas de comissão e vigências;
- override individual;
- segmentos/snapshots de cálculo existentes;
- resets e horários de corte;
- bônus manuais, descontos e comissão manual de BKO;
- fechamentos com pago, adiado, acumulado e desconto;
- IDs legados de proposta, pagamento, colaborador e Redmine;
- trilha de auditoria disponível.

## 23. Casos de aceite obrigatórios para a nova implementação

1. Limites exatos de TPS: 24,99; 25; 29,99; 30; 34,99; 35 e 100.
2. Pagamento exato, R$ 10 abaixo, R$ 11 abaixo, R$ 100 acima e R$ 101 acima.
3. Proposta com vários pagamentos em períodos diferentes.
4. Pagamento `PENDING` não afetando nenhum total financeiro definido como elegível.
5. Estorno parcial e total reabrindo o status corretamente.
6. Troca de líder antes e depois do primeiro pagamento.
7. Líder MEI com TPS 24,99 e 25; líder CLT com comissão zero.
8. MEI Escalonado exatamente em 75 mil/175 mil e cruzando uma ou mais faixas.
9. MEI Escalonado com pagamento parcial sem avançar produção não paga.
10. Virada do mês resetando faixa escalonada, sem depender do reset semanal.
11. Finalização em R$ 69.999,99, R$ 70.000,00 e acima, com e sem bônus.
12. Líder de finalização com desconto maior que a comissão, resultando em zero.
13. BKO MEI aceito e BKO CLT rejeitado.
14. Carryover adiado para a semana seguinte.
15. Corte por hora no mesmo dia do reset.
16. Sobrepagamento limitado a 100% na produção e comissão.
17. Tela, API, PDF e fechamento produzindo os mesmos centavos.

## 24. Fonte de verdade recomendada para a implementação

Ao reconstruir, separar claramente:

```text
Proposta = contrato e teto financeiro
Recebimento = entrada de caixa elegível
CommissionEntry = comissão gerada por cada recebimento/ajuste
Settlement = fechamento do período
Payout = dinheiro efetivamente pago ao beneficiário
```

O valor financeiro autoritativo deve vir de lançamentos imutáveis por recebimento e por regra versionada. Snapshots da proposta servem para explicação e projeção, não para substituir o razão de comissão.

## 25. Arquivos do sistema atual que sustentam este documento

- `backend/app/domain/services/commission_calculator.py`;
- `backend/app/domain/services/proportional_commission.py`;
- `backend/app/domain/services/scaled_mei_commission.py`;
- `backend/app/application/services/scaled_mei_commission_service.py`;
- `backend/app/application/services/commission_range_service.py`;
- `backend/app/application/services/lider_service.py`;
- `backend/app/application/services/reports_service.py`;
- `backend/app/application/use_cases/proposal_use_cases.py`;
- `backend/app/api/v1/endpoints/proposals.py`;
- `backend/app/api/v1/endpoints/commission_payments.py`;
- `backend/app/infrastructure/database/models/proposal_models.py`;
- `backend/app/infrastructure/database/models/commission_payment_models.py`;
- `backend/alembic/versions/add_scaled_mei_commission.py`;
- `backend/tests/test_commission_calculator.py`;
- `backend/tests/test_proposal_tolerance.py`;
- `backend/tests/test_commission_payment_rules.py`;
- `backend/tests/test_scaled_mei_paid_production.py`;
- `backend/tests/test_payment_date_validation.py`.

## 26. Decisões de implementação no RF Balance v2 — 17/08/2026

- somente recebimentos `APPROVED` geram produção, comissão e fechamento;
- o teto elegível é acumulado por proposta, inclusive para Finalização;
- a semana operacional padrão vai de sexta a quinta, sem alterar o reset mensal
  do Consultor Escalonado;
- o vínculo `MEI_GERAL` representa explicitamente a cobertura histórica do
  líder MEI geral sobre o consultor/equipe; mudanças futuras não reescrevem
  snapshots passados;
- exceções individuais saem da variável de ambiente e passam a ter vigência,
  autor e motivo;
- estornos nunca apagam crédito: geram débito compensatório explicável;
- bônus, desconto, adiamento, carryover e pagamento são conceitos separados no
  fechamento; `refunded_amount` não é reutilizado;
- período fechado congela cálculo e ajuste, mas não impede registrar o pagamento
  do saldo já fechado;
- BKO permanece manual, positivo, idempotente e exclusivo de MEI.
