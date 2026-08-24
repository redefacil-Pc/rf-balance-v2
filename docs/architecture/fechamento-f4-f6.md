# Fechamento de F4 e F5, e estado parcial da F6

**Data:** 18/08/2026
**Estado:** F4 e F5 implementadas; F6 parcial; homologação do comissionamento
com o Financeiro ainda não realizada.

Este registro segue a separação adotada em
[`fechamento-f1-f3.md`](fechamento-f1-f3.md): conclusão técnica não é
implantação. O cálculo é determinístico e explicável no código, mas nenhum
valor foi comparado contra os casos dourados do v1.

## F4 — motor de comissão

- rule sets e configurações de estratégia versionados por vigência, com
  ativação administrativa e faixas contínuas `[mínimo, máximo)`;
- motor do Consultor padrão e do Consultor MEI Escalonado, com regra resolvida
  pela função vigente na data efetiva do recebimento;
- estratégias de grupo: líder comercial, líder MEI geral, finalizador e líder
  de finalização;
- política individual por beneficiário, para exclusão ou override de TPS;
- `commission_entries` append-only: estorno gera débito compensatório e nunca
  altera o crédito original;
- snapshot de cada cálculo com inputs, outputs, hash, versão e regra aplicada,
  exposto na memória de cálculo da proposta e do recebimento;
- sobrepagamento não libera produção nem comissão acima de 100%.

Detalhes de decisão estão em [`f4-motor-comissao.md`](f4-motor-comissao.md).

## F5 — períodos e fechamento

- períodos com cutoff explícito, sem sobreposição de datas e com fechamento
  bloqueado antes do cutoff;
- geração de settlements por beneficiário, idempotente por período, com
  desconto, bônus, adiamento e carryover para o período seguinte;
- lançamentos manuais de BKO e bônus de finalização tipificados e somados
  separados do bruto calculado;
- registro de pagamento com valor, data, meio e referência;
- período fechado bloqueia a geração de fechamento no domínio, não só na UI;
- **reabertura auditada**: volta o período a `OPEN` sob lock de linha,
  preserva `closed_at`/`closed_by`, exige motivo descritivo e grava auditoria e
  outbox no mesmo commit. Fechamento já pago não pode ser reaberto — a
  correção é por compensação no período atual.

## F6 — o que existe e o que falta

Entregue:

- read model e tela de dashboard;
- relatório financeiro geral, por beneficiário, equipe e unidade, com export
  PDF e XLSX compartilhando os mesmos totais e recortes da tela;
- geração assíncrona e retomável de PDFs por beneficiário e ZIP, persistida em
  `document_jobs` e `stored_documents`, com progresso, retry e dead-letter;
- console de consulta da auditoria append-only.

Ainda **não** entregue:

- orçamento de performance como teste: o marcador `performance` existe no
  `pyproject.toml`, mas nenhum teste mede o p95 do dashboard ou do relatório;
- seed volumétrico da Trilha P, que é o que faria a lentidão aparecer em
  desenvolvimento.

## Evidências locais

Executadas em containers em 18/08/2026:

| Gate | Resultado |
|---|---:|
| Ruff check | aprovado |
| Ruff format | aprovado após reformatar 13 arquivos |
| mypy strict | 438 arquivos sem erro |
| testes unitários | 155 aprovados |
| testes de integração | 163 aprovados |
| suíte completa da API | 318 aprovados em 438,86 s |
| testes de frontend | 103 aprovados |
| build de frontend | aprovado |
| Alembic check | nenhuma operação pendente |

Ressalvas encontradas nesta rodada:

1. `tests/integration/test_commission_settlements_flow.py` tinha data literal
   `2026-08-17` numa exceção individual e passou a falhar sozinho na virada do
   dia, porque a regra recusa vigência retroativa. Corrigido para data relativa
   pelo mesmo relógio da aplicação.
2. `CollaboratorEditModal.test.tsx` fica no limite do `testTimeout` de 5 s do
   Vitest: 1,7 s isolado e 5,1 s sob carga da suíte completa. É flake de CI à
   espera de acontecer.

## Gates externos

Continuam valendo os quatro itens de F1–F3, mais estes:

1. Financeiro percorre o roteiro de
   [`../11-ROTEIRO-HOMOLOGACAO-COMISSOES.md`](../11-ROTEIRO-HOMOLOGACAO-COMISSOES.md)
   e assina os valores;
2. os casos dourados do v1 são comparados contra o v2 — divergência precisa ser
   classificada como erro do v2, erro do v1 ou mudança intencional;
3. as decisões da seção 6 foram fechadas no ADR 0016: reabertura exige duas
   pessoas distintas, estorno vira desconto carregável, liderança não vende e
   sobrepagamento pode ser aprovado sem limite de negócio.
