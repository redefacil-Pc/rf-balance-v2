import { ActionIcon, Alert, Button, Group, Modal, Select, Stack, Table, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { useCreateCommissionStrategyConfig } from '@/features/commission-rules/mutations/useCommissionStrategyConfigs';
import { decimalParaMoeda, mascararMoeda, moedaParaDecimal } from '@/shared/formatters/money-mask';
import { decimalParaPercentual, mascararPercentual, percentualParaDecimal } from '@/shared/formatters/percent-mask';
import type { CommissionStrategyConfig, CommissionStrategyPayload, LeaderTier } from '@/shared/types/commissions';

interface Props { opened: boolean; source: CommissionStrategyConfig | null; onClose: () => void }

function amanha(): string {
  const data = new Date(); data.setDate(data.getDate() + 1);
  return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, '0')}-${String(data.getDate()).padStart(2, '0')}`;
}
const dinheiro = (valor: unknown) => {
  const decimal = String(valor ?? '');
  return decimalParaMoeda(decimal.includes('.') ? decimal : `${decimal}.00`);
};
const percentual = (valor: unknown) => decimalParaPercentual(String(valor ?? ''));

function paraFormulario(source: CommissionStrategyConfig): CommissionStrategyPayload {
  const config = structuredClone(source.config);
  if (config.production_ranges) config.production_ranges = config.production_ranges.map((item) => ({ ...item, min: dinheiro(item.min), max: item.max === null ? null : dinheiro(item.max), percentages: item.percentages.map(percentual) }));
  if (config.tps_ranges) config.tps_ranges = config.tps_ranges.map((item) => ({ min: percentual(item.min), max: item.max === null ? null : percentual(item.max) }));
  if (config.tiers) config.tiers = config.tiers.map((item) => ({ min: dinheiro(item.min), max: dinheiro(item.max), percentage: percentual(item.percentage) }));
  for (const campo of ['mei_min_tps', 'mei_percentage', 'clt_percentage', 'base_percentage', 'excess_percentage'] as const) if (config[campo] !== undefined) config[campo] = percentual(config[campo]);
  for (const campo of ['threshold_amount', 'fixed_amount'] as const) if (config[campo] !== undefined) config[campo] = dinheiro(config[campo]);
  return config;
}

function paraApi(config: CommissionStrategyPayload): CommissionStrategyPayload {
  const result = structuredClone(config);
  if (result.production_ranges) result.production_ranges = result.production_ranges.map((item) => ({ ...item, min: moedaParaDecimal(item.min), max: item.max === null ? null : moedaParaDecimal(item.max), percentages: item.percentages.map(percentualParaDecimal) }));
  if (result.tps_ranges) result.tps_ranges = result.tps_ranges.map((item) => ({ min: percentualParaDecimal(item.min), max: item.max === null ? null : percentualParaDecimal(item.max) }));
  if (result.tiers) result.tiers = result.tiers.map((item) => ({ min: moedaParaDecimal(item.min), max: moedaParaDecimal(item.max), percentage: percentualParaDecimal(item.percentage) }));
  for (const campo of ['mei_min_tps', 'mei_percentage', 'clt_percentage', 'base_percentage', 'excess_percentage'] as const) if (result[campo] !== undefined) result[campo] = percentualParaDecimal(result[campo] ?? '');
  for (const campo of ['threshold_amount', 'fixed_amount'] as const) if (result[campo] !== undefined) result[campo] = moedaParaDecimal(result[campo] ?? '');
  return result;
}

function PercentInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <TextInput label={label} value={value} onChange={(event) => onChange(mascararPercentual(event.currentTarget.value))} rightSection="%" />;
}
function MoneyInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <TextInput label={label} value={value} onChange={(event) => onChange(mascararMoeda(event.currentTarget.value))} leftSection="R$" />;
}

export function CommissionStrategyConfigModal({ opened, source, onClose }: Props) {
  const criar = useCreateCommissionStrategyConfig();
  const [version, setVersion] = useState(''); const [name, setName] = useState('');
  const [validFrom, setValidFrom] = useState(amanha()); const [reason, setReason] = useState('');
  const [config, setConfig] = useState<CommissionStrategyPayload>({});
  useEffect(() => { if (opened && source) { setVersion(''); setName(source.name); setValidFrom(amanha()); setReason(''); setConfig(paraFormulario(source)); } }, [opened, source]);
  const set = (campo: keyof CommissionStrategyPayload, valor: unknown) => setConfig((atual) => ({ ...atual, [campo]: valor }));

  const alterarProducao = (indice: number, campo: 'min' | 'max', valor: string) => setConfig((atual) => {
    const ranges = (atual.production_ranges ?? []).map((item) => ({ ...item, percentages: [...item.percentages] }));
    ranges[indice] = { ...ranges[indice]!, [campo]: campo === 'max' && valor === '' ? null : valor };
    if (campo === 'max' && ranges[indice + 1]) ranges[indice + 1]!.min = valor;
    if (campo === 'min' && ranges[indice - 1]) ranges[indice - 1]!.max = valor;
    return { ...atual, production_ranges: ranges };
  });
  const alterarPercentualProducao = (linha: number, coluna: number, valor: string) => setConfig((atual) => {
    const ranges = (atual.production_ranges ?? []).map((item) => ({ ...item, percentages: [...item.percentages] }));
    ranges[linha]!.percentages[coluna] = valor; return { ...atual, production_ranges: ranges };
  });
  const alterarTps = (indice: number, campo: 'min' | 'max', valor: string) => setConfig((atual) => {
    const ranges = (atual.tps_ranges ?? []).map((item) => ({ ...item }));
    ranges[indice] = { ...ranges[indice]!, [campo]: campo === 'max' && valor === '' ? null : valor };
    const ordenadas = [...ranges].sort((a, b) => Number(percentualParaDecimal(a.min)) - Number(percentualParaDecimal(b.min)));
    const posicao = ordenadas.findIndex((item) => item === ranges[indice]);
    if (campo === 'max' && ordenadas[posicao + 1]) ordenadas[posicao + 1]!.min = valor;
    if (campo === 'min' && ordenadas[posicao - 1]) ordenadas[posicao - 1]!.max = valor;
    return { ...atual, tps_ranges: ranges };
  });
  const adicionarProducao = () => setConfig((atual) => {
    const ranges = (atual.production_ranges ?? []).map((item) => ({ ...item, percentages: [...item.percentages] }));
    const ultima = ranges.at(-1); if (ultima) ultima.max = '';
    ranges.push({ min: '', max: null, percentages: ['', '', '', ''] }); return { ...atual, production_ranges: ranges };
  });
  const removerProducao = (indice: number) => setConfig((atual) => {
    const ranges = (atual.production_ranges ?? []).filter((_, i) => i !== indice).map((item) => ({ ...item, percentages: [...item.percentages] }));
    if (ranges.length) { const anterior = ranges[Math.max(0, indice - 1)]; const proxima = ranges[indice]; if (anterior) anterior.max = proxima?.min ?? null; }
    return { ...atual, production_ranges: ranges };
  });
  const alterarTier = (indice: number, campo: keyof LeaderTier, valor: string) => setConfig((atual) => {
    const tiers = (atual.tiers ?? []).map((item) => ({ ...item })); tiers[indice] = { ...tiers[indice]!, [campo]: valor };
    if (campo === 'max' && tiers[indice + 1]) tiers[indice + 1]!.min = valor;
    if (campo === 'min' && tiers[indice - 1]) tiers[indice - 1]!.max = valor;
    return { ...atual, tiers };
  });
  const adicionarTier = () => setConfig((atual) => { const tiers = (atual.tiers ?? []).map((item) => ({ ...item })); const inicio = tiers.at(-1)?.max ?? ''; tiers.push({ min: inicio, max: '', percentage: '' }); return { ...atual, tiers }; });
  const removerTier = (indice: number) => setConfig((atual) => { const tiers = (atual.tiers ?? []).filter((_, i) => i !== indice).map((item) => ({ ...item })); if (tiers[indice - 1] && tiers[indice]) tiers[indice - 1]!.max = tiers[indice]!.min; return { ...atual, tiers }; });

  const salvar = () => source && criar.mutate({ strategy: source.strategy, version, name, valid_from: validFrom, reason, config: paraApi(config) }, { onSuccess: () => { notifications.show({ color: 'positivo', title: 'Rascunho criado', message: `Versão ${version} pronta para conferência e ativação.` }); onClose(); }, onError: (erro) => notifications.show({ color: 'red', title: erro.problem.title, message: erro.problem.detail }) });
  const valido = Boolean(source && version.trim() && name.trim().length >= 3 && reason.trim().length >= 3 && validFrom >= amanha());

  return <Modal opened={opened} onClose={onClose} title={`Corrigir ${source?.name ?? 'regra'} em nova versão`} size="xl" centered><Stack>
    <Alert color="blue">A versão ativa não será alterada. Esta correção será salva como rascunho com vigência futura.</Alert>
    <Group grow align="flex-start"><TextInput label="Versão" placeholder="Ex.: 2026.2" value={version} onChange={(e) => setVersion(e.currentTarget.value)} required /><TextInput label="Nome" value={name} onChange={(e) => setName(e.currentTarget.value)} required /><TextInput label="Início da vigência" type="date" min={amanha()} value={validFrom} onChange={(e) => setValidFrom(e.currentTarget.value)} required /></Group>
    <TextInput label="Motivo da correção" value={reason} onChange={(e) => setReason(e.currentTarget.value)} required />
    {source?.strategy === 'SCALED_CONSULTANT' && <Stack><Group justify="space-between"><Select label="Apuração exibida" value={config.display_mode} data={[{ value: 'WEEKLY', label: 'Semanal' }, { value: 'MONTHLY', label: 'Mensal' }]} onChange={(value) => set('display_mode', value)} /><Button variant="default" leftSection={<IconPlus size={14} />} onClick={adicionarProducao}>Adicionar faixa</Button></Group>
      <TextInput readOnly label="Colunas da matriz" value="Os quatro intervalos abaixo correspondem, na mesma ordem, às quatro colunas de percentual." />
      <Table withTableBorder><Table.Thead><Table.Tr>{(config.tps_ranges ?? []).map((_, i) => <Table.Th key={i}>Faixa TPS {i + 1}</Table.Th>)}</Table.Tr></Table.Thead><Table.Tbody><Table.Tr>{(config.tps_ranges ?? []).map((item, i) => <Table.Td key={i}><Group grow wrap="nowrap"><PercentInput label="De" value={item.min} onChange={(v) => alterarTps(i, 'min', v)} /><PercentInput label="Até" value={item.max ?? ''} onChange={(v) => alterarTps(i, 'max', v)} /></Group></Table.Td>)}</Table.Tr></Table.Tbody></Table>
      <Table withTableBorder><Table.Thead><Table.Tr><Table.Th>Produção de</Table.Th><Table.Th>Produção até</Table.Th>{(config.tps_ranges ?? []).map((item, i) => <Table.Th key={i}>TPS {item.min}%–{item.max ?? 'sem limite'}%</Table.Th>)}<Table.Th /></Table.Tr></Table.Thead><Table.Tbody>{(config.production_ranges ?? []).map((item, i) => <Table.Tr key={i}><Table.Td><MoneyInput label="" value={item.min} onChange={(v) => alterarProducao(i, 'min', v)} /></Table.Td><Table.Td><MoneyInput label="" value={item.max ?? ''} onChange={(v) => alterarProducao(i, 'max', v)} /></Table.Td>{item.percentages.map((value, j) => <Table.Td key={j}><PercentInput label="" value={value} onChange={(v) => alterarPercentualProducao(i, j, v)} /></Table.Td>)}<Table.Td><ActionIcon color="red" variant="subtle" aria-label={`Remover faixa ${i + 1}`} onClick={() => removerProducao(i)}><IconTrash size={16} /></ActionIcon></Table.Td></Table.Tr>)}</Table.Tbody></Table></Stack>}
    {source?.strategy === 'COMMERCIAL_LEADER' && <Group grow><PercentInput label="TPS mínimo do MEI" value={config.mei_min_tps ?? ''} onChange={(v) => set('mei_min_tps', v)} /><PercentInput label="Comissão MEI" value={config.mei_percentage ?? ''} onChange={(v) => set('mei_percentage', v)} /><PercentInput label="Comissão CLT" value={config.clt_percentage ?? ''} onChange={(v) => set('clt_percentage', v)} /></Group>}
    {source?.strategy === 'GENERAL_MEI_LEADER' && <Stack><Group justify="space-between"><PercentInput label="Base da produção proporcional" value={config.base_percentage ?? ''} onChange={(v) => set('base_percentage', v)} /><Button variant="default" leftSection={<IconPlus size={14} />} onClick={adicionarTier}>Adicionar faixa</Button></Group><Table withTableBorder><Table.Thead><Table.Tr><Table.Th>Produção de</Table.Th><Table.Th>Produção até</Table.Th><Table.Th>Comissão</Table.Th><Table.Th /></Table.Tr></Table.Thead><Table.Tbody>{(config.tiers ?? []).map((item, i) => <Table.Tr key={i}><Table.Td><MoneyInput label="" value={item.min} onChange={(v) => alterarTier(i, 'min', v)} /></Table.Td><Table.Td><MoneyInput label="" value={item.max} onChange={(v) => alterarTier(i, 'max', v)} /></Table.Td><Table.Td><PercentInput label="" value={item.percentage} onChange={(v) => alterarTier(i, 'percentage', v)} /></Table.Td><Table.Td><ActionIcon color="red" variant="subtle" aria-label={`Remover nível ${i + 1}`} onClick={() => removerTier(i)}><IconTrash size={16} /></ActionIcon></Table.Td></Table.Tr>)}</Table.Tbody></Table></Stack>}
    {source?.strategy === 'FINALIZER' && <Group grow><MoneyInput label="Produção mínima" value={config.threshold_amount ?? ''} onChange={(v) => set('threshold_amount', v)} /><MoneyInput label="Valor fixo" value={config.fixed_amount ?? ''} onChange={(v) => set('fixed_amount', v)} /><PercentInput label="Percentual sobre excedente" value={config.excess_percentage ?? ''} onChange={(v) => set('excess_percentage', v)} /></Group>}
    {source?.strategy === 'FINALIZATION_LEADER' && <Group grow><PercentInput label="Comissão MEI" value={config.mei_percentage ?? ''} onChange={(v) => set('mei_percentage', v)} /><PercentInput label="Comissão CLT" value={config.clt_percentage ?? ''} onChange={(v) => set('clt_percentage', v)} /></Group>}
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button disabled={!valido} loading={criar.isPending} onClick={salvar}>Criar rascunho</Button></Group>
  </Stack></Modal>;
}
