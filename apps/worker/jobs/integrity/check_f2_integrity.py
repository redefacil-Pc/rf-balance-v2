"""Confere invariantes redundantes de organização, proposta e recebíveis."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.data_integrity_check_model import DataIntegrityCheckModel


async def executar(session: AsyncSession) -> dict[str, int]:
    sobreposicoes = int(
        await session.scalar(
            text(
                "SELECT COUNT(*) FROM team_assignments a "
                "JOIN team_assignments b ON a.id < b.id "
                "AND a.consultant_id = b.consultant_id "
                "AND a.assignment_type = b.assignment_type "
                "AND a.start_date <= COALESCE(b.end_date, '9999-12-31') "
                "AND b.start_date <= COALESCE(a.end_date, '9999-12-31')"
            )
        )
        or 0
    )
    divergencias = int(
        await session.scalar(
            text(
                "SELECT COUNT(*) FROM proposals p LEFT JOIN ("
                " SELECT r.proposal_id, SUM(r.amount - COALESCE(x.amount, 0)) total"
                " FROM receipts r LEFT JOIN ("
                "  SELECT receipt_id, SUM(amount) amount FROM receipt_reversals GROUP BY receipt_id"
                " ) x ON x.receipt_id = r.id"
                " WHERE r.status = 'APPROVED' GROUP BY r.proposal_id"
                ") reconhecido ON reconhecido.proposal_id = p.id "
                "WHERE p.paid_amount_cached <> COALESCE(reconhecido.total, 0)"
            )
        )
        or 0
    )
    resultados = {
        "team_assignment_overlaps": sobreposicoes,
        "proposal_receipt_cache_divergences": divergencias,
    }
    for tipo, quantidade in resultados.items():
        session.add(
            DataIntegrityCheckModel(
                check_type=tipo,
                status="PASS" if quantidade == 0 else "FAIL",
                details={"count": quantidade},
            )
        )
    await session.commit()
    return resultados
