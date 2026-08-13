# apps/web — frontend

React + TypeScript + Vite, React Router, TanStack Query, React Hook Form + Zod, Vitest + Testing Library, Playwright.

## Estrutura

```text
src/
|-- app/
|   |-- router/         # definição de rotas, uma rota por arquivo quando tem loader/guard
|   |-- providers/      # query client, auth, tema — um provider por arquivo
|   `-- layouts/        # shells de página
|-- features/           # um diretório por área funcional
|-- shared/
|   |-- api/            # client gerado do OpenAPI + interceptors
|   |-- components/     # componentes reutilizáveis entre features
|   |-- formatters/     # currency.ts, date.ts, document.ts — um por tipo
|   |-- hooks/          # hooks genéricos
|   |-- types/          # tipos compartilhados
|   `-- lib/            # adaptadores de bibliotecas externas
`-- main.tsx
```

## Template de feature

```text
features/<feature>/
|-- pages/          # uma página por arquivo, só composição
|-- components/     # componentes daquela feature
|-- queries/        # um hook de leitura por arquivo (useProposalList.ts)
|-- mutations/      # um hook de escrita por arquivo (useRegisterReceipt.ts)
|-- schemas/        # schemas Zod — um por formulário
|-- hooks/          # lógica de UI local
`-- __tests__/      # testes da feature
```

Features existentes: `auth`, `collaborators`, `teams`, `proposals`, `receipts`, `commission-rules`, `settlements`, `dashboard`, `reports`, `audit`.

**Import cruzado entre features é proibido.** O que duas features precisam vai para `shared/`.

## Regras de arquivo

| Arquivo | Contém | Não contém |
|---|---|---|
| `pages/*.tsx` | composição de componentes e hooks | fetch direto, cálculo |
| `components/*.tsx` | apresentação, recebe dado pronto | busca de dado |
| `queries/*.ts` | um `useQuery` com query key hierárquica | mutação |
| `mutations/*.ts` | um `useMutation` + invalidação das keys | formatação |
| `schemas/*.ts` | um schema Zod e o tipo inferido | chamada de API |
| `shared/formatters/*.ts` | uma formatação | regra de negócio |

## Invariantes

- **Nenhuma conta financeira no cliente.** Dinheiro chega como string decimal (`"1234.56"`) e é apenas formatado com `Intl.NumberFormat('pt-BR', ...)`. Sem `parseFloat` para somar.
- Filtro, busca, paginação e período vivem nos search params da URL.
- Client de API é gerado do OpenAPI, nunca escrito à mão.
- `Idempotency-Key` gerado no início da interação e reutilizado no retry.
- Esconder botão não é autorização — o backend valida de qualquer forma.
- Todo estado coberto: loading, vazio, erro, sem permissão.
- WCAG 2.1 AA: teste por `getByRole`/`getByLabelText`, não por classe CSS.
