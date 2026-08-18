import { ActionIcon, Alert, Button, Divider, Group, Modal, Stack, Table, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { useCreateCommissionRuleSet } from '@/features/commission-rules/mutations/useCommissionRuleSets';
import { decimalParaPercentual, mascararPercentual, percentualParaDecimal } from '@/shared/formatters/percent-mask';
import type { CommissionBandInput, CommissionRuleSet, TaxRegime } from '@/shared/types/commissions';

interface Props {
  opened: boolean;
  onClose: () => void;
  source: CommissionRuleSet | null;
}

const DEFAULTS: CommissionBandInput[] = ([
  { tax_regime: 'MEI', tps_min: '0', tps_max: '25', percentage: '6' },
  { tax_regime: 'MEI', tps_min: '25', tps_max: '30', percentage: '8' },
  { tax_regime: 'MEI', tps_min: '30', tps_max: '35', percentage: '10' },
  { tax_regime: 'MEI', tps_min: '35', tps_max: null, percentage: '12' },
] as CommissionBandInput[]);

function amanha(): string {
  const data = new Date();
  data.setDate(data.getDate() + 1);
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, '0');
  const dia = String(data.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
}

function validarFaixas(rules: CommissionBandInput[]): string | null {
  const numero = (valor: string): number => Number(percentualParaDecimal(valor));
  for (const regime of ['MEI'] as const) {
    const faixas = rules.filter((item) => item.tax_regime === regime);
    if (faixas.length === 0 || numero(faixas[0]?.tps_min ?? '') !== 0) {
      return `As faixas de ${regime} devem começar em TPS zero.`;
    }
    for (let indice = 0; indice < faixas.length; indice += 1) {
      const faixa = faixas[indice];
      if (!faixa || faixa.tps_min === '' || faixa.percentage === '') return `Preencha todas as faixas de ${regime}.`;
      const minimo = numero(faixa.tps_min); const percentual = numero(faixa.percentage);
      if (!Number.isFinite(minimo) || minimo < 0 || minimo > 100 || !Number.isFinite(percentual) || percentual < 0 || percentual > 100) return `TPS e percentual de ${regime} devem estar entre 0 e 100.`;
      const ultima = indice === faixas.length - 1;
      if (ultima && faixa.tps_max !== null) return `A última faixa de ${regime} deve ficar sem TPS máximo.`;
      if (!ultima) {
        const proxima = faixas[indice + 1];
        if (faixa.tps_max === null || !proxima || numero(faixa.tps_max) !== numero(proxima.tps_min)) return `Há lacuna ou sobreposição entre as faixas ${indice + 1} e ${indice + 2} de ${regime}.`;
      }
    }
  }
  return null;
}

export function CommissionRuleSetModal({ opened, onClose, source }: Props) {
  const criar = useCreateCommissionRuleSet();
  const [version, setVersion] = useState('');
  const [name, setName] = useState('Tabela padrão de consultores');
  const [validFrom, setValidFrom] = useState(amanha());
  const [reason, setReason] = useState('');
  const [rules, setRules] = useState<CommissionBandInput[]>(DEFAULTS);

  useEffect(() => {
    if (!opened) return;
    setVersion('');
    setName(source?.name ?? 'Tabela padrão de consultores');
    setValidFrom(amanha());
    setReason('');
    setRules(source ? source.rules.map(({ tax_regime, tps_min, tps_max, percentage }) => ({
      tax_regime,
      tps_min: decimalParaPercentual(tps_min),
      tps_max: tps_max === null ? null : decimalParaPercentual(tps_max),
      percentage: decimalParaPercentual(percentage),
    })) : DEFAULTS);
  }, [opened, source]);

  const alterar = (regime: TaxRegime, indice: number, campo: 'tps_min' | 'tps_max' | 'percentage', valor: string) => {
    setRules((atuais) => {
      const posicoes = atuais.map((item, posicao) => item.tax_regime === regime ? posicao : -1).filter((posicao) => posicao >= 0);
      const alvo = posicoes[indice];
      if (alvo === undefined) return atuais;
      const proximas = atuais.map((item) => ({ ...item }));
      proximas[alvo] = { ...proximas[alvo]!, [campo]: campo === 'tps_max' && valor === '' ? null : valor };
      if (campo === 'tps_max' && posicoes[indice + 1] !== undefined) proximas[posicoes[indice + 1]!]!.tps_min = valor;
      if (campo === 'tps_min' && posicoes[indice - 1] !== undefined) proximas[posicoes[indice - 1]!]!.tps_max = valor;
      return proximas;
    });
  };

  const remover = (regime: TaxRegime, indice: number) => setRules((atuais) => {
    const doRegime = atuais.filter((item) => item.tax_regime === regime);
    const restantes = doRegime.filter((_, posicao) => posicao !== indice).map((item) => ({ ...item }));
    if (restantes.length > 0) {
      const anterior = restantes[Math.max(0, indice - 1)];
      const proxima = restantes[indice];
      if (anterior) anterior.tps_max = proxima?.tps_min ?? null;
    }
    return atuais.filter((item) => item.tax_regime !== regime).concat(restantes);
  });

  const adicionar = (regime: TaxRegime) => setRules((atuais) => {
    const proximas = atuais.map((item) => ({ ...item }));
    const ultima = [...proximas].reverse().find((item) => item.tax_regime === regime);
    if (ultima) ultima.tps_max = '';
    proximas.push({ tax_regime: regime, tps_min: '', tps_max: null, percentage: '' });
    return proximas;
  });

  const salvar = () => criar.mutate(
    {
      version,
      name,
      valid_from: validFrom,
      reason,
      rules: rules.map((item) => ({
        ...item,
        tps_min: percentualParaDecimal(item.tps_min),
        tps_max: item.tps_max === null ? null : percentualParaDecimal(item.tps_max),
        percentage: percentualParaDecimal(item.percentage),
      })),
    },
    {
      onSuccess: () => {
        notifications.show({ color: 'positivo', title: 'Rascunho criado', message: `Versão ${version} pronta para conferência.` });
        onClose();
      },
      onError: (erro) => notifications.show({ color: 'red', title: erro.problem.title, message: erro.problem.detail }),
    },
  );

  const erroDasFaixas = validarFaixas(rules);
  const valido = Boolean(version.trim() && name.trim().length >= 3 && validFrom >= amanha() && reason.trim().length >= 3 && !erroDasFaixas);

  return <Modal opened={opened} onClose={onClose} title="Nova versão das regras" size="xl" centered>
    <Stack>
      <Group grow align="flex-start">
        <TextInput label="Versão" placeholder="Ex.: 2026.2" value={version} onChange={(e) => setVersion(e.currentTarget.value)} required />
        <TextInput label="Nome" value={name} onChange={(e) => setName(e.currentTarget.value)} required />
        <TextInput label="Início da vigência" type="date" min={amanha()} value={validFrom} onChange={(e) => setValidFrom(e.currentTarget.value)} required />
      </Group>
      <TextInput label="Motivo da nova versão" value={reason} onChange={(e) => setReason(e.currentTarget.value)} required />
      {(['MEI'] as const).map((regime) => {
        const faixas = rules.filter((item) => item.tax_regime === regime);
        return <Stack key={regime} gap="xs">
          <Group justify="space-between"><Text fw={600}>Função Consultor padrão</Text><Button size="xs" variant="default" leftSection={<IconPlus size={14} />} onClick={() => adicionar(regime)}>Adicionar faixa</Button></Group>
          <Table withTableBorder verticalSpacing="xs"><Table.Thead><Table.Tr><Table.Th>De (%)</Table.Th><Table.Th>Até (%)</Table.Th><Table.Th>Comissão (%)</Table.Th><Table.Th w={50} /></Table.Tr></Table.Thead><Table.Tbody>
            {faixas.map((item, indice) => <Table.Tr key={`${regime}-${indice}`}>
              <Table.Td><TextInput aria-label={`TPS mínimo ${regime} ${indice + 1}`} value={item.tps_min} onChange={(e) => alterar(regime, indice, 'tps_min', mascararPercentual(e.currentTarget.value))} rightSection="%" /></Table.Td>
              <Table.Td><TextInput aria-label={`TPS máximo ${regime} ${indice + 1}`} placeholder={indice === faixas.length - 1 ? 'Sem limite' : undefined} value={item.tps_max ?? ''} onChange={(e) => alterar(regime, indice, 'tps_max', mascararPercentual(e.currentTarget.value))} rightSection="%" /></Table.Td>
              <Table.Td><TextInput aria-label={`Percentual ${regime} ${indice + 1}`} value={item.percentage} onChange={(e) => alterar(regime, indice, 'percentage', mascararPercentual(e.currentTarget.value))} rightSection="%" /></Table.Td>
              <Table.Td><ActionIcon color="red" variant="subtle" aria-label={`Remover faixa ${indice + 1} de ${regime}`} onClick={() => remover(regime, indice)}><IconTrash size={16} /></ActionIcon></Table.Td>
            </Table.Tr>)}
          </Table.Tbody></Table>
          <Divider />
        </Stack>;
      })}
      {erroDasFaixas ? <Alert color="red" title="Revise as faixas">{erroDasFaixas}</Alert> : <Text size="xs" c="dimmed">Faixas contínuas e completas para a função Consultor padrão.</Text>}
      <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button disabled={!valido} loading={criar.isPending} onClick={salvar}>Criar rascunho</Button></Group>
    </Stack>
  </Modal>;
}
