# ADRs — Architecture Decision Records

Uma decisão por arquivo, numerada e imutável. Decisão revista não é editada: cria-se um ADR novo que a substitui, e o antigo passa a `status: substituído por NNNN`.

Nome: `NNNN-titulo-kebab.md`. Template: [0000-template.md](0000-template.md).

## Pendentes (seção 20 do blueprint)

| # | Decisão | Trava |
|---|---|---|
| ~~0001~~ | ~~Monólito modular versus microserviços~~ | **aceito** — [0001](0001-monolito-modular.md) |
| ~~0002~~ | ~~MySQL versus PostgreSQL~~ | **aceito** — [0002](0002-mysql-como-banco-transacional.md) |
| ~~0003~~ | ~~Cookie versus bearer token~~ | **aceito** — [0003](0003-sessao-por-cookie-httponly.md) |
| ~~0004~~ | ~~Celery versus alternativa de fila~~ | **aceito** — [0004](0004-execucao-assincrona-sem-celery.md) |
| ~~0005~~ | ~~Redis Streams/lista versus broker dedicado~~ | **aceito** — [0005](0005-redis-streams-como-transporte.md) |
| ~~0006~~ | ~~S3/MinIO e política de retenção~~ | **aceito** — [0006](0006-storage-e-retencao.md) |
| ~~0007~~ | ~~Ledger imutável e compensação~~ | **aceito** — [0007](0007-ledger-imutavel-e-compensacao.md) |
| ~~0008~~ | ~~Data usada para produção e atribuição de líder~~ | **aceito** — [0008](0008-data-de-producao-e-lideranca.md) |
| ~~0009~~ | ~~Tolerância de quitação~~ | **aceito** — [0009](0009-tolerancia-de-quitacao-versionada.md) e decisão de sobrepagamento em [0016](0016-aprovacao-estorno-lider-e-sobrepagamento.md) |
| ~~0010~~ | ~~Política de período e cutoff~~ | **aceito** — [0010](0010-periodos-e-cutoff.md) |
| ~~0011~~ | ~~Tratamento de histórico fechado~~ | **aceito** — dupla aprovação e compensação definidas em [0016](0016-aprovacao-estorno-lider-e-sobrepagamento.md) |
| ~~0012~~ | ~~Estratégia de criptografia de PII~~ | **aceito** — [0012](0012-criptografia-de-pii.md) |
| ~~0013~~ | ~~Modelo de papéis de colaborador e intervalos de vigência~~ | **aceito** — [0013](0013-papeis-de-colaborador-e-intervalos-de-vigencia.md) |
| ~~0014~~ | ~~Read models síncronos versus eventuais~~ | **aceito** — [0014](0014-read-models-sincronos.md) |
| ~~0015~~ | ~~Casing do JSON na API~~ | **aceito** — [0015](0015-casing-do-json-da-api.md) |
| ~~0016~~ | ~~Aprovação, estorno, liderança e sobrepagamento~~ | **aceito** — [0016](0016-aprovacao-estorno-lider-e-sobrepagamento.md) |

Os jobs assíncronos seguem os ADRs 0004 e 0005. A lista registra agora todas as
decisões estruturais consumidas pelas fases implementadas.
