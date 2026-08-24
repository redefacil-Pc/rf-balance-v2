# Relatório de homologação financeira

**Execução técnica:** 21/08/2026  
**Ambiente:** banco isolado `rfbalance_test`  
**Banco oficial:** não utilizado  
**Resultado técnico sintético:** APROVADO  
**Comparação com o v1:** PENDENTE  
**Aceite do Financeiro:** PENDENTE

## Evidências automatizadas

### Comissão por proposta

Os sete cenários foram criados pelos casos de uso reais e validados
automaticamente. A repetição não duplicou propostas.

| Caso | Recebido | Comissão | Pendente | Resultado |
|---|---:|---:|---:|---|
| TPS abaixo de 25% | R$ 2.499,00 | R$ 149,94 | 0 | APROVADO |
| TPS em 25%, parcial | R$ 1.250,00 | R$ 100,00 | 0 | APROVADO |
| TPS em 35%, excedente | R$ 3.500,00 | R$ 420,00 | 0 | APROVADO |
| Escalonado até 75 mil | R$ 26.250,00 | R$ 2.100,00 | 0 | APROVADO |
| Escalonado cruzando faixa | R$ 7.000,00 | R$ 700,00 | 0 | APROVADO |
| Estorno e substituição | R$ 1.000,00 | R$ 60,00 | 0 | APROVADO |
| Recebimento pendente | R$ 200,00 | R$ 12,00 | 1 | APROVADO |

### Liderança

O gerador foi executado duas vezes sobre a mesma massa, sem duplicar vínculos
ou valores.

| Estratégia | Valor esperado e apurado | Resultado |
|---|---:|---|
| Líder comercial | R$ 1.140,00 | APROVADO |
| Líder MEI geral | R$ 554,40 | APROVADO |
| Líder de Finalização | R$ 375,29 | APROVADO |

### Fechamentos

O gerador foi executado duas vezes sobre a mesma massa. Pagamentos e ajustes
permaneceram idempotentes.

| Caso | Bruto | Pago | A pagar | Estado | Resultado |
|---|---:|---:|---:|---|---|
| BKO anterior com adiamento | R$ 200,00 | R$ 120,00 | R$ 0,00 | DEFERRED | APROVADO |
| BKO atual com carryover e ajustes | R$ 300,00 | R$ 200,00 | R$ 110,00 | DEFERRED | APROVADO |
| Consultor escalonado | R$ 2.800,00 | R$ 2.800,00 | R$ 0,00 | PAID | APROVADO |
| Finalização manual | R$ 0,00 | R$ 0,00 | R$ 300,00 | PENDING | APROVADO |

### Desempenho

Com 20 mil propostas sintéticas no banco de performance:

| Consulta | p95 apurado | Orçamento | Resultado |
|---|---:|---:|---|
| Dashboard de 3 anos | 0,315 s | 2,000 s | APROVADO |
| Relatório trimestral | 0,191 s | 5,000 s | APROVADO |

### Executor de casos dourados

O arquivo `business-rules/casos-dourados-v1.csv` foi executado contra as
configurações ativas da v2 em 21/08/2026:

- 40 casos lidos;
- 37 casos calculáveis aprovados;
- 0 divergências;
- 0 erros;
- 3 lançamentos manuais separados para conferência pelo fluxo de fechamento.

O relatório detalhado é gerado em
`data/homologacao/resultado-casos-dourados-v2.csv`. O comando pode ser repetido
com `make validate-golden` ou `scripts/rfb.ps1 validate-golden`.

## Pendência para equivalência com o v1

Não existe neste workspace um dump do v1 nem uma amostra anonimizada aprovada
pelo Financeiro. Por isso, este documento não afirma equivalência entre v1 e
v2. Para concluir o aceite:

1. usar as 40 linhas sintéticas já disponíveis em
   `business-rules/casos-dourados-v1.csv` para executar o roteiro funcional;
2. antes do aceite de equivalência, substituir `v1_reference` e os valores
   esperados por 30 a 50 casos reais anonimizados do v1;
3. recalcular os mesmos casos na v2;
4. classificar toda divergência como erro da v2, erro do v1 ou mudança
   intencional aprovada;
5. obter nome, data e aceite explícito do responsável financeiro abaixo.

## Aceite

- Responsável financeiro:
- Data:
- Quantidade de casos comparados:
- Divergências não resolvidas:
- Decisão: APROVADO / REPROVADO
- Observações:
