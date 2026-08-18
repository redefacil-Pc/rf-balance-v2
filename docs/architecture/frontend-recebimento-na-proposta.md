# Frontend: recebimento declarado na proposta

Registro da mudança de fluxo aplicada no backend e no frontend.

**Estado:** concluído e coberto por testes de integração e de frontend.

---

## 1. O que mudou, e por quê

O fluxo real do negócio é: **a Finalização lança a proposta com os valores
recebidos e os comprovantes; o Financeiro confere no extrato e aprova.** Uma
aprovação, não duas.

O sistema fazia o contrário — aprovava a proposta primeiro, e só depois alguém
lançava o recebimento. Isso tinha três consequências ruins:

1. O Financeiro aprovava **às cegas**: no momento da decisão, `paid_amount` era
   obrigatoriamente `0.00`, porque uma trava impedia qualquer lançamento antes
   da aprovação. Não havia valor algum para conferir contra o extrato.
2. Eram **duas decisões** do Financeiro — a da proposta e a do recebimento.
3. O comprovante era pedido **duas vezes**: um para submeter a proposta, outro
   por recebimento. No fluxo real, o mesmo documento.

### O modelo agora

Três janelas, e o que muda entre elas é **quando** o Financeiro confere:

| Estado da proposta | Declara recebimento? | Quem confere |
|---|---|---|
| Rascunho (`DRAFT`) ou devolvida (`REJECTED`) | sim | a **aprovação da proposta**, tudo de uma vez |
| Enviada (`SUBMITTED`) | **não** | — conjunto congelado |
| Aprovada (`APPROVED`) com saldo em aberto | sim | **decisão avulsa** do Financeiro |
| Quitada (`PAID`) ou cancelada | não | — |

A janela do meio existe para que o Financeiro não confira uma coisa e aprove
outra. A última linha responde ao pagamento parcelado: o cliente paga parte
agora e o resto depois, e o restante precisa entrar.

A regra vive no domínio, em `Proposal.aceita_recebimento` — o frontend **não a
reimplementa**, apenas reflete o que a API responde.

---

## 2. Contrato da API

### Declarar recebimento (Finalização)

```
POST /api/v1/proposals/{proposal_id}/receipts
Content-Type: multipart/form-data
Idempotency-Key: <uuid>          # obrigatório

amount, business_date, payment_time, payment_method, reference?, notes?, proof (arquivo)
→ 201 ReceiptWriteResponse
```

Permissão `receipts:write` **e** papel Financeiro, ou Operacional com função
operacional `FINALIZACAO` vigente. Erros:

| Situação | Status | `type` |
|---|---|---|
| Proposta enviada, aguardando decisão | 409 | `invalid-receipt-flow` |
| Proposta quitada | 409 | `invalid-receipt-flow` |
| Comprovante não é PDF/JPG/PNG, vazio ou > 10 MB | 422 | `invalid-receipt` |
| Mesma chave com outro valor | 409 | `idempotency-key-conflict` |
| Papel sem direito de lançar | 403 | `receipt-launcher-not-allowed` |

O `detail` do 409 explica o motivo ("aguardando a conferência do financeiro" ou
"já está quitada"). **Exiba o `detail`**, não uma mensagem própria.

Mesma chave com o mesmo conteúdo devolve o mesmo recebimento (201) — reenvio não
duplica.

### Remover recebimento declarado (correção)

```
DELETE /api/v1/receipts/{receipt_id}   → 204
```

Só enquanto não conferido e a proposta aceita recebimento. Substitui a antiga
"devolução" no momento do cadastro: quem digitou errado apaga e refaz.

### Conferir pagamento posterior (Financeiro)

```
POST /api/v1/receipts/{receipt_id}/decision
{ "decision": "APPROVE" | "REJECT", "reason": "..." }
→ 200 ReceiptWriteResponse
```

**Só vale para recebimento declarado depois da proposta aprovada.** O que foi
declarado antes do envio devolve `409` com *"será conferido junto da aprovação da
proposta"*. Quem declarou não confere o próprio lançamento (`403
receipt-self-approval`).

### Aprovar a proposta (Financeiro) — reconhece o dinheiro

```
POST /api/v1/proposals/{id}/decision
{ "version": n, "decision": "APROVAR" | "DEVOLVER", "reason": "..." }
```

Inalterado no contrato, **mudou no efeito**: aprovar agora reconhece os
recebimentos declarados e move `paid_amount` / `outstanding_amount` / `status`
da proposta no mesmo commit. Devolver não reconhece nada.

### Estorno (Financeiro)

```
POST /api/v1/receipts/{receipt_id}/reversal
{ "reason": "...", "business_date": "YYYY-MM-DD", "amount": "100.00"? }
```

Só sobre recebimento já reconhecido. `amount` é opcional: sem ele, estorna todo
o saldo restante; com ele, permite estornos parciais sucessivos. Cada estorno é
um lançamento compensatório imutável, reabre o saldo correspondente e volta a
permitir declaração.

---

## 3. Mapa da implementação

### 3.1 `features/receipts/mutations/useReceiptActions.ts`

- **Manter** `useCreateReceipt` (o endpoint não mudou) e `useReverseReceipt`.
- **Manter** a mutation de decisão, mas renomear para deixar o escopo claro —
  ela agora só serve a pagamento posterior. Sugestão: `useConferirPagamento`.
- **Acrescentar** `useRemoveReceipt` (`DELETE /receipts/{id}`), invalidando as
  mesmas chaves.

> O `useInvalidate` atual já invalida `['receipts']` e `['proposals']`. Mantenha:
> declarar e conferir mudam o saldo da proposta.

### 3.2 `features/receipts/types.ts`

`ReceiptStatus` continua `SUBMITTED | APPROVED | REJECTED`, mas os rótulos
mudam de sentido. Use:

| Valor | Rótulo na tela |
|---|---|
| `SUBMITTED` | **Declarado** (aguardando conferência) |
| `APPROVED` | **Reconhecido** |
| `REJECTED` | **Devolvido** |

"Aprovado" some do vocabulário de recebimento — quem aprova é a proposta.

### 3.3 `features/proposals/` — onde a declaração passa a morar

Esta é a mudança central: **declarar recebimento vira parte de montar a
proposta**, ao lado do anexo.

- Criar `queries/useProposalReceipts.ts` → `GET /receipts?proposal_id={id}`,
  com chave `proposalKeys.recebimentos(id)`.
- No `components/ProposalApprovalModal.tsx`, acrescentar uma seção
  **"Valores recebidos"** ao lado da seção de comprovantes já existente:
  - lista os recebimentos com valor, data, meio de pagamento e link do
    comprovante;
  - mostra o **total declarado** e compara com a comissão da proposta, para o
    operador ver quanto falta antes de enviar;
  - com a proposta editável e permissão de lançar: botão **Declarar recebimento**
    (abre o formulário) e **remover** por linha;
  - com a proposta aprovada e saldo em aberto: mesmo botão, e cada declaração
    nova aparece como "aguardando conferência".
- Mover `ReceiptCreateModal` de `features/receipts/components/` para
  `features/proposals/components/`, ou torná-lo genérico recebendo
  `proposalId` — hoje ele já recebe. **Não duplique o componente.**

> Import cruzado entre features é proibido pela convenção do projeto. Se o
> formulário for usado nas duas telas, o lugar dele é `shared/components/`, ou
> cada feature tem o seu. Decida antes de codar; não importe
> `features/receipts/...` de dentro de `features/proposals/...`.

### 3.4 `features/proposals/components/ProposalApprovalModal.tsx` — lado do Financeiro

Quando a proposta está `SUBMITTED` e o usuário tem `proposals:approve`:

- exibir a lista de valores declarados **em destaque**, com o total, porque é o
  que ele confere no extrato;
- deixar claro no texto do botão que aprovar reconhece o dinheiro — hoje o botão
  diz apenas "Aprovar";
- após aprovar, o detalhe da proposta volta com `paid_amount` e
  `outstanding_amount` atualizados: as queries já são invalidadas, basta exibir.

### 3.5 `features/receipts/pages/ReceiptsPage.tsx`

A tela deixa de ser "onde se lança recebimento" e vira **a fila do Financeiro**:

- **Remover** o botão de lançar (`ReceiptCreateModal`) — declarar agora acontece
  na proposta. A linha `canLaunch` sai.
- **Manter** a lista, o filtro por situação e o estorno.
- A ação de conferir só aparece para recebimento `SUBMITTED` **de proposta já
  aprovada**. Como a listagem não devolve o estado de aprovação da proposta,
  há duas saídas:
  1. acrescentar `proposal_approval_status` ao `ReceiptResponse` no backend
     (preferível — evita adivinhação no cliente); ou
  2. tentar a conferência e tratar o `409` exibindo o `detail`.

  **Recomendo (1)**: sem isso a tela mostra um botão que às vezes falha, e o
  usuário não tem como saber de antemão.

### 3.6 `features/receipts/components/ReceiptActionModal.tsx`

- Ajustar os rótulos: "Conferir pagamento" em vez de "Aprovar recebimento".
- O texto da devolução deve dizer que o valor **não entra no saldo**.

---

## 4. Sequência sugerida

1. **Backend primeiro**, se optar pelo item 3.5(1): acrescentar
   `proposal_approval_status` em `ReceiptResponse` — mudança pequena e destrava
   a tela.
2. `useProposalReceipts` + seção "Valores recebidos" no modal da proposta
   (leitura). Já dá para ver o efeito sem quebrar nada.
3. Mover a declaração para a proposta; remover o botão da `ReceiptsPage`.
4. `useRemoveReceipt` e o botão de remover por linha.
5. Rótulos e textos.

---

## 5. O que testar

Testes de componente (Vitest + Testing Library, mock no nível do client de API):

- proposta em rascunho mostra o botão de declarar; proposta enviada **não**;
- proposta aprovada com saldo em aberto mostra o botão de novo;
- proposta quitada não mostra;
- o total declarado aparece e bate com a soma das linhas;
- erro `409` da API é exibido com o `detail` do Problem Details, não com texto
  inventado pela tela;
- na fila do Financeiro, a ação de conferir não aparece para recebimento de
  proposta ainda não aprovada.

O E2E de referência já existe no backend em
`tests/integration/test_receipts_flow.py` — os nomes dos testes descrevem o
comportamento esperado de cada tela.

---

## 6. Armadilhas

- **Não recalcule dinheiro no cliente.** O total declarado é soma de exibição;
  `paid_amount` e `outstanding_amount` vêm prontos da API. Nunca `parseFloat`
  para somar e reexibir.
- **`Idempotency-Key` reutilizada no retry.** A mutation atual gera
  `crypto.randomUUID()` dentro do `mutationFn` — em retry isso produz chave nova
  e pode duplicar lançamento. Gere a chave **quando o formulário abre** e
  reutilize-a enquanto for o mesmo envio.
- **A permissão não basta.** `receipts:write` abre a porta, mas a rota também
  exige função operacional `FINALIZACAO` vigente. Esconder o botão é UX; o 403
  continua possível e precisa ser tratado.
- **Estorno não é remoção.** Remover só vale antes da conferência; depois de
  reconhecido, o caminho é o estorno, que preserva o histórico.
