"""Tabela `proposal_attachments` — comprovantes de pagamento da proposta.

O arquivo mora no object storage; a linha guarda a chave, o hash e os metadados.
O `sha256` permite provar depois que o arquivo servido é o mesmo que foi enviado
— comprovante de pagamento é evidência, e evidência sem integridade não vale.

Remoção física só existe enquanto a proposta está em rascunho ou devolvida; a
partir do envio, o conjunto de anexos é o que o financeiro analisou e não muda
por baixo da decisão.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.metadata import Base
from app.platform.db.types.timestamps import AGORA
from app.platform.db.types.utc_datetime import UtcDateTime


class ProposalAttachmentModel(Base):
    __tablename__ = "proposal_attachments"
    __table_args__ = (
        # "os comprovantes desta proposta", na ordem de envio
        Index("ix_proposal_attachments_proposal_id_uploaded_at", "proposal_id", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("proposals.id", ondelete="RESTRICT"), nullable=False
    )

    #: nome original, para o operador reconhecer o arquivo
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    #: caminho no bucket — nunca derivado do nome enviado pelo usuário
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, server_default=AGORA)
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
