"""`occurred_at` em UTC e `business_date` no fuso operacional são coisas distintas."""

from datetime import UTC, date, datetime

from app.platform.time.clock import FrozenClock


def test_business_date_usa_fuso_operacional_e_nao_utc() -> None:
    # 02:30 UTC de 12/08 é ainda 23:30 de 11/08 em São Paulo
    clock = FrozenClock(datetime(2026, 8, 12, 2, 30, tzinfo=UTC))

    assert clock.now().date() == date(2026, 8, 12)
    assert clock.business_date() == date(2026, 8, 11)


def test_now_sempre_em_utc() -> None:
    clock = FrozenClock(datetime(2026, 8, 12, 2, 30, tzinfo=UTC))

    assert clock.now().tzinfo == UTC
