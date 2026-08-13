# 0012 — Criptografia de PII com busca por hash determinístico

- **Status:** aceito
- **Data:** 2026-08-11
- **Decisores:** Orlean
- **Fase afetada:** F2 (colaboradores e propostas)

## Contexto

A F2 grava CPF/CNPJ de colaborador e de cliente, e chave PIX. O blueprint exige (seções 7.2, 7.4 e 13.3): documento **normalizado e único**, PIX **mascarado** para quem não tem permissão financeira, campo `customer_document_encrypted` com um `hash_for_search` ao lado, e `collaborators.document_hash` único.

Duas necessidades entram em conflito: **cifrar** o dado (para vazamento do banco não expor PII) e **buscar/deduplicar** por ele (para impedir cadastro duplicado). Cifragem com nonce aleatório produz texto diferente a cada gravação, o que impossibilita índice único.

## Decisão

Guardar **dois campos** por dado sensível:

1. **`*_encrypted`** — AES-256-GCM, nonce aleatório de 96 bits por valor, persistido como `v1:base64(nonce || ciphertext || tag)`. O prefixo de versão existe para permitir rotação de chave sem migração destrutiva.
2. **`*_hash`** — HMAC-SHA256 do valor normalizado com um *pepper* dedicado, em hex. É determinístico, então sustenta índice único e busca exata. Não guarda o valor, e o pepper impede ataque de dicionário (o espaço de CPF é pequeno o bastante para ser enumerado sem ele — hash puro de CPF **não** protege nada).

Chaves em variáveis próprias, distintas do `SECRET_KEY`: `PII_ENCRYPTION_KEY` e `PII_HASH_PEPPER`. Validação fail-fast no startup fora de `local`.

Busca por prefixo ou parcial em documento **não é suportada** — é busca exata pelo hash, ou por outro campo (nome, unidade).

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Texto puro com máscara na UI | Trivial; busca livre | Vazamento do banco expõe PII de todos; contraria 13.3 | Dado financeiro e fiscal em claro é risco desproporcional |
| Cifragem determinística (AES-SIV) | Cifra e indexa no mesmo campo | Valor igual gera texto igual, o que vaza padrão de repetição; menos revisado | O par cifrado+hash resolve o mesmo problema com primitivas mais comuns |
| Criptografia no banco (TDE) | Transparente | Protege o disco, não o acesso via aplicação ou dump autenticado | Não atende ao requisito de mascarar por permissão |
| Hash sem pepper | Simples | CPF é enumerável: 11 dígitos são quebrados por força bruta em minutos | Daria falsa sensação de proteção |

## Consequências

**Obrigatório:**

- Documento e PIX entram no domínio como value object que já normaliza; a camada de infraestrutura cifra e gera o hash.
- Toda leitura de PII passa por mascaramento, liberado somente com a permissão declarada (`collaborators:read_pii` para PIX e documento completo).
- `payload` de auditoria e log **nunca** recebe PII em claro — só o hash ou o valor mascarado.
- Ambiente não produtivo usa dado anonimizado (13.3).

**Proibido:**

- Índice, `ORDER BY` ou `LIKE` sobre campo cifrado.
- Reaproveitar `SECRET_KEY` como chave de PII: rotação de sessão e rotação de PII têm ciclos diferentes.

**Custo assumido:** perda da busca parcial por documento, e uma decifragem por registro exibido. Se a listagem de colaboradores passar do orçamento p95, a solução é não exibir documento na listagem — não afrouxar a cifragem.

**Rotação de chave:** nova chave entra como `v2`, com decifragem aceitando `v1`; um job de recifragem reescreve o acervo. Enquanto isso, os dois convivem.

## Impacto financeiro ou de dados

Nenhum cálculo é afetado. A deduplicação de colaborador e cliente passa a depender do pepper: **trocar o pepper invalida todos os hashes** e exige recomputá-los a partir dos valores decifrados. O pepper é, portanto, um segredo de retenção longa — documentar no runbook de backup.
