# Runbook — ambiente local

Todo o desenvolvimento roda em container. Não há passo "instalar Python/Node na máquina".

## Primeira execução

```bash
cp .env.example .env
```

Ajuste o `.env` (no mínimo `SECRET_KEY`, com 32+ caracteres) e suba:

```bash
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env up -d
```

No Windows, use o atalho equivalente:

```powershell
.\scripts\rfb.ps1 up
```

Em Linux/macOS/CI o `Makefile` cobre os mesmos alvos (`make up`, `make test`, `make migrate`).

## Endereços

| Serviço | URL local |
|---|---|
| API (docs) | http://localhost:8000/docs |
| API health | http://localhost:8000/health/ready |
| Frontend (Vite) | http://localhost:5173 |
| Storage | endpoint S3/Spaces configurado em `OBJECT_STORAGE_ENDPOINT` |
| MySQL | 127.0.0.1:3307 |
| Redis | 127.0.0.1:6380 |

## Portas: por que não são as padrão

As portas do host foram escolhidas para conviver com o que já roda nesta máquina:

- **3306 é do MySQL do sistema atual (v1)** e não deve ser tocada enquanto os dois sistemas coexistirem — a v2 usa **3307**.
- **6379 / 9000 / 9001** estão ocupadas por outro projeto local (`workflow`) — a v2 usa **6380 / 9100 / 9101**.

Todas são configuráveis por `*_HOST_PORT` no `.env` e afetam **apenas** o acesso a partir do host. Entre containers valem os nomes de serviço (`db:3306` e `redis:6379`).

### MinIO opcional

O ambiente normal usa o endpoint S3/Spaces do `.env`; com DigitalOcean, MinIO
e `minio-init` não são criados. Para desenvolvimento offline ou E2E, ative o
perfil isolado, que nunca reutiliza as credenciais do Spaces:

```bash
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env --profile local-storage up -d minio minio-init
```

Nesse perfil, o console fica em http://localhost:9101. `minio-init` e
`backup-init` são tarefas de execução única e terminam corretamente como
`Exited (0)`.

## Primeiro acesso à aplicação

Depois de `up`, aplique as migrações e semeie identidade:

```powershell
.\scripts\rfb.ps1 migrate
```

```bash
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env exec -T -e SEED_ADMIN_PASSWORD=SuaSenhaLocal api python -m app.platform.db.seed
```

O seed é idempotente e **não sobrescreve senha de usuário existente**. Sem a
variável de senha, ele gera uma aleatória e a imprime uma única vez — anote na
hora.

Contas criadas por padrão, uma por perfil de acesso:

| Perfil | E-mail padrão | Variável de senha |
|---|---|---|
| Administrador | `admin@rfbalance.local` | `SEED_ADMIN_PASSWORD` |
| Financeiro | `financeiro@rfbalance.local` | `SEED_FINANCEIRO_PASSWORD` |
| Operacional | `operacional@rfbalance.local` | `SEED_OPERACIONAL_PASSWORD` |

Liderança e Consultor existem no catálogo mas **só nascem sob demanda**, quando
`SEED_LIDERANCA_PASSWORD` ou `SEED_CONSULTOR_PASSWORD` é definida. No caso do
consultor isso é proteção, não conveniência: enquanto o escopo de dados por
consultor não existir, a conta enxergaria a carteira de todos.

Acesse http://localhost:5173 e entre com essas credenciais.

### Massa de teste

Para ver as telas povoadas, com uma pessoa por perfil de acesso e por função
operacional — inclusive um BKO **sem conta**, que é o caso de quem não usa o
sistema:

```powershell
.\scripts\rfb.ps1 seed-demo
```

É idempotente pelo CPF e imprime as senhas provisórias uma única vez. Usa os
casos de uso da aplicação, não SQL: massa criada por fora aceitaria dado que o
sistema recusa, e passaria a mentir sobre o que ele permite.

## RBAC fora de sincronia

Permissões e papéis são derivados do catálogo em código
(`identity/domain/permission_catalog.py`) e reaplicados pelo `migrate`. Se o
`/health/ready` acusar o check `rbac`, o banco está atrás do código — o sintoma
seria 403 sem explicação. Para reaplicar sem tocar em usuários:

```powershell
.\scripts\rfb.ps1 sync-rbac
```

A sincronização **cria e reconcilia**, mas nunca apaga papel que sumiu do
catálogo — tirar acesso de alguém não pode ser efeito colateral de deploy. Ela
apenas reporta os obsoletos. Para removê-los de fato, quando alguém decidiu:

```powershell
.\scripts\rfb.ps1 sync-rbac-purge
```

A purga **se recusa a remover papel que ainda tenha conta vinculada** e lista
quais são. Migre essas contas para um papel do catálogo primeiro — um papel
removido debaixo de uma conta a deixaria logando e sem enxergar nada, com o
sintoma ("abriu vazio") longe da causa.

**Bloqueado por tentativas?** O limite é 5 falhas por e-mail ou IP em 15 minutos.
Em ambiente local, para liberar sem esperar:

```bash
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env exec -T db mysql -urfbalance -prfbalance rfbalance -e "DELETE FROM login_attempts WHERE succeeded = 0;"
```

## Comandos do dia a dia

| Ação | Comando |
|---|---|
| Aplicar migrações | `.\scripts\rfb.ps1 migrate` |
| Criar migração | `.\scripts\rfb.ps1 revision -Message "descricao"` |
| Testes unitários | `.\scripts\rfb.ps1 test-unit` |
| Testes de integração | `.\scripts\rfb.ps1 test-integration` |
| Lint / tipos | `.\scripts\rfb.ps1 lint` / `typecheck` |
| Testes do front | `.\scripts\rfb.ps1 web-test` |
| Logs de um serviço | `.\scripts\rfb.ps1 logs -Service api` |
| Exportar OpenAPI | `.\scripts\rfb.ps1 openapi` |

## Armadilhas conhecidas

**Mudou dependência?** `pyproject.toml` e `package.json` vivem dentro da imagem — depois de alterar, é preciso `build`:

```bash
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env build api web
```

Código-fonte (`app/`, `worker/`, `tests/`, `src/`) é bind mount com reload automático: não precisa rebuild.

**Permissão nova no catálogo não chega ao usuário até o seed rodar de novo.**
`app/modules/identity/domain/permission_catalog.py` é a fonte, mas as linhas em
`permissions` e `role_permissions` são criadas pelo seed. Depois de acrescentar
uma permissão: rode o seed (é idempotente e preserva senhas) e **refaça o
login** — a resolução de sessão é cacheada por 60s no Redis.

**Alteração em `src/` não aparece no navegador.** O bind mount do Windows não
propaga inotify para dentro do container; o Vite roda com `watch.usePolling`
justamente por isso. Se ainda assim o HMR não pegar, reinicie o serviço:
`.\scripts\rfb.ps1 restart`.

**`up` que falha no meio deixa container órfão.** Um `up` interrompido por conflito de porta pode deixar container rodando mas desanexado da rede — o sintoma é `getent hosts redis` não resolver de dentro da `api`. Solução:

```bash
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env down --remove-orphans
```

**MySQL 8.4 usa `caching_sha2_password`.** O driver precisa do pacote `cryptography` (já nas dependências). Se aparecer `RuntimeError: 'cryptography' package is required`, a imagem está desatualizada — rebuild.

**Readiness em 503.** `GET /health/ready` diz qual dependência falhou:

```bash
curl -s http://localhost:8000/health/ready
```

`migration: esperada=X aplicada=Y` significa schema fora de sincronia — rode `migrate`.

## Resetar o ambiente

```bash
docker compose -f infrastructure/compose/docker-compose.yml --env-file .env --profile local-storage down -v
```

O perfil inclui na limpeza o volume opcional do MinIO. Isso não afeta o bucket
do DigitalOcean nem o sistema atual (v1).
