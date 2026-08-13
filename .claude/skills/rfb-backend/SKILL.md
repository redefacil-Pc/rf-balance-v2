---
name: rfb-backend
description: Backend do RF Balance em Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 — criar endpoint, command/query handler, use case, controller, repositório, job de worker, idempotência, transação, autorização RBAC, tratamento de erro Problem Details e testes de API. Use para qualquer trabalho em backend/, em módulo de domínio, contrato OpenAPI, worker/fila ou geração de PDF no servidor.
---

# Backend — RF Balance

Stack: Python 3.12+, FastAPI, Pydantic v2 (`ConfigDict`), SQLAlchemy 2, Alembic, MySQL 8, Redis (fila/lock curto/cache), um worker único (Celery **ou** Dramatiq **ou** RQ — decidido por ADR), Jinja2 + WeasyPrint para PDF oficial.

Fronteiras de módulo e camadas: ver skill `rfb-arquitetura`. Schema e migração: ver `rfb-database`.

## Estrutura

```text
backend/
|-- app/
|   |-- modules/
|   |   |-- identity/  organization/  teams/  commercial/  receivables/
|   |   |-- commissions/  settlements/  periods/  reporting/  documents/  audit/
|   |-- platform/         # config, db, bus, observability
|   `-- main.py
|-- migrations/
|-- tests/
|   |-- unit/  integration/  contract/  e2e/
`-- pyproject.toml
```

Cada módulo: `domain/`, `application/`, `infrastructure/`, `api/`.

## Controller: cinco passos e nada mais

```python
@router.post("/proposals/{proposal_id}/receipts", status_code=201)
async def register_receipt(
    proposal_id: int,
    body: RegisterReceiptRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    actor: Annotated[Actor, Depends(require_permission("receipts:write"))],
    handler: Annotated[RegisterReceiptHandler, Depends(get_register_receipt_handler)],
) -> ReceiptResponse:
    result = await handler.execute(
        RegisterReceipt(
            proposal_id=proposal_id,
            amount=body.amount,
            business_date=body.business_date,
            actor_id=actor.id,
            idempotency_key=idempotency_key,
        )
    )
    return ReceiptResponse.from_result(result)
```

Controller **não** faz query no ORM, não calcula comissão, não abre transação, não formata dinheiro. Se um controller tem mais de ~15 linhas de lógica, a regra vazou da `application/`.

## Use case / handler

- Um command = uma classe imutável (dataclass frozen ou modelo Pydantic) + um handler com `execute`.
- O handler abre a Unit of Work, chama domínio, persiste, grava auditoria e outbox, commita uma vez.
- Nunca dois commits no mesmo handler. Nunca commit em repositório.
- Queries são handlers separados, sem transação de escrita, podendo ler projeção de `reporting`.

```python
class RegisterReceiptHandler:
    def __init__(self, uow: UnitOfWork, engine: CommissionEngine, clock: Clock): ...

    async def execute(self, cmd: RegisterReceipt) -> ReceiptResult:
        async with self.uow:
            if prior := await self.uow.idempotency.find(cmd.idempotency_key):
                return prior.result                      # replay, não duplica
            period = await self.uow.periods.active_for(cmd.business_date)
            period.assert_open()                         # 409 period-closed
            proposal = await self.uow.proposals.get_for_update(cmd.proposal_id)
            receipt = proposal.register_receipt(cmd.amount, cmd.business_date, self.clock.now())
            entries = self.engine.derive(proposal, receipt)   # snapshot incluso
            self.uow.commissions.add_all(entries)
            self.uow.audit.record("receipt.registered", actor=cmd.actor_id, payload=...)
            self.uow.outbox.publish(ReceiptRegistered(...))
            await self.uow.idempotency.store(cmd.idempotency_key, receipt.id)
            await self.uow.commit()
        return ReceiptResult(...)
```

## Idempotência e concorrência

- Todo comando financeiro exige header `Idempotency-Key`; chave repetida retorna o **mesmo** resultado, não erro e não duplicata.
- Chave única em `idempotency_keys` — a garantia é do banco, não do `if`.
- Escrita em aggregate usa `SELECT ... FOR UPDATE` ou versão otimista (`ETag`/`version`); conflito → 409.
- Lock Redis só para serializar job, nunca como substituto de constraint.

## Contratos de API

- Prefixo `/api/v1`.
- Casing do JSON: um único padrão no projeto inteiro (definido por ADR) — não misturar.
- Datas `YYYY-MM-DD`; instantes ISO 8601 UTC.
- **Dinheiro como string decimal** em API crítica: `"1234.56"`. Não serializar `float`.
- Listas grandes: paginação por cursor.
- `X-Correlation-ID` em request e response, propagado para log e worker.
- Erro em `application/problem+json`:

```json
{
  "type": "https://rfbalance/errors/period-closed",
  "title": "Período fechado",
  "status": 409,
  "detail": "A proposta pertence a um período já fechado.",
  "instance": "/api/v1/proposals/123",
  "correlation_id": "01J...",
  "errors": []
}
```

- Mudança aditiva fica em v1; remoção ou mudança de semântica exige v2 ou janela de depreciação.
- OpenAPI é gerado e validado no CI; o client TypeScript do frontend sai dele.

## Autorização

- Autorização é sempre no backend, por permissão atômica (`receipts:write`, `settlements:approve`, `audit:read`), via dependência do FastAPI.
- Escopo de dados (unidade, equipe, próprio colaborador) entra como Specification aplicada na query — nunca filtrado no cliente.
- PII e chave PIX mascaradas por permissão na camada de resposta.

## Pydantic v2

- `model_config = ConfigDict(frozen=True, extra="forbid")` em DTO de entrada.
- `Decimal` para dinheiro, com `max_digits`/`decimal_places` coerentes com a coluna.
- DTO de resposta não é entidade de domínio nem model do ORM; converter explicitamente.

## Jobs / worker

Assíncrono por natureza: PDF/ZIP em lote, XLSX grande, recálculo massivo, reconciliação de read model, backup, verificação de integridade.

- Job é **idempotente e retomável**; retry não pode duplicar lançamento.
- Estado visível em `document_jobs` (ou equivalente), consultável pelo frontend por polling com backoff ou SSE.
- Worker roda sem scheduler embutido na API; a API não faz trabalho longo em request.
- Payload de job carrega ids e correlation id, não objetos de domínio serializados.

## Observabilidade

Log estruturado JSON com `correlation_id`, ator, módulo, ação e duração — sem token, PII crua ou payload financeiro completo. `/health/live` e `/health/ready` (banco, migração esperada, Redis, storage).

## Testes

- `unit/`: domínio e strategies de comissão, sem I/O. Cobrir faixas, bordas e arredondamento.
- `integration/`: handler + MySQL/Redis efêmeros; testar transação, rollback e idempotência (executar o mesmo comando duas vezes).
- `contract/`: schema OpenAPI vs consumidores.
- `e2e/`: fluxo proposta → recebimento → comissão → fechamento → PDF.

## Checklist antes de entregar

1. Controller só orquestra? `domain/` sem framework?
2. Um único commit por comando, com auditoria e outbox dentro dele?
3. Comando financeiro tem `Idempotency-Key` e teste de replay?
4. Período fechado é bloqueado no domínio?
5. Dinheiro em `Decimal` no cálculo e string na API?
6. Permissão verificada no backend e escopo aplicado em SQL?
7. Erro segue Problem Details com `correlation_id`?
8. OpenAPI atualizado e client regenerado?
