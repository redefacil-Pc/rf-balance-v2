# F4 — motor de comissão

**Estado:** motores do Consultor padrão e do Consultor Escalonado implementados;
configuração administrativa versionada disponível.

## Decisões aplicadas

- cálculo acontece na escrita, quando o recebimento é reconhecido;
- competência usa a data efetiva do recebimento;
- regra do consultor é resolvida pela função vigente nessa data; MEI/CLT é cadastral;
- faixas usam intervalos contínuos `[mínimo, máximo)`, sem lacuna ou
  sobreposição;
- cada cálculo grava inputs, outputs, hash, versão e regra utilizada;
- `commission_entries` é append-only: estorno cria débito, nunca altera o
  crédito original;
- sobrepagamento nunca libera produção ou comissão acima de 100%.

## Versão inicial

O rule set `STANDARD_CONSULTANT/2026.1` foi criado com vigência-base desde
01/01/2000 para permitir reprodução histórica. Ele atende qualquer colaborador
com função `CONSULTOR`, seja o regime cadastral MEI ou CLT:

| TPS | Percentual |
|---:|---:|
| 0 até abaixo de 25 | 6% |
| 25 até abaixo de 30 | 8% |
| 30 até abaixo de 35 | 10% |
| 35 ou mais | 12% |

Essa configuração inicial é dado versionado na migration, não constante do
calculador. Uma alteração futura deve criar nova versão com vigência futura;
entradas antigas continuam apontando para a versão original.

## Fluxo entregue

```text
Financeiro reconhece recebimento
→ resolve proposta, consultor, regime e regra vigente
→ limita a base ao saldo ainda comissionável
→ calcula produção e comissão proporcionais
→ grava snapshot + crédito + outbox no mesmo commit

Financeiro estorna recebimento
→ mantém o crédito original
→ recalcula somente a redução da base que estava dentro do teto elegível
→ grava débito compensatório ligado ao estorno + outbox no mesmo commit
```

O teto usa o valor líquido de cada recebimento, descontados os estornos. Por
isso um estorno reabre capacidade real para um recebimento substituto gerar
novo crédito. Se a devolução atingir apenas o excedente tolerado ou se outro
recebimento reconhecido continuar cobrindo integralmente o teto, ela não reduz
a comissão.

Consultores com papel `CONSULTOR_MEI_ESCALONADO` são deliberadamente ignorados
pela estratégia padrão e processados pelo motor `SCALED_CONSULTANT`.

### Troca de modalidade do consultor

`MEI` e `CLT` são regimes permitidos para os dois tipos de consultor. A modalidade de
comissão é determinada pela função vigente: `CONSULTOR` para as faixas por TPS
e `CONSULTOR_MEI_ESCALONADO` para o MEI 2 escalonado. A edição do colaborador
faz a troca em uma única transação: encerra a função anterior no dia precedente
e abre a nova na data informada. A operação exige motivo, não aceita vigência
retroativa e preserva a mesma pessoa, conta de acesso, vínculos de equipe,
exceções individuais e histórico de comissões. As duas modalidades não podem
ter vigências sobrepostas.

## Consultor Escalonado

O motor escalonado consome a configuração versionada
`commission_strategy_configs/SCALED_CONSULTANT`. Para cada recebimento aprovado,
ele:

1. limita o recebimento ao saldo elegível da comissão da empresa;
2. converte essa parcela em produção reconhecida proporcional;
3. acumula a produção por consultor e mês civil;
4. divide a nova produção nos segmentos atravessados por R$ 75 mil e R$ 175 mil;
5. cruza cada segmento com a faixa TPS vigente;
6. arredonda comissão da empresa e do consultor por segmento;
7. grava snapshot com acumulado anterior/posterior, segmentos, percentuais e
   versão da configuração, seguido do crédito no ledger.

A ordenação determinística é data de pagamento, horário efetivo (ou criação) e
ID. O modo semanal/mensal permanece apenas uma escolha de exibição e fechamento;
o acumulado sempre reinicia no primeiro dia do mês civil.

No estorno, créditos e snapshots permanecem imutáveis. O motor simula novamente
o mês com os valores líquidos atuais, compara o total ideal com o saldo já
lançado e registra um único débito compensatório. Isso corrige tanto a comissão
da parcela estornada quanto a mudança de faixa das parcelas posteriores.

## Configuração administrativa

A rota `/commission-rules` substituiu o placeholder da F4. Usuários autorizados
podem consultar todas as versões e faixas MEI/CLT, copiar uma versão existente,
editar as faixas e criar um novo rascunho. A ativação é uma permissão separada.

Os campos usam máscara percentual brasileira e escondem a escala técnica do
banco: `6.000000` é exibido como `6%` e `11.500000` como `11,5%`. Alterar o fim
de uma faixa ajusta automaticamente o início da seguinte.

A tela também apresenta, em abas distintas, o mapa completo levantado no
documento de regras: matriz do MEI Escalonado, líder comercial, líder MEI geral,
Finalização, líder de Finalização e BKO. Os cinco grupos automáticos possuem
configuração persistida, editor específico, rascunho, vigência e ativação. BKO
continua identificado como lançamento manual, sem percentual automático.

Uma regra ativa não é editada no lugar. O comando **Corrigir em nova versão**
copia seus parâmetros, permite ajustar faixas, percentuais e valores com
máscaras brasileiras e cria um rascunho futuro. A ativação encerra a vigência
anterior sem modificar cálculos históricos. A persistência dessas estratégias
é consumida pelos respectivos motores na data efetiva do recebimento. Os quatro
limites TPS do Escalonado também são editáveis e validados como intervalos
contínuos, não apenas usados como cabeçalhos fixos.

O backend exige vigência futura, motivo, cobertura completa dos dois regimes e
faixas contínuas iniciadas em zero. Ao ativar, ele encaixa a nova versão na
linha temporal: encerra a anterior no dia precedente e, quando já existe uma
versão futura, termina a nova no dia anterior à seguinte. Cálculos e versões
anteriores não são alterados.

Endpoints:

- `GET /api/v1/commission-rule-sets`;
- `POST /api/v1/commission-rule-sets`;
- `POST /api/v1/commission-rule-sets/{id}/activation`.
- `GET /api/v1/commission-strategy-configs`;
- `POST /api/v1/commission-strategy-configs`;
- `POST /api/v1/commission-strategy-configs/{id}/activation`.

## Estratégias coletivas e finalização

O reconhecimento materializa também:

- `COMMERCIAL_LEADER`: líder histórico vigente no primeiro recebimento, com 3%
  para líder MEI quando TPS >= 25% e zero para as demais combinações padrão;
- `GENERAL_MEI_LEADER`: vínculo histórico `MEI_GERAL`, produção proporcional e
  níveis marginais sobre a base configurável de 35%;
- `FINALIZER`: delta semanal da fórmula de gatilho, fixo e excedente;
- `FINALIZATION_LEADER`: delta semanal sobre a base das finalizadoras vinculadas.

Cada estratégia grava beneficiário, vínculo/base anterior e posterior, versão,
percentuais e segmentos. Estorno recalcula o direito ideal do período e cria
débito compensatório. A unicidade do ledger distingue snapshot e estratégia,
permitindo que um recebimento afete vários beneficiários com segurança.

## Exceções individuais

`commission_beneficiary_policies` substitui a variável global do legado por
configuração com vigência, autor e motivo. Uma política pode excluir totalmente
o direito ou definir percentual próprio do Consultor padrão para TPS >= 35%.
No Escalonado, a exclusão zera a comissão, mas a produção reconhecida continua
avançando a faixa mensal. A política aplicada integra o snapshot explicável.

## Explicação, BKO e fechamento

As rotas de memória de cálculo por proposta/recebimento retornam inputs,
outputs, segmentos, regra, créditos, débitos e líquido. A interface expõe “Ver
cálculo” em cada recebimento e “Memória completa da proposta” no fluxo da
proposta, somente a perfis com acesso aos fechamentos.

BKO MEI recebe crédito manual positivo e idempotente; BKO CLT é rejeitado. O
fechamento agrega razão automática e BKO por beneficiário/período, mantendo em
campos distintos bruto, carryover, bônus, desconto, adiado, pago e a pagar.
Pagamento parcial é validado contra o saldo e fechamento quitado não aceita
novos ajustes.

`commission_periods` registra início, fim e cutoff. Depois de `CLOSED`, geração
e ajustes ficam bloqueados; o pagamento do fechamento continua permitido. O
estorno financeiro posterior preserva snapshots/créditos e lança a compensação
na competência atual.

Endpoints adicionais:

- `GET /api/v1/proposals/{id}/commission-calculations`;
- `GET /api/v1/receipts/{id}/commission-calculations`;
- `GET|POST /api/v1/commission-beneficiary-policies`;
- `POST /api/v1/commission-bko-entries`;
- `GET|POST /api/v1/commission-settlements` e ações de ajuste/pagamento;
- `GET|POST /api/v1/commission-periods` e ação de fechamento.
