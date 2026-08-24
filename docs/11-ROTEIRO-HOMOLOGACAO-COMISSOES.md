# Roteiro de homologação do comissionamento

## Preparar a massa local

O comando abaixo cria propostas, comprovantes, recebimentos, aprovações,
estornos, snapshots e lançamentos usando os casos de uso reais da aplicação:

```bash
make seed-commission-demo
```

Alternativa no Windows, sem `make`:

```powershell
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env exec -T api python -m app.platform.db.seed_commission_demo
```

O comando não executa em produção e é idempotente: pode ser repetido sem
duplicar as propostas. Os registros usam o prefixo
`TESTE-COMISSAO-20260817` no campo **ID externo**.

## Conferência pela interface

1. Abra **Propostas**.
2. No filtro **ID externo**, pesquise `TESTE-COMISSAO-20260817`.
3. Abra a proposta desejada pela ação de aprovação/detalhes.
4. Em **Valores recebidos**, confira o valor e a situação.
5. Clique no ícone de calculadora para conferir um recebimento isolado.
6. Clique em **Memória completa da proposta** para conferir todos os
   beneficiários, regras, bases, créditos e débitos.
7. Abra **Recebimentos** para conferir o lançamento pendente e os estornos.

O perfil usado precisa possuir a permissão `settlements:read` para visualizar
a memória de cálculo.

## Resultados esperados

| ID externo (sufixo) | O que valida | Recebido reconhecido | Comissão líquida esperada |
|---|---|---:|---:|
| `TPS-24-99` | Limite imediatamente abaixo de 25%, faixa de 6% | R$ 2.499,00 | R$ 149,94 |
| `TPS-25-PARCIAL` | Limite exato de 25%, faixa de 8%, pagamento parcial | R$ 1.250,00 | R$ 100,00 |
| `TPS-35-EXCEDENTE` | Faixa de 12%, sobrepagamento de R$ 50 estornado sem reduzir direito | R$ 3.500,00 | R$ 420,00 |
| `ESCALONADO-75K` | Produção escalonada até o primeiro limite mensal | R$ 26.250,00 | R$ 2.100,00 |
| `ESCALONADO-CRUZA` | Produção seguinte atravessando a faixa mensal | R$ 7.000,00 | R$ 700,00 |
| `ESTORNO-SUBSTITUTO` | Crédito original, débito de estorno e novo crédito substituto | R$ 1.000,00 | R$ 60,00 |
| `RECEBIMENTO-PENDENTE` | `SUBMITTED` não entra no caixa nem gera comissão | R$ 200,00 | R$ 12,00 |

No último cenário existe também um recebimento de R$ 300,00 aguardando o
Financeiro. Antes de sua aprovação, ele não pode alterar o recebido reconhecido
de R$ 200,00 nem a comissão de R$ 12,00.

Os totais da tabela consideram todas as estratégias materializadas na proposta.
As estratégias de Finalização podem produzir snapshot de valor zero enquanto o
gatilho semanal configurado ainda não tiver sido alcançado; isso é esperado e
deve aparecer na memória de cálculo.

## Critérios de aceite visual

- os valores devem aparecer sempre com duas casas decimais;
- a memória deve identificar beneficiário, estratégia e versão da regra;
- cada recebimento aprovado deve mostrar a base efetivamente aproveitada;
- o estorno deve aparecer como débito, sem apagar o crédito original;
- o recebimento substituto deve criar um novo crédito;
- o recebimento pendente não deve possuir snapshot nem lançamento;
- o total líquido exibido deve coincidir com a tabela acima.

## Massa de fechamento e pagamento

Depois das propostas, execute:

```bash
make seed-settlement-demo
```

No Windows:

```powershell
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env exec -T api python -m app.platform.db.seed_settlement_demo
```

O comando demonstra:

- colaborador isolado **Teste BKO Carryover**, sem alterar fechamentos reais;
- BKO manual de R$ 200,00 na semana de duas competências atrás;
- pagamento de R$ 120,00 e adiamento de R$ 80,00 nesse fechamento;
- fechamento e congelamento da semana anterior;
- BKO atual de R$ 300,00 com carryover de R$ 80,00 nos sete dias que terminam hoje;
- bônus de R$ 50,00, desconto de R$ 20,00, adiamento de R$ 100,00 e
  pagamento parcial de R$ 200,00, restando R$ 110,00;
- Consultor Escalonado com pagamento integral de R$ 2.800,00;
- Finalização CLT isolada com bônus manual de R$ 300,00;
- período atual aberto para continuar a homologação.

Na tela **Fechamentos de comissão**, selecione o período informado pelo comando. Os
cartões mostram a soma de bruto, acréscimos, valores retidos, pago e a pagar. A
tabela preserva a composição por beneficiário.

Na tela **Relatório financeiro**, use o mesmo período para conferir:

- faturamento aprovado, estornos e faturamento reconhecido;
- produção reconhecida sem duplicar as estratégias de liderança;
- comissões separadas entre consultores, liderança, finalização e BKO;
- total de comissões e faturamento líquido;
- bônus, descontos, adiamentos, pagamentos e saldo a pagar dos fechamentos;
- composição por beneficiário. Em **Detalhar**, cada valor automático informa
  proposta, recebimento e regra; lançamentos de BKO e bônus de Finalização aparecem
  identificados como manuais.

Essa apresentação implementa a composição descrita nas seções 14 e 15 do
documento-base. Produção, faturamento e detalhamento por consultor/equipe são
uma visão analítica separada, com escopo de acesso próprio.

## Equipes e comissões de liderança

Depois da massa de propostas, execute:

```bash
make seed-leadership-demo
```

O comando usa os casos de uso oficiais, pode ser repetido sem duplicar dados e
forma estas equipes vigentes na data da execução:

- **Bruno Lider / Comercial:** Carla Consultora e Teste Consultor Escalonado;
- **Elena Lider MEI / MEI Geral:** Carla Consultora e Teste Consultor Escalonado;
- **Fabio Lider Final / Finalização:** Ana Operacional.

| Liderança | Estratégia | Comissão bruta |
|---|---|---:|
| Bruno Lider | Líder comercial | R$ 1.140,00 |
| Elena Lider MEI | Líder MEI geral | R$ 554,40 |
| Fabio Lider Final | Líder de Finalização | R$ 375,29 |

Na tela **Equipes**, a seção **Equipes vigentes** mostra diretamente os vínculos
agrupados por líder e finalidade. Use a data de referência para conferir a
composição atual ou reconstruir como cada equipe estava formada no passado.
As ferramentas abaixo continuam disponíveis para criar ou transferir vínculos,
consultar o histórico individual e encerrar uma vigência.
Em **Fechamentos** e **Relatório financeiro**, os três beneficiários aparecem
juntos no setor **Lideranças**, com detalhamento até proposta e recebimento.

As massas de fechamento e liderança devem ser validadas em bancos de teste
separados, ou com uma limpeza entre elas. As duas exercitam intencionalmente o
período corrente e poderiam alterar os totais uma da outra.

## Dashboard, auditoria e exportações

O **Dashboard** usa o período mensal por padrão e permite alternar para semana
ou intervalo personalizado. Confira produção aprovada, faturamento reconhecido,
comissões, faturamento líquido, comissão da empresa, pendência financeira, TPS
médio, situação das propostas, evolução diária e ranking. O recorte acompanha o
perfil: Admin/Financeiro veem o consolidado; liderança vê sua equipe; consultor
vê a própria participação; operacional vê o que cadastrou.

Na tela **Auditoria**, filtre a trilha por período, módulo, ação, ator, entidade
ou correlação. O botão **Detalhar** apresenta o contexto seguro registrado no
evento; a tela nunca altera nem remove eventos.

No **Relatório financeiro**, use **Baixar PDF** ou **Exportar XLSX**. Os dois
arquivos são gerados a partir do mesmo DTO da tela. O XLSX contém as planilhas
`Resumo` e `Beneficiários`; o PDF apresenta o consolidado e a composição. A
exportação exige simultaneamente as permissões `reports:export` e
`settlements:read`.
