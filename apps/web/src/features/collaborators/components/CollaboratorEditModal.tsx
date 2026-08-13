import { Alert, Button, Group, Modal, Select, Stack, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';

import { useUpdateCollaborator } from '@/features/collaborators/mutations/useUpdateCollaborator';
import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import type { Collaborator, TaxRegime } from '@/shared/types/organization';

export function CollaboratorEditModal({ collaborator, onClose }: { collaborator: Collaborator | null; onClose: () => void }) {
  const [name, setName] = useState(''); const [companyId, setCompanyId] = useState<number>(); const [unitId, setUnitId] = useState<number | null>(null); const [taxRegime, setTaxRegime] = useState<TaxRegime>('MEI');
  const companies = useCompanies(); const units = useUnits(companyId); const update = useUpdateCollaborator();
  useEffect(() => { setName(collaborator?.full_name ?? ''); setCompanyId(collaborator?.company_id); setUnitId(collaborator?.unit_id ?? null); setTaxRegime((collaborator?.tax_regime as TaxRegime) ?? 'MEI'); }, [collaborator]);
  if (!collaborator) return null;
  return <Modal opened onClose={onClose} title={`Editar colaborador — ${collaborator.full_name}`} centered><Stack>
    {update.error && <Alert color="red" title={update.error.problem.title}>{update.error.problem.detail}</Alert>}
    <TextInput label="Nome completo" withAsterisk value={name} onChange={(e) => setName(e.currentTarget.value)} />
    <Select label="Empresa" withAsterisk data={(companies.data ?? []).map((item) => ({ value: String(item.id), label: item.legal_name }))} value={companyId ? String(companyId) : null} onChange={(value) => { setCompanyId(value ? Number(value) : undefined); setUnitId(null); }} />
    <Select label="Unidade" clearable disabled={!companyId} data={(units.data ?? []).map((item) => ({ value: String(item.id), label: item.name }))} value={unitId ? String(unitId) : null} onChange={(value) => setUnitId(value ? Number(value) : null)} />
    <Select label="Regime" withAsterisk data={['MEI', 'CLT']} value={taxRegime} onChange={(value) => setTaxRegime(value as TaxRegime)} />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button loading={update.isPending} disabled={!companyId || name.trim().length < 3} onClick={() => companyId && update.mutate({ id: collaborator.id, company_id: companyId, unit_id: unitId, full_name: name.trim(), tax_regime: taxRegime }, { onSuccess: () => { notifications.show({ color: 'positivo', title: 'Colaborador atualizado', message: name.trim() }); onClose(); } })}>Salvar</Button></Group>
  </Stack></Modal>;
}
