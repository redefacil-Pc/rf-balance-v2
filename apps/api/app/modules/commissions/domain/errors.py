from app.platform.errors.domain_error import DomainError


class CommissionRuleConfigurationError(DomainError):
    code = "invalid-commission-rule-configuration"
    title = "Configuração de comissão inválida"


class CommissionRuleConflictError(DomainError):
    status = 409
    code = "commission-rule-conflict"
    title = "Conflito na versão de comissão"


class CommissionRuleSetNotFoundError(DomainError):
    status = 404
    code = "commission-rule-set-not-found"
    title = "Versão de comissão não encontrada"
