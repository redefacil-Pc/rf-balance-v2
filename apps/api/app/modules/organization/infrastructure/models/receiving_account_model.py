"""Tabela `receiving_accounts` — contas que recebem o dinheiro do cliente.

Não confundir com `bank_accounts`: aquela é conta de **destino de pagamento**,
de um colaborador, unidade ou empresa, e guarda o número cifrado porque paga
comissão. Esta é o catálogo do outro lado do fluxo — em qual conta da casa o
cliente depositou — e existe para ser escolhida no lançamento do recebimento.

O rótulo é livre, como no v1 (`Almeida Serviços LTDA (SANTANDER)`), porque as
contas recebedoras não são necessariamente empresas cadastradas: há conta de
pessoa física no meio. Amarrar a `companies` exigiria cadastrar entidade que o
sistema não administra, só para poder nomear uma conta.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA, AGORA_COM_ON_UPDATE
from app.platform.db.types.utc_datetime import UtcDateTime


class ReceivingAccountModel(Base):
    __tablename__ = "receiving_accounts"
    __table_args__ = (UniqueConstraint("label", name="uq_receiving_accounts_label"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: como aparece na lista de escolha do recebimento
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    #: ordena a lista; empate desempata pelo rótulo, para a ordem ser estável
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: conta desativada some da escolha, mas continua nos recebimentos antigos
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, server_default=AGORA_COM_ON_UPDATE
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
