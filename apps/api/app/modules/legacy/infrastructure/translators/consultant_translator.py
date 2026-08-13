"""ACL: `consultants` do v1 → candidato a colaborador.

Duas perdas de informação são inevitáveis aqui e ficam registradas como issue, em
vez de silenciadas:

1. **`role` é campo único.** Quem acumulava funções no v1 não tem como ser
   representado — o legado guarda uma palavra só. Traduzimos essa palavra e o
   restante fica para conferência humana (ADR-0013).
2. **Não existe início de vigência.** Usamos `created_at` do cadastro, que é a
   melhor aproximação disponível e ainda assim é uma aproximação: vigência errada
   troca o beneficiário da comissão na F4.
"""

from __future__ import annotations

from datetime import date, datetime

from app.modules.legacy.application.ports.legacy_source import LinhaLegada
from app.modules.legacy.domain.value_objects.candidato_a_colaborador import CandidatoAColaborador
from app.modules.legacy.domain.value_objects.issue import (
    CodigoDeIssue,
    Issue,
    atencao,
    bloqueio,
)
from app.modules.organization.domain.value_objects.papel_de_colaborador import PapelDeColaborador
from app.shared.domain.documento import Documento

ORIGEM = "consultants"

#: data usada quando o legado não tem `created_at` — anterior a qualquer operação
#: registrada, para não inventar vigência que começa depois da primeira proposta
INICIO_PRESUMIDO = date(2020, 1, 1)


def traduzir(linha: LinhaLegada) -> tuple[CandidatoAColaborador | None, list[Issue]]:
    problemas: list[Issue] = []
    legacy_id = (linha.get("id") or "").strip()

    if not legacy_id:
        return None, [
            bloqueio(ORIGEM, "?", CodigoDeIssue.LINHA_ILEGIVEL, "Linha sem `id` de origem.")
        ]

    nome = (linha.get("name") or "").strip()
    if not nome:
        problemas.append(
            bloqueio(ORIGEM, legacy_id, CodigoDeIssue.LINHA_ILEGIVEL, "Consultor sem nome.")
        )

    documento = _documento(linha.get("document"), legacy_id, problemas)
    papel = _papel(linha.get("role"), legacy_id, problemas)
    inicio = _inicio_de_vigencia(linha.get("created_at"), legacy_id, problemas)

    empresa = (linha.get("company") or "").strip() or None
    if empresa:
        problemas.append(
            atencao(
                ORIGEM,
                legacy_id,
                CodigoDeIssue.EMPRESA_DO_CONSULTOR_SEM_DESTINO,
                "`company` é a razão social do MEI do colaborador, não a empresa do grupo: "
                "sem destino canônico até o negócio decidir.",
                company=empresa,
            )
        )

    if documento is None or not nome:
        return None, problemas

    return (
        CandidatoAColaborador(
            legacy_id=legacy_id,
            full_name=nome,
            documento=documento,
            is_active=(linha.get("is_active") or "0").strip() == "1",
            papel=papel,
            valid_from=inicio,
            unidade=(linha.get("unidade") or "").strip().lower() or None,
            tipo_de_chave_pix=_tipo_de_pix(linha.get("pix_type")),
            chave_pix=(linha.get("pix_key") or "").strip() or None,
            empresa_do_legado=empresa,
        ),
        problemas,
    )


def _documento(bruto: str | None, legacy_id: str, problemas: list[Issue]) -> Documento | None:
    try:
        return Documento.normalizar(bruto or "")
    except ValueError as exc:
        problemas.append(
            bloqueio(
                ORIGEM,
                legacy_id,
                CodigoDeIssue.DOCUMENTO_INVALIDO,
                f"Documento do consultor não passa na validação: {exc}.",
            )
        )
        return None


def _papel(
    bruto: str | None, legacy_id: str, problemas: list[Issue]
) -> PapelDeColaborador | None:
    texto = (bruto or "").strip().upper()
    try:
        return PapelDeColaborador(texto)
    except ValueError:
        problemas.append(
            atencao(
                ORIGEM,
                legacy_id,
                CodigoDeIssue.PAPEL_DESCONHECIDO,
                "Função do legado fora do catálogo canônico; o papel precisa ser informado "
                "manualmente antes da carga.",
                role=texto or None,
            )
        )
        return None


def _inicio_de_vigencia(bruto: str | None, legacy_id: str, problemas: list[Issue]) -> date:
    problemas.append(
        atencao(
            ORIGEM,
            legacy_id,
            CodigoDeIssue.VIGENCIA_PRESUMIDA,
            "O legado não guarda início de vigência da função: derivado de `created_at`.",
        )
    )
    if not bruto:
        return INICIO_PRESUMIDO
    try:
        return datetime.fromisoformat(bruto).date()
    except ValueError:
        return INICIO_PRESUMIDO


def _tipo_de_pix(bruto: str | None) -> str | None:
    """O legado grava `Telefone`, `Email`, `Aleatoria`; o canônico usa maiúsculas."""
    texto = (bruto or "").strip().upper()
    return texto or None
