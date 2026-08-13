---
name: rfb-frontend
description: Frontend do RF Balance em React + TypeScript + Vite — criar página, feature, formulário, tabela, componente, hook, query/mutation TanStack Query, schema Zod, rota, estado, acessibilidade e teste de UI. Use para qualquer trabalho em frontend/src, consumo da API, exibição de valores financeiros, fluxo de exportação/PDF ou revisão de UX de tela.
---

# Frontend — RF Balance

Stack: React + TypeScript + Vite, React Router, TanStack Query (estado remoto), React Hook Form + Zod (formulários), biblioteca de componentes acessíveis, client TypeScript **gerado do OpenAPI**, Vitest + Testing Library (componentes), Playwright (E2E).

## Regra número um

O frontend **não calcula dinheiro**. Produção, comissão, base, rateio, total de fechamento — tudo vem calculado do backend e é apenas formatado. Nenhuma soma, percentual ou rateio em `.tsx`. Se o valor que a tela precisa não existe no DTO, o endpoint muda; a tela não improvisa.

Autorização também não é do frontend: esconder botão é UX, não segurança. A permissão é checada no backend de qualquer forma.

## Organização por feature

```text
src/
|-- app/                  # bootstrap, router, providers
|-- features/
|   |-- auth/  collaborators/  teams/  proposals/  receipts/
|   |-- commission-rules/  settlements/  dashboard/  reports/  audit/
|-- shared/
|   |-- api/              # client gerado + interceptors
|   |-- components/  formatters/  hooks/  types/
`-- main.tsx
```

Cada feature contém `pages/`, `components/`, `queries/`, `mutations/`, `schemas/` e seus testes. Import cruzado entre features é proibido — o que é comum sobe para `shared/`.

## Rotas

```text
/login  /dashboard  /collaborators  /collaborators/:id  /teams
/proposals  /proposals/new  /proposals/:id
/commission-rules  /periods  /settlements  /reports  /audit
/admin/users  /admin/operations
```

Filtro, busca, paginação e período **vivem na URL** (search params), não em `useState` — a tela precisa ser compartilhável e recarregável.

## Client de API

- Gerado do OpenAPI, nunca escrito à mão; regerar quando o contrato muda.
- Não montar URL com string concatenada em componente.
- Interceptor central cuida de `X-Correlation-ID`, refresh de sessão e conversão de Problem Details em erro tipado.
- Comando financeiro envia `Idempotency-Key` gerado no início da interação e **reutilizado no retry**, não regerado a cada clique.

## Estado

- Servidor: TanStack Query. Chaves hierárquicas: `['proposals', 'list', params]`, `['proposals', 'detail', id]`.
- Após mutação, invalidar por chave; não fazer patch manual de cache em dado financeiro.
- Formulário: React Hook Form + resolver Zod. Schema Zod é a fonte de validação do cliente e do tipo do form.
- UI local: `useState` ou context pequeno. **Não** duplicar payload financeiro em store global.
- Autenticação: provider derivado de `/auth/me`, não de leitura de token.
- Job (PDF/ZIP/export): polling com backoff ou SSE, com progresso visível e estado terminal claro.

## Dinheiro, data e número

- Receber dinheiro como **string decimal** (`"1234.56"`) e formatar com `Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })`.
- Nunca `parseFloat` para depois somar ou reexibir. Nunca aritmética de centavos no cliente.
- Data operacional em `America/Sao_Paulo`; instante vem em UTC e é convertido só na exibição.
- Formatadores ficam em `shared/formatters/`, um por tipo — não repetir `toFixed(2)` solto.

## Segurança do cliente

- Refresh token em cookie HttpOnly/Secure/SameSite; access token em memória (ou cookie, conforme ADR) — nunca `localStorage`.
- CSP restritiva.
- PII e chave PIX mascaradas por permissão vinda do backend.
- Sanitizar qualquer conteúdo injetado em HTML usado para impressão/PDF.
- Não logar token nem payload sensível no console.

## UX obrigatória

- Ação financeira sempre com confirmação explícita, dizendo o valor e o efeito.
- Feedback claro em reenvio/idempotência ("este recebimento já foi registrado").
- Período fechado sinalizado na tela, com campos desabilitados e motivo.
- Recálculo mostra **diff antes** de aplicar.
- Todo estado coberto: loading, vazio, erro, sem permissão.
- Exportação assíncrona com progresso e link final.
- Acessibilidade WCAG 2.1 AA: label associado, foco visível, navegação por teclado, contraste, erro de campo anunciado, tabela com header semântico.

## Componentes

- Componente de apresentação recebe dado pronto; busca de dado mora em hook de `queries/`.
- Tabela grande: paginação por cursor do backend, não `slice` no cliente.
- Um componente por arquivo, tipos explícitos nas props, sem `any`.
- Reaproveitar `shared/components/` antes de criar variante nova.

## Testes

- Vitest + Testing Library: renderizar por papel/acessibilidade (`getByRole`, `getByLabelText`), não por classe CSS.
- Testar estado vazio, erro e desabilitado por permissão/período fechado.
- Mock no nível do client de API, não do `fetch` global.
- Playwright para os fluxos críticos: login, criar proposta, registrar recebimento, fechar período, gerar relatório.

## Checklist antes de entregar

1. Alguma conta financeira foi feita no cliente? (deve ser não)
2. Dinheiro chega como string e é só formatado?
3. Filtros estão na URL?
4. Mutação invalida as query keys certas?
5. Comando financeiro tem confirmação e `Idempotency-Key` estável no retry?
6. Loading / vazio / erro / sem-permissão existem?
7. Teclado e leitor de tela funcionam no fluxo novo?
8. Client do OpenAPI foi regenerado se o contrato mudou?
