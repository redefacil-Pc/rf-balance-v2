import { Accordion, Badge, Divider, Group, Modal, SimpleGrid, Stack, Text } from '@mantine/core';

import { useCommissionExplanation } from '@/features/receipts/queries/useCommissionExplanation';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import { decimalParaPercentual } from '@/shared/formatters/percent-mask';

const ROTULOS: Record<string, string> = {
  STANDARD_CONSULTANT: 'Consultor padrão',
  SCALED_CONSULTANT: 'Consultor Escalonado',
  COMMERCIAL_LEADER: 'Líder comercial',
  GENERAL_MEI_LEADER: 'Líder MEI geral',
  FINALIZER: 'Finalização',
  FINALIZATION_LEADER: 'Líder de finalização',
};

const CAMPOS: Record<string, string> = {
  receipt_eligible_amount: 'Valor recebido aproveitado',
  recognized_production: 'Produção reconhecida',
  monthly_production_before: 'Produção mensal anterior',
  monthly_production_after: 'Produção mensal posterior',
  period_production_before: 'Produção semanal anterior',
  period_production_after: 'Produção semanal posterior',
  period_base_before: 'Base semanal anterior',
  period_base_after: 'Base semanal posterior',
  period_team_base_before: 'Base anterior do time',
  period_team_base_after: 'Base posterior do time',
  tps: 'TPS',
  percentage: 'Percentual aplicado',
  base_percentage: 'Percentual da base',
  commission_amount: 'Comissão calculada',
};

function valorLegivel(chave: string, valor: unknown): string | null {
  if (valor === null || valor === undefined || Array.isArray(valor) || typeof valor === 'object') {
    return null;
  }
  const texto = String(valor);
  if (chave.includes('percentage') || chave === 'tps') {
    return `${decimalParaPercentual(texto)}%`;
  }
  if (chave.includes('amount') || chave.includes('production') || chave.includes('base')) {
    return formatarMoeda(texto);
  }
  return texto;
}

interface Props {
  receiptId?: number | null;
  proposalId?: number | null;
  onClose: () => void;
}

export function CommissionExplanationModal({ receiptId = null, proposalId = null, onClose }: Props) {
  const query = useCommissionExplanation(receiptId, proposalId);
  const items = query.data?.items ?? [];
  const opened = receiptId !== null || proposalId !== null;
  const contexto = receiptId !== null ? `Recebimento #${receiptId}` : `Proposta #${proposalId}`;
  return (
    <Modal opened={opened} onClose={onClose} title="Memória de cálculo" size="xl" centered>
      <EstadoDaLista
        carregando={query.isPending}
        erro={query.error ?? null}
        vazio={items.length === 0}
        mensagemVazio="Este recebimento ainda não gerou comissão."
      >
        <Stack gap="md">
          <Group justify="space-between">
            <Text size="sm" c="dimmed">{contexto}</Text>
            <Text fw={700}>Total líquido: {formatarMoeda(query.data?.total_net_amount ?? '0.00')}</Text>
          </Group>
          <Accordion variant="separated">
            {items.map((item) => (
              <Accordion.Item key={item.id} value={String(item.id)}>
                <Accordion.Control>
                  <Group justify="space-between" pr="md">
                    <div>
                      <Text fw={600}>{ROTULOS[item.strategy] ?? item.strategy}</Text>
                      <Text size="xs" c="dimmed">{item.beneficiary_name} · regra {item.rule_version ?? '—'}</Text>
                    </div>
                    <Text fw={700}>{formatarMoeda(item.net_amount)}</Text>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
                    {[...Object.entries(item.inputs), ...Object.entries(item.outputs)].map(([chave, valor]) => {
                      const legivel = valorLegivel(chave, valor);
                      return legivel && CAMPOS[chave] ? (
                        <Group key={chave} justify="space-between" gap="md">
                          <Text size="sm" c="dimmed">{CAMPOS[chave]}</Text>
                          <Text size="sm" fw={500}>{legivel}</Text>
                        </Group>
                      ) : null;
                    })}
                  </SimpleGrid>
                  <Divider my="sm" label="Razão financeira" />
                  <Stack gap={6}>
                    {item.entries.map((entry) => (
                      <Group key={entry.id} justify="space-between">
                        <Group gap="xs">
                          <Badge color={entry.entry_type === 'CREDIT' ? 'green' : 'red'} variant="light">
                            {entry.entry_type === 'CREDIT' ? 'Crédito' : 'Débito'}
                          </Badge>
                          <Text size="sm">{entry.description}</Text>
                        </Group>
                        <Text size="sm" fw={600}>{formatarMoeda(entry.amount)}</Text>
                      </Group>
                    ))}
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        </Stack>
      </EstadoDaLista>
    </Modal>
  );
}
