"""Erros de domínio do módulo de organização."""

from __future__ import annotations

from app.platform.errors.domain_error import DomainError


class DocumentoInvalidoError(DomainError):
    status = 422
    code = "documento-invalido"
    title = "Documento inválido"


class DocumentoDuplicadoError(DomainError):
    status = 409
    code = "documento-duplicado"
    title = "Documento já cadastrado"

    def __init__(self, entidade: str = "colaborador") -> None:
        # não revela de quem é o cadastro existente: pode ser de outra unidade,
        # fora do escopo de quem está consultando
        super().__init__(f"Já existe um {entidade} com este documento.")


class ColaboradorInativoError(DomainError):
    status = 409
    code = "colaborador-inativo"
    title = "Colaborador inativo"


class SituacaoColaboradorError(DomainError):
    status = 409
    code = "situacao-colaborador-invalida"
    title = "Situação do colaborador inválida"


class VigenciaSobrepostaError(DomainError):
    status = 409
    code = "vigencia-sobreposta"
    title = "Vigência sobreposta"


class PapelIncompativelError(DomainError):
    status = 422
    code = "papel-incompativel"
    title = "Papel incompatível"


class UnidadeDeOutraEmpresaError(DomainError):
    status = 422
    code = "unidade-de-outra-empresa"
    title = "Unidade não pertence à empresa"


class RecursoNaoEncontradoError(DomainError):
    status = 404
    code = "nao-encontrado"
    title = "Não encontrado"


class ContaJaVinculadaError(DomainError):
    """Uma conta de acesso pertence a um colaborador só.

    Duas pessoas compartilhando login tornariam "meus resultados" ambíguo — e é
    justamente esse recorte que decide o que cada um enxerga.
    """

    status = 409
    code = "conta-ja-vinculada"
    title = "Conta já vinculada"


class ContaInativaError(DomainError):
    status = 409
    code = "conta-inativa"
    title = "Conta inativa"


class DadosBancariosInvalidosError(DomainError):
    status = 422
    code = "dados-bancarios-invalidos"
    title = "Dados bancários inválidos"
