import { Card, SimpleGrid, Text } from '@mantine/core';

import { formatarMoeda } from '@/shared/formatters/currency';
import type { CommissionSettlement } from '@/shared/types/commissions';

function centavos(value: string): bigint {
  const negative = value.startsWith('-');
  const normalized = negative ? value.slice(1) : value;
  const [integer = '0', fraction = ''] = normalized.split('.');
  const result = BigInt(integer || '0') * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2));
  return negative ? -result : result;
}

function decimal(value: bigint): string {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  return `${negative ? '-' : ''}${absolute / 100n}.${(absolute % 100n).toString().padStart(2, '0')}`;
}

function sum(items: CommissionSettlement[], field: keyof CommissionSettlement): bigint {
  return items.reduce((total, item) => total + centavos(String(item[field] ?? '0')), 0n);
}

export function resumirFechamentos(items: CommissionSettlement[]) {
  const gross = sum(items, 'gross_amount');
  const carryover = sum(items, 'carryover_amount');
  const bonus = sum(items, 'bonus_amount');
  const discount = sum(items, 'discount_amount');
  const deferred = sum(items, 'deferred_amount');
  const paid = sum(items, 'paid_amount');
  const payable = sum(items, 'payable_amount');
  return {
    gross: decimal(gross),
    additions: decimal(carryover + bonus),
    deductions: decimal(discount + deferred),
    paid: decimal(paid),
    payable: decimal(payable),
  };
}

function Indicator({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <Card withBorder radius="md" padding="md">
    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{label}</Text>
    <Text size="xl" fw={700} mt={4}>{formatarMoeda(value)}</Text>
    <Text size="xs" c="dimmed" mt={2}>{detail}</Text>
  </Card>;
}

export function SettlementSummary({ items }: { items: CommissionSettlement[] }) {
  const summary = resumirFechamentos(items);
  return <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
    <Indicator label="Comissão bruta" value={summary.gross} detail="Razão automática + BKO manual" />
    <Indicator label="Acréscimos" value={summary.additions} detail="Acumulado anterior + bônus" />
    <Indicator label="Retido" value={summary.deductions} detail="Descontos + adiamentos" />
    <Indicator label="Pago" value={summary.paid} detail="Pagamentos registrados" />
    <Indicator label="A pagar" value={summary.payable} detail="Saldo líquido atual" />
  </SimpleGrid>;
}
