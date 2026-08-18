import { Alert, Button, Divider, Grid, Group, Modal, Select, Stack, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';

import { useUpdateCollaborator } from '@/features/collaborators/mutations/useUpdateCollaborator';
import { useCollaboratorDetail } from '@/features/collaborators/queries/useCollaboratorDetail';
import { useCollaboratorFunctions } from '@/features/collaborators/queries/useCollaboratorFunctions';
import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import type { Collaborator, CollaboratorFunction, TaxRegime } from '@/shared/types/organization';

type Modalidade = 'CONSULTOR' | 'CONSULTOR_MEI_ESCALONADO';
const HOJE = dataLocalHoje();

function modalidadeAtual(collaborator: Collaborator | null): Modalidade | null {
  if (collaborator?.roles.includes('CONSULTOR_MEI_ESCALONADO')) return 'CONSULTOR_MEI_ESCALONADO';
  if (collaborator?.roles.includes('CONSULTOR')) return 'CONSULTOR';
  return null;
}

function modalidadeVigente(functions: CollaboratorFunction[]): Modalidade | null {
  const consultantFunctions = functions.filter(
    (item) => item.current && (item.role === 'CONSULTOR' || item.role === 'CONSULTOR_MEI_ESCALONADO'),
  );
  if (consultantFunctions.length !== 1) return null;
  const role = consultantFunctions[0]?.role;
  return role === 'CONSULTOR' || role === 'CONSULTOR_MEI_ESCALONADO' ? role : null;
}

export function CollaboratorEditModal({ collaborator, onClose }: { collaborator: Collaborator | null; onClose: () => void }) {
  const [name, setName] = useState('');
  const [companyId, setCompanyId] = useState<number>();
  const [unitId, setUnitId] = useState<number | null>(null);
  const [taxRegime, setTaxRegime] = useState<TaxRegime>('MEI');
  const [modality, setModality] = useState<Modalidade | null>(null);
  const [modalityValidFrom, setModalityValidFrom] = useState(HOJE);
  const [modalityReason, setModalityReason] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [keyType, setKeyType] = useState<string | null>(null);
  const [newKey, setNewKey] = useState('');
  const companies = useCompanies();
  const units = useUnits(companyId);
  const detail = useCollaboratorDetail(collaborator?.id ?? null);
  const functionHistory = useCollaboratorFunctions(collaborator?.id ?? null);
  const update = useUpdateCollaborator();
  // A consulta de funções é a fonte canônica. O resumo da tabela serve apenas
  // enquanto ela carrega e pode estar defasado após uma alteração de vigência.
  const historyModality = functionHistory.data
    ? modalidadeVigente(functionHistory.data)
    : undefined;
  const initialModality = historyModality !== undefined
    ? historyModality
    : modalidadeAtual(collaborator);
  const modalityChanged = initialModality !== null && modality !== initialModality;

  useEffect(() => {
    setName(collaborator?.full_name ?? '');
    setCompanyId(collaborator?.company_id);
    setUnitId(collaborator?.unit_id ?? null);
    setTaxRegime((collaborator?.tax_regime as TaxRegime) ?? 'MEI');
    setModality(modalidadeAtual(collaborator));
    setModalityValidFrom(HOJE);
    setModalityReason('');
    setNewKey('');
  }, [collaborator]);

  useEffect(() => {
    if (historyModality !== undefined) setModality(historyModality);
  }, [collaborator?.id, historyModality]);

  useEffect(() => {
    if (detail.data) {
      setEmail(detail.data.email ?? '');
      setPhone(detail.data.phone ?? '');
      setKeyType(detail.data.payment_key_type);
    }
  }, [detail.data]);

  if (!collaborator) return null;
  const invalidModalityChange = modalityChanged
    && (modalityValidFrom < HOJE || modalityReason.trim().length < 3);

  const save = () => {
    if (!companyId) return;
    update.mutate({
      id: collaborator.id,
      company_id: companyId,
      unit_id: unitId,
      full_name: name.trim(),
      tax_regime: taxRegime,
      email: email.trim() || null,
      phone: phone.trim() || null,
      payment_key: newKey && keyType ? { key_type: keyType, key: newKey.trim() } : undefined,
      consultant_modality: modalityChanged ? modality ?? undefined : undefined,
      modality_valid_from: modalityChanged ? modalityValidFrom : undefined,
      modality_reason: modalityChanged ? modalityReason.trim() : undefined,
    }, {
      onSuccess: () => {
        notifications.show({
          color: 'positivo',
          title: modalityChanged ? 'Cadastro e modalidade atualizados' : 'Colaborador atualizado',
          message: name.trim(),
        });
        onClose();
      },
    });
  };

  return <Modal opened onClose={onClose} title={`Editar colaborador — ${collaborator.full_name}`} size="lg" centered><Stack>
    {(update.error ?? detail.error ?? functionHistory.error) && <Alert color="red">{(update.error ?? detail.error ?? functionHistory.error)?.problem.detail}</Alert>}
    <Divider label="Dados operacionais" labelPosition="left" />
    <Grid>
      <Grid.Col span={{ base: 12, sm: 7 }}><TextInput label="Nome completo" withAsterisk value={name} onChange={(event) => setName(event.currentTarget.value)} /></Grid.Col>
      <Grid.Col span={{ base: 12, sm: 5 }}><Select label="Regime" description="Define somente o vínculo: MEI ou CLT." data={['MEI', 'CLT']} value={taxRegime} onChange={(value) => setTaxRegime(value as TaxRegime)} /></Grid.Col>
      {initialModality && <Grid.Col span={12}><Select label="Regra de comissão (função vigente)" description="A função, e não o regime, escolhe o motor de comissão." data={[
        { value: 'CONSULTOR', label: 'Consultor padrão — faixas por TPS' },
        { value: 'CONSULTOR_MEI_ESCALONADO', label: 'Consultor escalonado — produção acumulada' },
      ]} value={modality} onChange={(value) => setModality(value as Modalidade)} /></Grid.Col>}
      {functionHistory.isSuccess && !initialModality && <Grid.Col span={12}><Alert color="yellow">
        Este colaborador não possui uma função de consultor vigente. Abra primeiro “Funções” e atribua Consultor padrão ou Consultor escalonado; depois a troca ficará disponível aqui.
      </Alert></Grid.Col>}
      {modalityChanged && <>
        <Grid.Col span={{ base: 12, sm: 5 }}><TextInput label="Nova modalidade vigente a partir de" type="date" min={HOJE} withAsterisk value={modalityValidFrom} onChange={(event) => setModalityValidFrom(event.currentTarget.value)} /></Grid.Col>
        <Grid.Col span={{ base: 12, sm: 7 }}><TextInput label="Motivo da alteração" withAsterisk value={modalityReason} onChange={(event) => setModalityReason(event.currentTarget.value)} /></Grid.Col>
        <Grid.Col span={12}><Alert color="blue">A modalidade anterior será encerrada no dia precedente. Conta de acesso, vínculos de equipe e histórico serão preservados.</Alert></Grid.Col>
      </>}
      <Grid.Col span={{ base: 12, sm: 6 }}><Select label="Empresa" data={(companies.data ?? []).map((item) => ({ value: String(item.id), label: item.legal_name }))} value={companyId ? String(companyId) : null} onChange={(value) => { setCompanyId(value ? Number(value) : undefined); setUnitId(null); }} /></Grid.Col>
      <Grid.Col span={{ base: 12, sm: 6 }}><Select label="Unidade" clearable data={(units.data ?? []).map((item) => ({ value: String(item.id), label: item.name }))} value={unitId ? String(unitId) : null} onChange={(value) => setUnitId(value ? Number(value) : null)} /></Grid.Col>
    </Grid>
    <Divider label="Contato" labelPosition="left" />
    <Group grow><TextInput label="E-mail operacional" value={email} onChange={(event) => setEmail(event.currentTarget.value)} /><TextInput label="Telefone" value={phone} onChange={(event) => setPhone(event.currentTarget.value)} /></Group>
    <Divider label="Chave PIX" labelPosition="left" />
    <Text size="xs" c="dimmed">Chave atual: {detail.data?.payment_key_masked ?? 'não cadastrada'}. Preencha uma nova chave somente para substituí-la; a anterior será encerrada no histórico.</Text>
    <Group grow><Select label="Tipo" clearable data={['CPF', 'CNPJ', 'EMAIL', 'TELEFONE', 'ALEATORIA']} value={keyType} onChange={setKeyType} /><TextInput label="Nova chave" value={newKey} onChange={(event) => setNewKey(event.currentTarget.value)} /></Group>
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button loading={update.isPending} disabled={!companyId || name.trim().length < 3 || (newKey.length > 0 && !keyType) || invalidModalityChange} onClick={save}>Salvar alterações</Button></Group>
  </Stack></Modal>;
}
