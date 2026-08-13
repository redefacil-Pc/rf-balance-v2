"""Resolver `bko`/`finalizacao` por nome: só quando não há dúvida (seção 18)."""

from __future__ import annotations

from datetime import date

from app.modules.legacy.domain.policies.resolucao_de_participante import (
    IndiceDeColaboradores,
    normalizar,
)
from app.modules.legacy.domain.value_objects.candidato_a_colaborador import CandidatoAColaborador
from app.shared.domain.documento import Documento

DOCUMENTOS = ("52998224725", "11144477735", "39053344705")


def colaborador(legacy_id: str, nome: str, documento: str) -> CandidatoAColaborador:
    return CandidatoAColaborador(
        legacy_id=legacy_id,
        full_name=nome,
        documento=Documento.normalizar(documento),
        is_active=True,
        papel=None,
        valid_from=date(2026, 1, 1),
        unidade=None,
        tipo_de_chave_pix=None,
        chave_pix=None,
        empresa_do_legado=None,
    )


def test_normalizacao_ignora_acento_caixa_e_espaco() -> None:
    assert normalizar(" josé  da   SILVA ") == "JOSE DA SILVA"


def test_resolve_nome_unico() -> None:
    indice = IndiceDeColaboradores([colaborador("7", "Maria Consultora", DOCUMENTOS[0])])

    encontrado, motivo = indice.resolver("MARIA CONSULTORA")

    assert encontrado == "7"
    assert motivo is None


def test_nome_com_acento_divergente_ainda_resolve() -> None:
    indice = IndiceDeColaboradores([colaborador("7", "Jucélia Barbosa", DOCUMENTOS[0])])

    encontrado, _ = indice.resolver("JUCELIA BARBOSA")

    assert encontrado == "7"


def test_homonimo_nao_resolve_e_explica() -> None:
    indice = IndiceDeColaboradores(
        [
            colaborador("7", "Maria Souza", DOCUMENTOS[0]),
            colaborador("8", "Maria Souza", DOCUMENTOS[1]),
        ]
    )

    encontrado, motivo = indice.resolver("Maria Souza")

    # atribuir comissão à pessoa errada é pagar a pessoa errada
    assert encontrado is None
    assert motivo is not None
    assert "ambíguo" in motivo


def test_nome_desconhecido_nao_resolve() -> None:
    indice = IndiceDeColaboradores([colaborador("7", "Maria Souza", DOCUMENTOS[0])])

    encontrado, motivo = indice.resolver("Fulano Que Nao Existe")

    assert encontrado is None
    assert motivo is not None


def test_campo_vazio_nao_e_problema() -> None:
    indice = IndiceDeColaboradores([])

    encontrado, motivo = indice.resolver(None)

    assert encontrado is None
    assert motivo is None
