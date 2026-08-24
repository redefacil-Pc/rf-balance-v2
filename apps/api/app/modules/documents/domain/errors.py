from app.platform.errors.domain_error import DomainError


class DocumentJobNotFoundError(DomainError):
    status = 404
    code = "document-job-not-found"
    title = "Lote de documentos não encontrado"


class DocumentNotReadyError(DomainError):
    status = 409
    code = "document-not-ready"
    title = "Documento ainda não está disponível"


class DocumentIdempotencyConflictError(DomainError):
    status = 409
    code = "document-idempotency-conflict"
    title = "Chave de idempotência em conflito"
