"""Sessão viva é decisão do domínio, não da camada de API."""

from datetime import UTC, datetime, timedelta

from app.modules.identity.domain.entities.session import Session

AGORA = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def _sessao(**alteracoes: object) -> Session:
    padrao: dict[str, object] = {
        "id": 1,
        "user_id": 10,
        "token_hash": "h" * 64,
        "csrf_token": "c" * 43,
        "issued_at": AGORA,
        "expires_at": AGORA + timedelta(days=14),
        "last_used_at": AGORA,
    }
    padrao.update(alteracoes)
    return Session(**padrao)  # type: ignore[arg-type]


def test_sessao_recem_criada_esta_viva() -> None:
    assert _sessao().esta_viva(AGORA + timedelta(hours=1))


def test_sessao_expirada_nao_esta_viva() -> None:
    sessao = _sessao(expires_at=AGORA + timedelta(minutes=5))

    assert not sessao.esta_viva(AGORA + timedelta(minutes=6))


def test_sessao_revogada_nao_esta_viva_mesmo_dentro_da_validade() -> None:
    sessao = _sessao(revoked_at=AGORA, revoked_reason="logout")

    assert not sessao.esta_viva(AGORA + timedelta(minutes=1))


def test_rotacao_conta_do_ultimo_giro_e_nao_da_emissao() -> None:
    sessao = _sessao(rotated_at=AGORA + timedelta(minutes=10))

    assert not sessao.precisa_rotacionar(AGORA + timedelta(minutes=20), 900)
    assert sessao.precisa_rotacionar(AGORA + timedelta(minutes=25), 900)


def test_revogar_preserva_o_primeiro_motivo() -> None:
    sessao = _sessao()

    sessao.revogar(AGORA, "logout")
    sessao.revogar(AGORA + timedelta(minutes=1), "troca_de_senha")

    assert sessao.revoked_at == AGORA
    assert sessao.revoked_reason == "logout"
