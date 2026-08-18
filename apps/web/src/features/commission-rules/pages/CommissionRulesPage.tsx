import { Accordion, Badge, Button, Card, Group, Modal, SimpleGrid, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconCopy, IconPlayerPlay, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { CommissionRuleSetModal } from '@/features/commission-rules/components/CommissionRuleSetModal';
import { CommissionRulesCatalog } from '@/features/commission-rules/components/CommissionRulesCatalog';
import { BeneficiaryPoliciesCard } from '@/features/commission-rules/components/BeneficiaryPoliciesCard';
import { useActivateCommissionRuleSet } from '@/features/commission-rules/mutations/useCommissionRuleSets';
import { useCommissionRuleSets } from '@/features/commission-rules/queries/useCommissionRuleSets';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { decimalParaPercentual } from '@/shared/formatters/percent-mask';
import type { CommissionRuleSet } from '@/shared/types/commissions';

const STATUS = { ACTIVE: ['Ativa', 'positivo'], DRAFT: ['Rascunho', 'yellow'], RETIRED: ['Encerrada', 'gray'] } as const;

function dataBr(data: string | null): string {
  return data ? data.split('-').reverse().join('/') : 'sem término';
}

export function CommissionRulesPage() {
  const { pode } = useAuth();
  const consulta = useCommissionRuleSets();
  const ativar = useActivateCommissionRuleSet();
  const [editor, setEditor] = useState<{ opened: boolean; source: CommissionRuleSet | null }>({ opened: false, source: null });
  const [paraAtivar, setParaAtivar] = useState<CommissionRuleSet | null>(null);
  const [motivo, setMotivo] = useState('');
  const referencia = (consulta.data ?? []).find((item) => item.status === 'ACTIVE') ?? consulta.data?.[0] ?? null;

  const confirmarAtivacao = () => paraAtivar && ativar.mutate(
    { id: paraAtivar.id, reason: motivo },
    {
      onSuccess: () => {
        notifications.show({ color: 'positivo', title: 'Versão ativada', message: `A versão ${paraAtivar.version} entrará em vigor em ${dataBr(paraAtivar.valid_from)}.` });
        setParaAtivar(null); setMotivo('');
      },
      onError: (erro) => notifications.show({ color: 'red', title: erro.problem.title, message: erro.problem.detail }),
    },
  );

  return <Stack gap="lg">
    <Group justify="space-between" align="flex-start">
      <div><Title order={2} size="h3">Regras de comissão</Title><Text c="dimmed" size="sm">Versões imutáveis por vigência. Cálculos antigos mantêm a regra originalmente aplicada.</Text></div>
      {pode('commission_rules:write') && <Button leftSection={<IconPlus size={16} />} onClick={() => setEditor({ opened: true, source: referencia })}>Nova versão</Button>}
    </Group>
    <CommissionRulesCatalog />
    <BeneficiaryPoliciesCard />
    <div><Title order={3} size="h4">Consultor padrão — versões configuráveis</Title><Text size="sm" c="dimmed">Faixas TPS aplicadas à função Consultor padrão, independentemente do regime MEI ou CLT.</Text></div>
    <EstadoDaLista carregando={consulta.isPending} erro={consulta.error ?? null} vazio={(consulta.data ?? []).length === 0} mensagemVazio="Nenhuma versão configurada.">
      <Accordion variant="separated">
        {(consulta.data ?? []).map((conjunto) => {
          const [rotulo, cor] = STATUS[conjunto.status];
          return <Accordion.Item key={conjunto.id} value={String(conjunto.id)}>
            <Accordion.Control><Group justify="space-between" pr="md"><div><Text fw={600}>{conjunto.version} — {conjunto.name}</Text><Text size="xs" c="dimmed">Vigência: {dataBr(conjunto.valid_from)} até {dataBr(conjunto.valid_to)}</Text></div><Badge color={cor} variant="light">{rotulo}</Badge></Group></Accordion.Control>
            <Accordion.Panel><Stack>
              <Text size="sm"><strong>Motivo:</strong> {conjunto.reason}</Text>
              <SimpleGrid cols={{ base: 1, md: 2 }}><Card withBorder padding="sm"><Text fw={600} mb="xs">Função Consultor padrão</Text><Table striped verticalSpacing="xs"><Table.Thead><Table.Tr><Table.Th>Faixa TPS</Table.Th><Table.Th ta="right">Comissão</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{conjunto.rules.map((item) => <Table.Tr key={item.id}><Table.Td>A partir de {decimalParaPercentual(item.tps_min)}% {item.tps_max ? `e abaixo de ${decimalParaPercentual(item.tps_max)}%` : '(sem limite superior)'}</Table.Td><Table.Td ta="right">{decimalParaPercentual(item.percentage)}%</Table.Td></Table.Tr>)}</Table.Tbody></Table></Card></SimpleGrid>
              <Group justify="flex-end">
                {pode('commission_rules:write') && <Button variant="default" leftSection={<IconCopy size={15} />} onClick={() => setEditor({ opened: true, source: conjunto })}>Copiar como nova versão</Button>}
                {conjunto.status === 'DRAFT' && pode('commission_rules:activate') && <Button color="positivo" leftSection={<IconPlayerPlay size={15} />} onClick={() => setParaAtivar(conjunto)}>Ativar versão</Button>}
              </Group>
            </Stack></Accordion.Panel>
          </Accordion.Item>;
        })}
      </Accordion>
    </EstadoDaLista>
    <CommissionRuleSetModal opened={editor.opened} source={editor.source} onClose={() => setEditor({ opened: false, source: null })} />
    <Modal opened={paraAtivar !== null} onClose={() => setParaAtivar(null)} title="Ativar versão" centered><Stack><Text size="sm">A versão anterior será encerrada no dia anterior à nova vigência. Esta ação não altera cálculos históricos.</Text><TextInput label="Motivo da ativação" value={motivo} onChange={(e) => setMotivo(e.currentTarget.value)} required /><Group justify="flex-end"><Button variant="default" onClick={() => setParaAtivar(null)}>Cancelar</Button><Button color="positivo" disabled={motivo.trim().length < 3} loading={ativar.isPending} onClick={confirmarAtivacao}>Confirmar ativação</Button></Group></Stack></Modal>
  </Stack>;
}
