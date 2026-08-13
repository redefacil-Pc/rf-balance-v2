from app.platform.errors.domain_error import DomainError


class RecebimentoNaoEncontradoError(DomainError):
    status = 404
    code = "receipt-not-found"
    title = "Recebimento não encontrado"


class RecebimentoInvalidoError(DomainError):
    code = "invalid-receipt"
    title = "Recebimento inválido"


class FluxoDeRecebimentoInvalidoError(DomainError):
    status = 409
    code = "invalid-receipt-flow"
    title = "Fluxo de recebimento inválido"


class LancadorDeRecebimentoInvalidoError(DomainError):
    status = 403
    code = "receipt-launcher-not-allowed"
    title = "Lançamento não permitido"


class AutoAprovacaoDeRecebimentoError(DomainError):
    status = 403
    code = "receipt-self-approval"
    title = "Autoaprovação não permitida"


class ChaveIdempotenteEmConflitoError(DomainError):
    status = 409
    code = "idempotency-key-conflict"
    title = "Chave de idempotência em conflito"
