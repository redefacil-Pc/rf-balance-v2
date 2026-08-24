import { Button, Group, Modal, Stack, Text, TextInput } from '@mantine/core';
import { useEffect, useState } from 'react';

import { useAdjustSettlement, usePaySettlement, type Period } from '@/features/settlements/queries/useSettlements';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import { decimalParaMoeda, mascararMoeda, moedaParaDecimal } from '@/shared/formatters/money-mask';
import type { CommissionSettlement } from '@/shared/types/commissions';

interface Props {
  settlement: CommissionSettlement | null;
  action: 'ADJUST' | 'PAY';
  period: Period;
  onClose: () => void;
}

export function SettlementActionModal({ settlement, action, period, onClose }: Props) {
  const adjust = useAdjustSettlement(period);
  const pay = usePaySettlement(period);
  const [bonus, setBonus] = useState('0,00');
  const [discount, setDiscount] = useState('0,00');
  const [deferred, setDeferred] = useState('0,00');
  const [amount, setAmount] = useState('0,00');
  const [method, setMethod] = useState('PIX');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const today = dataLocalHoje();

  useEffect(() => {
    if (!settlement) return;
    setBonus(decimalParaMoeda(settlement.bonus_amount));
    setDiscount(decimalParaMoeda(settlement.manual_discount_amount));
    setDeferred(decimalParaMoeda(settlement.deferred_amount));
    setAmount(decimalParaMoeda(settlement.payable_amount));
    setNotes(settlement.notes ?? '');
  }, [settlement]);

  const submit = async () => {
    if (!settlement) return;
    if (action === 'ADJUST') {
      await adjust.mutateAsync({ id: settlement.id, bonus_amount: moedaParaDecimal(bonus), discount_amount: moedaParaDecimal(discount), deferred_amount: moedaParaDecimal(deferred), notes });
    } else {
      await pay.mutateAsync({ id: settlement.id, amount: moedaParaDecimal(amount), payment_date: today, payment_method: method, reference });
    }
    onClose();
  };

  return <Modal opened={settlement !== null} onClose={onClose}
    title={action === 'ADJUST' ? 'Ajustar fechamento' : 'Registrar pagamento'} centered>
    <Stack>
      <Text size="sm" fw={600}>{settlement?.beneficiary_name}</Text>
      {action === 'ADJUST' ? <>
        <TextInput label="Bônus / acumulado" value={bonus} onChange={(event) => setBonus(mascararMoeda(event.currentTarget.value))} />
        <TextInput label="Desconto" value={discount} onChange={(event) => setDiscount(mascararMoeda(event.currentTarget.value))} />
        {settlement && Number(settlement.reversal_discount_amount) > 0 && <Text size="sm" c="orange">Desconto automático por estorno: {decimalParaMoeda(settlement.reversal_discount_amount)}</Text>}
        {settlement && Number(settlement.reversal_carryover_amount) > 0 && <Text size="sm" c="orange">Saldo do estorno para as próximas semanas: {decimalParaMoeda(settlement.reversal_carryover_amount)}</Text>}
        <TextInput label="Valor adiado" value={deferred} onChange={(event) => setDeferred(mascararMoeda(event.currentTarget.value))} />
        <TextInput label="Observação" value={notes} onChange={(event) => setNotes(event.currentTarget.value)} />
      </> : <>
        <TextInput label="Valor a pagar" value={amount} onChange={(event) => setAmount(mascararMoeda(event.currentTarget.value))} />
        <TextInput label="Método" value={method} onChange={(event) => setMethod(event.currentTarget.value)} />
        <TextInput label="Referência" value={reference} onChange={(event) => setReference(event.currentTarget.value)} />
      </>}
      {(adjust.error || pay.error) && <Text size="sm" c="red">{(adjust.error ?? pay.error)?.problem.detail}</Text>}
      <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button>
        <Button onClick={() => void submit()} loading={adjust.isPending || pay.isPending}>Confirmar</Button></Group>
    </Stack>
  </Modal>;
}
