"""Caso de uso: rodar o importador legado.

Na F2 roda **sempre em dry-run**: lê o v1, traduz, confere e grava o relatório em
`legacy_import_runs`/`legacy_import_issues`. Nenhuma linha é escrita em
`collaborators` ou `proposals` — a carga real é da F7, depois de o relatório de
divergência ser aceito pelo negócio. Pedir escrita aqui é erro explícito, não
uma flag que alguém liga por engano.

A ordem importa: colaboradores primeiro, porque a resolução de `bko` e
`finalizacao` das propostas depende do conjunto de nomes já traduzido.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from app.modules.legacy.application.ports.legacy_source import LegacySource, LinhaLegada
from app.modules.legacy.domain.policies import deteccao_de_duplicidade as duplicidade
from app.modules.legacy.domain.policies import reconciliacao
from app.modules.legacy.domain.policies.resolucao_de_participante import IndiceDeColaboradores
from app.modules.legacy.domain.value_objects.candidato_a_colaborador import CandidatoAColaborador
from app.modules.legacy.domain.value_objects.candidato_a_proposta import CandidatoAProposta
from app.modules.legacy.domain.value_objects.issue import CodigoDeIssue, Issue, atencao, bloqueio
from app.modules.legacy.infrastructure.repositories.sql_legacy_import_repository import (
    SqlLegacyImportRepository,
)
from app.modules.legacy.infrastructure.translators import (
    consultant_translator,
    proposal_translator,
    propostas_translator,
    sales_translator,
)
from app.platform.db.session.unit_of_work import UnitOfWork
from app.platform.time.clock import Clock

#: assinatura comum dos tradutores de estrutura comercial
Tradutor = Callable[[LinhaLegada], tuple[CandidatoAProposta | None, list[Issue]]]


class CargaRealNaoImplementadaError(RuntimeError):
    """A escrita nas tabelas canônicas é entrega da F7, não uma flag da F2."""


@dataclass(frozen=True, slots=True)
class RunLegacyImport:
    dry_run: bool = True
    ator: int | None = None


@dataclass(slots=True)
class RelatorioDaImportacao:
    run_id: int
    source_label: str
    consultores_lidos: int
    colaboradores: int
    totais: list[reconciliacao.TotaisDaOrigem] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def bloqueios(self) -> int:
        return sum(1 for issue in self.issues if issue.bloqueia)

    def para_dicionario(self) -> dict[str, Any]:
        return {
            "consultores_lidos": self.consultores_lidos,
            "colaboradores_traduzidos": self.colaboradores,
            "propostas": {total.origem: total.para_dicionario() for total in self.totais},
            "issues": reconciliacao.contar_issues(self.issues),
        }


class RunLegacyImportHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        origem: LegacySource,
        execucoes: SqlLegacyImportRepository,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._origem = origem
        self._execucoes = execucoes
        self._clock = clock

    async def execute(self, cmd: RunLegacyImport) -> RelatorioDaImportacao:
        if not cmd.dry_run:
            raise CargaRealNaoImplementadaError(
                "A carga real do legado é entrega da F7. Na F2 o importador só roda em dry-run."
            )

        execucao = await self._execucoes.abrir_execucao(
            source_label=self._origem.rotulo,
            dry_run=True,
            quando=self._clock.now(),
            ator=cmd.ator,
        )

        issues: list[Issue] = []
        colaboradores, lidos_de_consultants = await self._traduzir_colaboradores(issues)
        indice = IndiceDeColaboradores(colaboradores)

        principais, total_principal = await self._traduzir_propostas(indice, issues)
        totais = [total_principal]

        paralelos: list[CandidatoAProposta] = []
        for tabela, traduzir in (
            ("propostas", propostas_translator.traduzir),
            ("sales", sales_translator.traduzir),
        ):
            candidatos, total = await self._traduzir_origem(tabela, traduzir, issues)
            paralelos.extend(candidatos)
            totais.append(total)

        issues.extend(duplicidade.detectar(principais, paralelos))

        relatorio = RelatorioDaImportacao(
            run_id=execucao.id,
            source_label=self._origem.rotulo,
            consultores_lidos=lidos_de_consultants,
            colaboradores=len(colaboradores),
            totais=totais,
            issues=issues,
        )

        await self._execucoes.registrar_issues(run_id=execucao.id, issues=issues)
        await self._execucoes.encerrar_execucao(
            execucao, summary=relatorio.para_dicionario(), quando=self._clock.now()
        )
        await self._uow.commit()

        return relatorio

    async def _traduzir_colaboradores(
        self, issues: list[Issue]
    ) -> tuple[list[CandidatoAColaborador], int]:
        linhas = await self._origem.ler("consultants")
        candidatos: list[CandidatoAColaborador] = []
        vistos: dict[str, str] = {}

        for linha in linhas:
            candidato, problemas = consultant_translator.traduzir(linha)
            issues.extend(problemas)
            if candidato is None:
                continue

            digitos = candidato.documento.digitos
            anterior = vistos.get(digitos)
            if anterior is not None:
                issues.append(
                    bloqueio(
                        consultant_translator.ORIGEM,
                        candidato.legacy_id,
                        CodigoDeIssue.DOCUMENTO_DUPLICADO,
                        f"Mesmo documento já usado pelo consultor {anterior}: a v2 exige "
                        "documento único e a duplicidade precisa ser resolvida na origem.",
                        duplicado_de=anterior,
                    )
                )
                continue

            vistos[digitos] = candidato.legacy_id
            candidatos.append(candidato)

        return candidatos, len(linhas)

    async def _traduzir_propostas(
        self, indice: IndiceDeColaboradores, issues: list[Issue]
    ) -> tuple[list[CandidatoAProposta], reconciliacao.TotaisDaOrigem]:
        linhas = await self._origem.ler("proposals")
        candidatos: list[CandidatoAProposta] = []
        redmines: dict[str, str] = {}

        for linha in linhas:
            candidato, problemas = proposal_translator.traduzir(linha)
            issues.extend(problemas)
            if candidato is None:
                continue

            if _redmine_repetido(candidato, redmines, issues):
                continue

            candidatos.append(_com_participantes(candidato, indice, issues))

        return candidatos, reconciliacao.totalizar(
            proposal_translator.ORIGEM, lidos=len(linhas), candidatos=candidatos
        )

    async def _traduzir_origem(
        self,
        tabela: str,
        traduzir: Tradutor,
        issues: list[Issue],
    ) -> tuple[list[CandidatoAProposta], reconciliacao.TotaisDaOrigem]:
        linhas = await self._origem.ler(tabela)
        candidatos: list[CandidatoAProposta] = []

        for linha in linhas:
            candidato, problemas = traduzir(linha)
            issues.extend(problemas)
            if candidato is not None:
                candidatos.append(candidato)

        return candidatos, reconciliacao.totalizar(tabela, lidos=len(linhas), candidatos=candidatos)


def _redmine_repetido(
    candidato: CandidatoAProposta, vistos: dict[str, str], issues: list[Issue]
) -> bool:
    if candidato.external_id is None:
        return False

    anterior = vistos.get(candidato.external_id)
    if anterior is not None:
        issues.append(
            bloqueio(
                candidato.origem,
                candidato.legacy_id,
                CodigoDeIssue.REDMINE_DUPLICADO,
                f"Redmine {candidato.external_id} já usado pela proposta {anterior}: "
                "`external_id` é único na v2.",
                duplicado_de=anterior,
            )
        )
        return True

    vistos[candidato.external_id] = candidato.legacy_id
    return False


def _com_participantes(
    candidato: CandidatoAProposta, indice: IndiceDeColaboradores, issues: list[Issue]
) -> CandidatoAProposta:
    """Resolve BKO e finalização por nome; sem correspondência única, fica vazio."""
    bko, motivo_do_bko = indice.resolver(candidato.bko_do_legado)
    finalizador, motivo_da_finalizacao = indice.resolver(candidato.finalizacao_do_legado)

    for campo, motivo in (("bko", motivo_do_bko), ("finalizacao", motivo_da_finalizacao)):
        if motivo is None:
            continue
        issues.append(
            atencao(
                candidato.origem,
                candidato.legacy_id,
                CodigoDeIssue.PARTICIPANTE_NAO_RESOLVIDO,
                f"`{campo}` não resolvido: {motivo} O campo fica vazio na importação.",
                campo=campo,
            )
        )

    return replace(
        candidato,
        bko_collaborator_legacy_id=bko,
        finalizer_collaborator_legacy_id=finalizador,
    )
