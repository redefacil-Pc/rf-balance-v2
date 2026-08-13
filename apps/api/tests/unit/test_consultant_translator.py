"""ACL de `consultants`: o que traduz, o que recusa e o que não sabe (seção 18)."""

from __future__ import annotations

from datetime import date

from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Issue, Severidade
from app.modules.legacy.infrastructure.translators import consultant_translator as tradutor
from app.modules.organization.domain.value_objects.papel_de_colaborador import PapelDeColaborador

CPF = "52998224725"


def linha(**alteracoes: str | None) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "id": "16",
        "name": "MARIA CONSULTORA",
        "document": CPF,
        "is_active": "1",
        "created_at": "2026-01-13 14:06:05",
        "pix_key": "(79) 98103-1196",
        "pix_type": "Telefone",
        "company": None,
        "role": "CONSULTOR",
        "unidade": "aracaju",
    }
    base.update(alteracoes)
    return base


def codigos(problemas: list[Issue]) -> set[str]:
    return {problema.codigo.value for problema in problemas}


def test_traduz_consultor_completo() -> None:
    candidato, _ = tradutor.traduzir(linha())

    assert candidato is not None
    assert candidato.legacy_id == "16"
    assert candidato.documento.digitos == CPF
    assert candidato.papel is PapelDeColaborador.CONSULTOR
    assert candidato.is_active
    assert candidato.unidade == "aracaju"
    assert candidato.tipo_de_chave_pix == "TELEFONE"


def test_vigencia_vem_de_created_at_e_e_sempre_sinalizada() -> None:
    candidato, problemas = tradutor.traduzir(linha())

    assert candidato is not None
    assert candidato.valid_from == date(2026, 1, 13)
    # a aproximação nunca passa silenciosa: vigência errada troca beneficiário
    assert CodigoDeIssue.VIGENCIA_PRESUMIDA.value in codigos(problemas)


def test_documento_invalido_bloqueia_a_importacao() -> None:
    candidato, problemas = tradutor.traduzir(linha(document="111.111.111-11"))

    assert candidato is None
    assert CodigoDeIssue.DOCUMENTO_INVALIDO.value in codigos(problemas)
    assert any(p.severidade is Severidade.BLOQUEIO for p in problemas)


def test_papel_fora_do_catalogo_vira_atencao_e_nao_chute() -> None:
    candidato, problemas = tradutor.traduzir(linha(role="CONSULTOR_LIDER"))

    assert candidato is not None
    # não escolhe entre CONSULTOR e LIDER: deixa vazio para alguém decidir
    assert candidato.papel is None
    assert CodigoDeIssue.PAPEL_DESCONHECIDO.value in codigos(problemas)


def test_bko_do_legado_e_papel_valido() -> None:
    candidato, _ = tradutor.traduzir(linha(role="BKO"))

    assert candidato is not None
    assert candidato.papel is PapelDeColaborador.BKO


def test_empresa_do_consultor_fica_registrada_sem_destino() -> None:
    _, problemas = tradutor.traduzir(linha(company="Alfa Negócios Ltda"))

    assert CodigoDeIssue.EMPRESA_DO_CONSULTOR_SEM_DESTINO.value in codigos(problemas)


def test_linha_sem_id_e_ilegivel() -> None:
    candidato, problemas = tradutor.traduzir(linha(id=None))

    assert candidato is None
    assert CodigoDeIssue.LINHA_ILEGIVEL.value in codigos(problemas)


def test_inativo_do_legado_chega_inativo() -> None:
    candidato, _ = tradutor.traduzir(linha(is_active="0"))

    assert candidato is not None
    assert not candidato.is_active
