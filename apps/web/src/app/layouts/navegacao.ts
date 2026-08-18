import {
  IconBuildingBank,
  IconBuildingStore,
  IconCashBanknote,
  IconChartBar,
  IconClipboardList,
  IconFileText,
  IconHistory,
  IconPercentage,
  IconSettings,
  IconUsers,
  IconUsersGroup,
  IconWallet,
} from '@tabler/icons-react';
import type { Icon } from '@tabler/icons-react';

/**
 * Mapa de navegação: rotas da seção 10.3 do blueprint com a permissão que cada
 * uma exige. Item sem permissão do usuário não aparece — e a rota continua
 * protegida no backend de qualquer forma.
 *
 * `fase` indica de qual fase do plano a tela depende; enquanto não chega, a
 * rota mostra um placeholder honesto em vez de dado inventado.
 */
export interface ItemDeNavegacao {
  rotulo: string;
  caminho: string;
  icone: Icon;
  permissao: string;
  fase: 'F1' | 'F2' | 'F3' | 'F4' | 'F5' | 'F6';
}

export interface GrupoDeNavegacao {
  titulo: string;
  itens: ItemDeNavegacao[];
}

export const navegacao: GrupoDeNavegacao[] = [
  {
    titulo: 'Operação',
    itens: [
      {
        rotulo: 'Dashboard',
        caminho: '/',
        icone: IconChartBar,
        permissao: 'dashboard:read',
        fase: 'F6',
      },
      {
        rotulo: 'Propostas',
        caminho: '/proposals',
        icone: IconClipboardList,
        permissao: 'proposals:read',
        fase: 'F2',
      },
      {
        rotulo: 'Aprovar propostas',
        caminho: '/proposal-approvals',
        icone: IconClipboardList,
        permissao: 'proposals:approve',
        fase: 'F2',
      },
      {
        rotulo: 'Recebimentos',
        caminho: '/receipts',
        icone: IconCashBanknote,
        permissao: 'receipts:read',
        fase: 'F3',
      },
    ],
  },
  {
    titulo: 'Cadastros',
    itens: [
      {
        rotulo: 'Colaboradores',
        caminho: '/collaborators',
        icone: IconUsers,
        permissao: 'collaborators:read',
        fase: 'F2',
      },
      {
        rotulo: 'Equipes',
        caminho: '/teams',
        icone: IconUsersGroup,
        permissao: 'teams:read',
        fase: 'F2',
      },
      {
        rotulo: 'Empresas e unidades',
        caminho: '/units',
        icone: IconBuildingStore,
        permissao: 'collaborators:read',
        fase: 'F2',
      },
      {
        rotulo: 'Contas de banco',
        caminho: '/receiving-accounts',
        icone: IconBuildingBank,
        permissao: 'receipts:read',
        fase: 'F3',
      },
    ],
  },
  {
    titulo: 'Comissionamento',
    itens: [
      {
        rotulo: 'Regras de comissão',
        caminho: '/commission-rules',
        icone: IconPercentage,
        permissao: 'commission_rules:read',
        fase: 'F4',
      },
      {
        rotulo: 'Períodos',
        caminho: '/periods',
        icone: IconHistory,
        permissao: 'periods:read',
        fase: 'F5',
      },
      {
        rotulo: 'Fechamentos',
        caminho: '/settlements',
        icone: IconWallet,
        permissao: 'settlements:read',
        fase: 'F5',
      },
    ],
  },
  {
    titulo: 'Análise',
    itens: [
      {
        rotulo: 'Relatório financeiro',
        caminho: '/reports',
        icone: IconFileText,
        permissao: 'settlements:read',
        fase: 'F5',
      },
      {
        rotulo: 'Auditoria',
        caminho: '/audit',
        icone: IconHistory,
        permissao: 'audit:read',
        fase: 'F6',
      },
    ],
  },
  {
    titulo: 'Administração',
    itens: [
      {
        rotulo: 'Usuários e acessos',
        caminho: '/admin/users',
        icone: IconSettings,
        permissao: 'users:read',
        fase: 'F1',
      },
      {
        rotulo: 'Operações',
        caminho: '/admin/operations',
        icone: IconSettings,
        permissao: 'admin:operations',
        fase: 'F6',
      },
    ],
  },
];
