import { Alert, Button, Divider, Grid, Group, Modal, Select, Stack, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';

import { useUpdateCollaborator } from '@/features/collaborators/mutations/useUpdateCollaborator';
import { useCollaboratorDetail } from '@/features/collaborators/queries/useCollaboratorDetail';
import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import type { Collaborator, TaxRegime } from '@/shared/types/organization';

export function CollaboratorEditModal({ collaborator, onClose }: { collaborator: Collaborator | null; onClose: () => void }) {
  const [name, setName] = useState(''); const [companyId, setCompanyId] = useState<number>(); const [unitId, setUnitId] = useState<number | null>(null); const [taxRegime, setTaxRegime] = useState<TaxRegime>('MEI');
  const [email, setEmail] = useState(''); const [phone, setPhone] = useState(''); const [keyType, setKeyType] = useState<string | null>(null); const [newKey, setNewKey] = useState('');
  const companies = useCompanies(); const units = useUnits(companyId); const detail = useCollaboratorDetail(collaborator?.id ?? null); const update = useUpdateCollaborator();
  useEffect(() => { setName(collaborator?.full_name ?? ''); setCompanyId(collaborator?.company_id); setUnitId(collaborator?.unit_id ?? null); setTaxRegime((collaborator?.tax_regime as TaxRegime) ?? 'MEI'); setNewKey(''); }, [collaborator]);
  useEffect(() => { if (detail.data) { setEmail(detail.data.email ?? ''); setPhone(detail.data.phone ?? ''); setKeyType(detail.data.payment_key_type); } }, [detail.data]);
  if (!collaborator) return null;
  return <Modal opened onClose={onClose} title={`Editar colaborador — ${collaborator.full_name}`} size="lg" centered><Stack>
    {(update.error ?? detail.error) && <Alert color="red">{(update.error ?? detail.error)?.problem.detail}</Alert>}
    <Divider label="Dados operacionais" labelPosition="left" /><Grid><Grid.Col span={{ base: 12, sm: 7 }}><TextInput label="Nome completo" withAsterisk value={name} onChange={(e) => setName(e.currentTarget.value)} /></Grid.Col><Grid.Col span={{ base: 12, sm: 5 }}><Select label="Regime" data={['MEI', 'CLT']} value={taxRegime} onChange={(v) => setTaxRegime(v as TaxRegime)} /></Grid.Col><Grid.Col span={{ base: 12, sm: 6 }}><Select label="Empresa" data={(companies.data ?? []).map((item) => ({ value: String(item.id), label: item.legal_name }))} value={companyId ? String(companyId) : null} onChange={(v) => { setCompanyId(v ? Number(v) : undefined); setUnitId(null); }} /></Grid.Col><Grid.Col span={{ base: 12, sm: 6 }}><Select label="Unidade" clearable data={(units.data ?? []).map((item) => ({ value: String(item.id), label: item.name }))} value={unitId ? String(unitId) : null} onChange={(v) => setUnitId(v ? Number(v) : null)} /></Grid.Col></Grid>
    <Divider label="Contato" labelPosition="left" /><Group grow><TextInput label="E-mail operacional" value={email} onChange={(e) => setEmail(e.currentTarget.value)} /><TextInput label="Telefone" value={phone} onChange={(e) => setPhone(e.currentTarget.value)} /></Group>
    <Divider label="Chave PIX" labelPosition="left" /><Text size="xs" c="dimmed">Chave atual: {detail.data?.payment_key_masked ?? 'não cadastrada'}. Preencha uma nova chave somente para substituí-la; a anterior será encerrada no histórico.</Text><Group grow><Select label="Tipo" clearable data={['CPF', 'CNPJ', 'EMAIL', 'TELEFONE', 'ALEATORIA']} value={keyType} onChange={setKeyType} /><TextInput label="Nova chave" value={newKey} onChange={(e) => setNewKey(e.currentTarget.value)} /></Group>
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button loading={update.isPending} disabled={!companyId || name.trim().length < 3 || (newKey.length > 0 && !keyType)} onClick={() => companyId && update.mutate({ id: collaborator.id, company_id: companyId, unit_id: unitId, full_name: name.trim(), tax_regime: taxRegime, email: email.trim() || null, phone: phone.trim() || null, payment_key: newKey && keyType ? { key_type: keyType, key: newKey.trim() } : undefined }, { onSuccess: () => { notifications.show({ color: 'positivo', title: 'Colaborador atualizado', message: name.trim() }); onClose(); } })}>Salvar alterações</Button></Group>
  </Stack></Modal>;
}
