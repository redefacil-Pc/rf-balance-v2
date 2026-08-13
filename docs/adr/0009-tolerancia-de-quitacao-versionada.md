# 0009 — Tolerância de quitação como política versionada

- **Status:** proposto — o **mecanismo** está implementado; os **limites** aguardam confirmação do financeiro
- **Data:** 2026-08-12
- **Decisores:** Orlean
- **Fase afetada:** F2 (proposta e status), consumido pela F3 (recebimentos) e F4 (comissão)

## Contexto

O sistema atual considera quitada uma proposta com diferença de até **R$ 10,00 abaixo** ou **R$ 100,00 acima** da comissão da empresa (seção 7.4). Os valores estão espalhados como constante no código, sem registro de quando passaram a valer.

Isso cria dois problemas concretos. O primeiro é de manutenção: mudar a tolerância exige achar todas as cópias. O segundo é pior e só aparece no fechamento — um recálculo feito hoje sobre um período antigo usaria a tolerância de hoje, e a proposta que estava quitada em março pode "desquitar" em agosto sem que ninguém tenha alterado nada.

Falta também definir o que acontece **acima** do excedente tolerado. É uma das perguntas em aberto da seção 21 (sobrepagamento).

## Decisão

A tolerância é uma **política versionada**, não uma constante: `SettlementTolerancePolicy(versao, falta_tolerada, excedente_tolerado)`, resolvida por identificador de versão.

A versão aplicada é **gravada na proposta** (`proposals.tolerance_policy_version`). Recálculo e shadow mode resolvem a política pela versão gravada, não pela vigente. Versão desconhecida levanta erro em vez de cair na vigente — silenciar aqui reescreveria a história de um fechamento já feito.

Os limites do v1 ficam congelados como versão `v1` (−R$ 10,00 / +R$ 100,00), para o shadow mode da F7 comparar proposta a proposta sem "por que deu diferente".

A classificação tem **três** resultados, não dois:

| Diferença (recebido − comissão) | Resultado | Status da proposta |
|---|---|---|
| menor que −`falta_tolerada` | `EM_ABERTO` | `OPEN` ou `PARTIALLY_PAID` |
| entre −`falta_tolerada` e +`excedente_tolerado` | `QUITADA` | `PAID` |
| acima de +`excedente_tolerado` | `SOBREPAGAMENTO` | `PAID`, com sinalização |

Sobrepagamento **quita** a proposta — o dinheiro entrou — mas fica marcado para decisão do financeiro, e a API o expõe (`overpaid`). O que fazer com o excedente (devolver, abater, provisionar) continua em aberto e será decidido em ADR próprio.

Decorrência: a falta tolerada **não** entra no "a receber". `outstanding_amount` é zero em proposta quitada, senão a carteira do dashboard acumularia centavos de propostas que ninguém vai cobrar.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Constante no código (como hoje) | Nada a construir | Recálculo antigo usa tolerância nova; mudança exige deploy | É o defeito que a reconstrução corrige |
| Tabela de configuração editável, sem versão | Muda sem deploy | Editar a linha muda o passado retroativamente | Perde a mesma garantia, com mais infraestrutura |
| Tolerância por empresa/unidade | Flexível | Não há demanda observada; multiplica o espaço de teste do fechamento | Adicionável depois como dimensão da política, sem quebrar o versionamento |
| Sobrepagamento tratado como quitação simples | Menos conceito | O excedente some do radar do financeiro | Dinheiro a mais precisa aparecer para alguém decidir |

## Consequências

**Obrigatório:**

- Quem decide quitação é a política; nenhuma comparação de valor com `10` ou `100` solta no código, no SQL ou no frontend.
- Toda proposta grava a versão da política que a classificou.
- Limite novo é **versão nova** (`v2`), nunca edição da `v1`.

**Proibido:**

- Resolver versão desconhecida caindo na vigente.
- Recalcular período fechado com política diferente da que foi gravada.

**A revisitar:**

- Os limites do v1 precisam de confirmação do financeiro (seção 21). Confirmados, este ADR passa a `aceito`; alterados, entra a `v2` e este registro explica a transição.
- O destino do excedente em sobrepagamento é decisão separada, esperada para a F3.

## Impacto financeiro ou de dados

Alto e direto: a política decide se a proposta está paga, e o status da proposta alimenta o motor de comissão da F4. Um limite errado paga comissão sobre proposta não quitada — ou deixa de pagar comissão devida. Por isso as faixas, incluindo os dois valores exatos de fronteira, são cobertas por teste unitário.
