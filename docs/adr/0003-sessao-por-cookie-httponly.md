# 0003 — Sessão por cookie HttpOnly com token opaco e rotação

- **Status:** aceito
- **Data:** 2026-08-11
- **Decisores:** Orlean
- **Fase afetada:** F1 (plataforma e identidade)

## Contexto

A API precisa autenticar um sistema financeiro interno, com requisito explícito de **revogação** de sessão (seção 13.1 do blueprint) e proteção de PII. O frontend é uma SPA servida no mesmo domínio, atrás do mesmo proxy da API.

Duas famílias de solução: token no JavaScript (bearer em memória ou `localStorage`) ou cookie `HttpOnly`.

## Decisão

Sessão em **cookie `HttpOnly`, `Secure`, `SameSite=Lax`**, contendo um **token opaco** — não um JWT. O token é gerado com `secrets.token_urlsafe(32)`, guardado no banco apenas como hash SHA-256 em `sessions`, e **rotacionado** a cada chamada de `/auth/refresh`.

Proteção CSRF por **double submit**: um segundo cookie legível (`rfb_csrf`) que o frontend reenvia no header `X-CSRF-Token`; o backend exige a igualdade em todo método não seguro.

Validação por request: consulta a `sessions`, com **cache no Redis (TTL 60s)** da resolução sessão → usuário + permissões. O banco é a fonte da verdade; o cache é reconstruível, o que respeita a regra de cache do blueprint.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Bearer em memória | Sem CSRF, simples de testar | Perde sessão a cada reload; exposto a XSS; revogação ainda exigiria estado no servidor | Sessão perdida no reload é inaceitável na operação diária; XSS em sistema que exibe PII e valor financeiro é risco desproporcional |
| JWT stateless (sem estado no servidor) | Escala sem consulta ao banco | Revogação real exige lista de bloqueio — ou seja, estado de qualquer forma; token válido após demissão do usuário até expirar | O requisito de revogação anula a vantagem principal do JWT |
| Token em `localStorage` | Trivial | Legível por qualquer script injetado | Contraria a seção 10.5 do blueprint |

## Consequências

**Obrigatório:**

- Todo `fetch` do frontend usa `credentials: 'include'`.
- Método não seguro sem `X-CSRF-Token` válido → 403.
- CORS com allowlist exata e `allow_credentials=True`; curinga é proibido.
- Logout e troca de senha revogam a sessão no banco **e** invalidam o cache.
- Rotação de token em cada refresh; token antigo usado após rotação marca a sessão como suspeita e a revoga (detecção de replay).
- `sessions` guarda apenas hash do token — vazamento do banco não permite personificar.

**Proibido:**

- Token de sessão em `localStorage`, `sessionStorage` ou variável global de JS.
- Autorização decidida no cliente.

**Custo assumido:** uma consulta a Redis (ou ao banco, no miss) por request autenticado. Revisitar se o p95 de rota autenticada passar de 500 ms por causa dessa resolução.

**Consequência de configuração:** as variáveis `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` previstas na seção 12.4 do blueprint deixam de ser necessárias e foram removidas do `.env.example`.

## Impacto financeiro ou de dados

Nenhum cálculo é afetado. A trilha de auditoria ganha precisão: cada evento passa a referenciar uma sessão identificável e revogável.
