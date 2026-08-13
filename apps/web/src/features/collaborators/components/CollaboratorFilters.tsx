import { Button, Group, Select, TextInput } from '@mantine/core';
import { IconSearch, IconX } from '@tabler/icons-react';

import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import { PAPEIS, rotuloDoPapel } from '@/shared/types/organization';

export interface FiltrosSelecionados {
  company_id?: number;
  unit_id?: number;
  role?: string;
  tax_regime?: string;
  only_active?: boolean;
  name?: string;
}

interface Props {
  valor: FiltrosSelecionados;
  onChange: (filtros: FiltrosSelecionados) => void;
}

/** Os filtros da seção 7.2. O estado vive na URL, não aqui. */
export function CollaboratorFilters({ valor, onChange }: Props) {
  const empresas = useCompanies();
  const unidades = useUnits(valor.company_id);

  const alterar = (parcial: FiltrosSelecionados) => onChange({ ...valor, ...parcial });

  return (
    <Group align="flex-end" gap="sm" wrap="wrap">
      <TextInput
        label="Nome"
        placeholder="Começa com..."
        leftSection={<IconSearch size={16} />}
        value={valor.name ?? ''}
        onChange={(evento) => alterar({ name: evento.currentTarget.value || undefined })}
        w={220}
      />

      <Select
        label="Empresa"
        placeholder="Todas"
        clearable
        w={200}
        data={(empresas.data ?? []).map((e) => ({ value: String(e.id), label: e.legal_name }))}
        value={valor.company_id ? String(valor.company_id) : null}
        onChange={(v) =>
          alterar({ company_id: v ? Number(v) : undefined, unit_id: undefined })
        }
      />

      <Select
        label="Unidade"
        placeholder={valor.company_id ? 'Todas' : 'Selecione a empresa'}
        clearable
        disabled={!valor.company_id}
        w={180}
        data={(unidades.data ?? []).map((u) => ({ value: String(u.id), label: u.name }))}
        value={valor.unit_id ? String(valor.unit_id) : null}
        onChange={(v) => alterar({ unit_id: v ? Number(v) : undefined })}
      />

      <Select
        label="Função"
        placeholder="Todas"
        clearable
        w={200}
        data={PAPEIS.map((papel) => ({ value: papel, label: rotuloDoPapel(papel) }))}
        value={valor.role ?? null}
        onChange={(v) => alterar({ role: v ?? undefined })}
      />

      <Select
        label="Regime"
        placeholder="Todos"
        clearable
        w={120}
        data={['MEI', 'CLT']}
        value={valor.tax_regime ?? null}
        onChange={(v) => alterar({ tax_regime: v ?? undefined })}
      />

      <Select
        label="Situação"
        w={140}
        data={[
          { value: 'true', label: 'Ativos' },
          { value: 'false', label: 'Inativos' },
          { value: '', label: 'Todos' },
        ]}
        value={valor.only_active === undefined ? '' : String(valor.only_active)}
        onChange={(v) => alterar({ only_active: v === '' ? undefined : v === 'true' })}
      />

      <Button
        variant="subtle"
        leftSection={<IconX size={16} />}
        onClick={() => onChange({})}
        disabled={Object.keys(valor).length === 0}
      >
        Limpar
      </Button>
    </Group>
  );
}
