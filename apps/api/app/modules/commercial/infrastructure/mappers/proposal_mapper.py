"""Tradução entre a linha de `proposals` e a entidade `Proposal`.

Fica aqui, e não na entidade, para que o domínio continue sem SQLAlchemy e sem
saber que documento de cliente é armazenado cifrado.
"""

from __future__ import annotations

from app.modules.commercial.domain.entities.proposal import Proposal
from app.modules.commercial.domain.value_objects.percentual_tps import PercentualTps
from app.modules.commercial.domain.value_objects.situacao_de_aprovacao import SituacaoDeAprovacao
from app.modules.commercial.domain.value_objects.status_da_proposta import StatusDaProposta
from app.modules.commercial.infrastructure.models.proposal_model import ProposalModel
from app.platform.security.pii_cipher import PiiCipher
from app.shared.domain.dinheiro import Dinheiro
from app.shared.domain.documento import Documento, TipoDeDocumento


def para_entidade(modelo: ProposalModel, cipher: PiiCipher) -> Proposal:
    digitos = cipher.decifrar(modelo.customer_document_encrypted)
    return Proposal(
        id=modelo.id,
        external_id=modelo.external_id,
        consultant_id=modelo.consultant_id,
        bko_collaborator_id=modelo.bko_collaborator_id,
        finalizer_collaborator_id=modelo.finalizer_collaborator_id,
        business_date=modelo.business_date,
        customer_name=modelo.customer_name,
        customer_document=Documento(digitos, TipoDeDocumento(modelo.customer_document_type)),
        operation_amount=Dinheiro(modelo.operation_amount),
        tps=PercentualTps(modelo.tps_percentage),
        paid_amount=Dinheiro(modelo.paid_amount_cached),
        status=StatusDaProposta(modelo.status),
        approval_status=SituacaoDeAprovacao(modelo.approval_status),
        rejection_reason=modelo.rejection_reason,
        tolerance_policy_version=modelo.tolerance_policy_version,
        version=modelo.version,
    )


def aplicar_na_linha(modelo: ProposalModel, proposta: Proposal) -> None:
    """Copia o resultado do domínio para a linha. Os campos de identidade e do
    cliente não entram: proposta não troca de dono nem de cliente — para isso
    existe cancelamento e cadastro novo."""
    modelo.operation_amount = proposta.operation_amount.valor
    modelo.tps_percentage = proposta.tps.valor
    modelo.company_commission_amount = proposta.company_commission_amount.valor
    modelo.paid_amount_cached = proposta.paid_amount.valor
    modelo.outstanding_amount_cached = proposta.outstanding_amount.valor
    modelo.status = proposta.status.value
    modelo.approval_status = proposta.approval_status.value
    modelo.rejection_reason = proposta.rejection_reason
    modelo.tolerance_policy_version = proposta.tolerance_policy_version
    modelo.bko_collaborator_id = proposta.bko_collaborator_id
    modelo.finalizer_collaborator_id = proposta.finalizer_collaborator_id
