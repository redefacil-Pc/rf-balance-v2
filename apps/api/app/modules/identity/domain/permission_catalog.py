"""Catálogo de permissões atômicas e composição dos papéis.

Base: matriz da seção 13.2 do blueprint. **As permissões finais devem ser
confirmadas pelo negócio** — este catálogo é o ponto de partida, não a palavra
final.

Uma nova responsabilidade de acesso entra como papel composto de permissões já
existentes; uma nova função operacional, por si só, não cria papel. Só se
acrescenta permissão aqui quando surge uma capacidade realmente nova.
"""

from __future__ import annotations

from types import MappingProxyType

PERMISSOES: MappingProxyType[str, str] = MappingProxyType(
    {
        "users:read": "Consultar usuários e papéis",
        "users:write": "Criar e alterar usuários e papéis",
        "collaborators:read": "Consultar colaboradores",
        "collaborators:write": "Criar e alterar colaboradores",
        "collaborators:read_pii": "Ver documento completo e chave PIX",
        "companies:write": "Criar e alterar empresas e unidades",
        "teams:read": "Consultar vínculos consultor-líder",
        "teams:write": "Manter vínculos consultor-líder",
        "proposals:read": "Consultar propostas",
        "proposals:write": "Criar e alterar propostas",
        "proposals:read_pii": "Ver documento completo do cliente da proposta",
        "proposals:approve": "Aprovar ou devolver propostas enviadas",
        "receipts:read": "Consultar recebimentos",
        "receipts:write": "Registrar recebimentos",
        "reversals:approve": "Aprovar estornos",
        "commission_rules:read": "Consultar regras de comissão",
        "commission_rules:write": "Criar versões de regra de comissão",
        "commission_rules:activate": "Ativar versão de regra de comissão",
        "periods:read": "Consultar períodos",
        "periods:close": "Fechar período",
        "periods:reopen": "Reabrir período",
        "settlements:read": "Consultar fechamentos de comissão",
        "settlements:write": "Montar fechamentos de comissão",
        "settlements:approve": "Aprovar e pagar fechamentos",
        "adjustments:write": "Lançar ajustes manuais",
        "adjustments:approve": "Aprovar ajustes manuais",
        "reports:read": "Consultar relatórios",
        "reports:export": "Exportar relatórios e PDFs",
        "dashboard:read": "Consultar dashboard",
        "audit:read": "Consultar auditoria e histórico",
        "admin:operations": "Executar operações administrativas",
        "backups:run": "Executar backup",
    }
)

_ADMIN = tuple(PERMISSOES)

_FINANCEIRO = (
    "collaborators:read",
    "collaborators:read_pii",
    "teams:read",
    "proposals:read",
    "proposals:read_pii",
    "proposals:approve",
    "receipts:read",
    "receipts:write",
    "reversals:approve",
    "commission_rules:read",
    "periods:read",
    "periods:close",
    "settlements:read",
    "settlements:write",
    "settlements:approve",
    "adjustments:write",
    "adjustments:approve",
    "reports:read",
    "reports:export",
    "dashboard:read",
    "audit:read",
)

_OPERACIONAL = (
    "collaborators:read",
    "proposals:read",
    "proposals:write",
    "dashboard:read",
)

_LIDERANCA = (
    "collaborators:read",
    "teams:read",
    "teams:write",
    "proposals:read",
    "receipts:read",
    "reports:read",
    "reports:export",
    "dashboard:read",
)

_CONSULTOR = (
    "proposals:read",
    "reports:read",
    "dashboard:read",
)

PAPEIS: MappingProxyType[str, tuple[str, ...]] = MappingProxyType(
    {
        "ADMIN": _ADMIN,
        # Perfis de acesso representam responsabilidades no sistema, não a
        # função operacional mantida em `collaborator_roles`.
        "FINANCEIRO": _FINANCEIRO,
        # Quem sobe a proposta: cadastra, anexa o comprovante e envia para o
        # financeiro. Não aprova a própria proposta — a separação entre quem
        # cadastra e quem decide é o que dá sentido ao fluxo de aprovação.
        #
        "OPERACIONAL": _OPERACIONAL,
        # Acompanha a equipe: enxerga produção e mantém os vínculos
        # consultor-líder. Não cadastra proposta nem decide aprovação — supervisão
        # que também lança é supervisão que audita o próprio trabalho.
        "LIDERANCA": _LIDERANCA,
        # O papel mais restrito: o consultor acompanha a própria produção.
        #
        # O recorte "própria" é aplicado em SQL por `ProposalScopeResolver` —
        # participação como consultor, BKO ou finalizador. A permissão diz *se*
        # pode ler proposta; o escopo diz *quais*.
        "CONSULTOR": _CONSULTOR,
    }
)

NOMES_DOS_PAPEIS: MappingProxyType[str, str] = MappingProxyType(
    {
        "ADMIN": "Administrador",
        "FINANCEIRO": "Financeiro",
        "OPERACIONAL": "Operacional",
        "LIDERANCA": "Liderança",
        "CONSULTOR": "Consultor",
    }
)
