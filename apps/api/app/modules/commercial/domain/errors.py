"""Erros de domínio do módulo comercial.

Conflito de `version` e período fechado usam `ConcurrencyConflictError` e
`PeriodClosedError` da plataforma: são o mesmo contrato de erro em todos os
módulos, e duplicar o `code` daria dois nomes para a mesma falha na API.
"""

from __future__ import annotations

from app.platform.errors.domain_error import DomainError


class ValorDaOperacaoInvalidoError(DomainError):
    status = 422
    code = "valor-da-operacao-invalido"
    title = "Valor da operação inválido"


class TpsInvalidoError(DomainError):
    status = 422
    code = "tps-invalido"
    title = "TPS inválido"


class DocumentoDoClienteInvalidoError(DomainError):
    status = 422
    code = "documento-do-cliente-invalido"
    title = "Documento do cliente inválido"


class ExternalIdDuplicadoError(DomainError):
    status = 409
    code = "external-id-duplicado"
    title = "Redmine/ID externo já cadastrado"

    def __init__(self, external_id: str) -> None:
        super().__init__(f"Já existe uma proposta com o identificador externo {external_id}.")


class PropostaNaoEncontradaError(DomainError):
    status = 404
    code = "proposta-nao-encontrada"
    title = "Proposta não encontrada"


class PropostaCanceladaError(DomainError):
    status = 409
    code = "proposta-cancelada"
    title = "Proposta cancelada"


class PropostaComRecebimentoError(DomainError):
    status = 409
    code = "proposta-com-recebimento"
    title = "Proposta com recebimento"


class TransicaoDeStatusInvalidaError(DomainError):
    status = 409
    code = "transicao-de-status-invalida"
    title = "Transição de status inválida"


class TransicaoDeAprovacaoInvalidaError(DomainError):
    status = 409
    code = "transicao-de-aprovacao-invalida"
    title = "Transição de aprovação inválida"


class PropostaSemComprovanteError(DomainError):
    status = 422
    code = "proposta-sem-comprovante"
    title = "Proposta sem recebimento declarado"

    def __init__(self) -> None:
        super().__init__(
            "Declare ao menos um valor recebido, com seu comprovante, antes de enviar "
            "para aprovação."
        )


class PropostaEmAnaliseError(DomainError):
    status = 409
    code = "proposta-em-analise"
    title = "Proposta em análise"

    def __init__(self) -> None:
        super().__init__(
            "A proposta está aguardando decisão do financeiro e não aceita alteração. "
            "Aguarde a aprovação ou a devolução."
        )


class MotivoDeDevolucaoObrigatorioError(DomainError):
    status = 422
    code = "motivo-de-devolucao-obrigatorio"
    title = "Motivo de devolução obrigatório"


class AutoAprovacaoDePropostaError(DomainError):
    status = 409
    code = "auto-aprovacao-de-proposta"
    title = "Autoaprovação não permitida"

    def __init__(self) -> None:
        super().__init__(
            "Quem declarou um recebimento desta proposta não pode aprovar a própria proposta."
        )


class ComprovanteNaoEncontradoError(DomainError):
    status = 404
    code = "comprovante-nao-encontrado"
    title = "Comprovante não encontrado"


class ComprovanteInvalidoError(DomainError):
    status = 422
    code = "comprovante-invalido"
    title = "Comprovante inválido"


class ParticipanteInvalidoError(DomainError):
    """Consultor, BKO ou finalizador inexistente ou inativo."""

    status = 422
    code = "participante-invalido"
    title = "Participante inválido"
