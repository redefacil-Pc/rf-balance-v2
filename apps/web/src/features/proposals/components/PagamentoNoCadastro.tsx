import { Alert, Button, FileButton, Group, Select, Stack, Text, TextInput } from '@mantine/core';
import { IconPaperclip } from '@tabler/icons-react';
import { useCallback, useState } from 'react';

import type { InitialReceiptInput } from '@/features/proposals/mutations/useCreateProposal';
import { useReceivingAccounts } from '@/features/receiving-accounts/queries/useReceivingAccounts';
import { mascararMoeda, moedaParaDecimal } from '@/shared/formatters/money-mask';

export function obterDataHoraEmSaoPaulo(agora = new Date()) {
  return {
    data: agora.toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' }),
    hora: agora.toLocaleTimeString('pt-BR', {
      timeZone: 'America/Sao_Paulo',
      hour: '2-digit',
      minute: '2-digit',
    }),
  };
}

/**
 * O pagamento declarado junto do cadastro da proposta.
 *
 * Bloco **opcional**, como o "Valor Pago (Opcional)" do v1: em branco, a
 * proposta nasce aberta e o valor entra depois. Preenchido, vira tudo-ou-nada —
 * valor sem comprovante, sem forma ou sem conta é meio registro, e meio
 * comprovante é pior que nenhum, porque parece completo na listagem.
 */
export function usePagamentoNoCadastro(habilitado = true) {
  const contas = useReceivingAccounts(true, habilitado);
  const [instanteInicial] = useState(obterDataHoraEmSaoPaulo);
  const [valor, setValor] = useState('');
  const [data, setData] = useState(instanteInicial.data);
  const [dataMaxima, setDataMaxima] = useState(instanteInicial.data);
  const [hora, setHora] = useState(instanteInicial.hora);
  const [forma, setForma] = useState<string | null>('PIX');
  const [conta, setConta] = useState<string | null>(null);
  const [comprovante, setComprovante] = useState<File | null>(null);
  // gerada uma vez por tentativa, não dentro da mutation: em retry, uma chave
  // nova duplicaria o lançamento em vez de ser reconhecida como repetição
  const [chave, setChave] = useState(() => crypto.randomUUID());

  const decimal = moedaParaDecimal(valor);
  const preenchido = decimal !== '' && Number(decimal) > 0;
  const completo = preenchido && Boolean(forma) && Boolean(conta) && comprovante !== null;
  const receipt: InitialReceiptInput | null = completo
    ? {
        amount: decimal,
        businessDate: data,
        paymentTime: hora,
        paymentMethod: forma as string,
        receivingAccountId: Number(conta),
        proof: comprovante as File,
        idempotencyKey: chave,
      }
    : null;

  const limpar = useCallback(() => {
    const atual = obterDataHoraEmSaoPaulo();
    setValor('');
    setData(atual.data);
    setDataMaxima(atual.data);
    setHora(atual.hora);
    setForma('PIX');
    setConta(null);
    setComprovante(null);
    setChave(crypto.randomUUID());
  }, []);

  return {
    campos: {
      valor,
      setValor,
      data,
      setData,
      dataMaxima,
      hora,
      setHora,
      forma,
      setForma,
      conta,
      setConta,
      comprovante,
      setComprovante,
      contas,
    },
    preenchido,
    completo,
    receipt,
    limpar,
  };
}

type Pagamento = ReturnType<typeof usePagamentoNoCadastro>;

export function PagamentoNoCadastro({ pagamento }: { pagamento: Pagamento }) {
  const { campos, preenchido, completo } = pagamento;
  const semContas = campos.contas.data?.length === 0;

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Pagamento
      </Text>
      <Text size="xs" c="dimmed">
        Opcional. Em branco, a proposta fica aberta e o valor é declarado depois. Preenchido, o
        comprovante, a forma de pagamento e a conta passam a ser obrigatórios.
      </Text>

      <Group grow align="flex-start">
        <TextInput
          label="Valor pago"
          placeholder="0,00"
          inputMode="decimal"
          leftSection="R$"
          value={campos.valor}
          onChange={(evento) => campos.setValor(mascararMoeda(evento.currentTarget.value))}
        />
        <TextInput
          label="Data do pagamento"
          type="date"
          max={campos.dataMaxima}
          disabled={!preenchido}
          value={campos.data}
          onChange={(evento) => campos.setData(evento.currentTarget.value)}
        />
        <TextInput
          label="Hora efetiva"
          type="time"
          disabled={!preenchido}
          value={campos.hora}
          onChange={(evento) => campos.setHora(evento.currentTarget.value)}
        />
      </Group>

      <Group grow align="flex-start">
        <Select
          label="Forma de pagamento"
          withAsterisk={preenchido}
          disabled={!preenchido}
          value={campos.forma}
          onChange={campos.setForma}
          data={['PIX', 'TED', 'BOLETO', 'DINHEIRO', 'OUTRO']}
        />
        <Select
          label="Conta que recebeu"
          withAsterisk={preenchido}
          searchable
          placeholder={semContas ? 'Cadastre uma conta em Contas de banco' : 'Selecione'}
          disabled={!preenchido || campos.contas.isPending || semContas}
          value={campos.conta}
          onChange={campos.setConta}
          data={(campos.contas.data ?? []).map((item) => ({
            value: String(item.id),
            label: item.label,
          }))}
        />
      </Group>

      <div>
        <Text size="sm" fw={500}>
          Comprovante{' '}
          {preenchido && (
            <Text component="span" c="red">
              *
            </Text>
          )}
        </Text>
        <FileButton
          onChange={campos.setComprovante}
          accept="application/pdf,image/jpeg,image/png"
        >
          {(props) => (
            <Button
              {...props}
              variant="default"
              disabled={!preenchido}
              leftSection={<IconPaperclip size={16} />}
            >
              {campos.comprovante?.name ?? 'Selecionar PDF, JPG ou PNG'}
            </Button>
          )}
        </FileButton>
        <Text size="xs" c="dimmed" mt={4}>
          Até 10 MB.
        </Text>
      </div>

      {preenchido && !completo && (
        <Alert color="yellow">
          Informe forma de pagamento, conta que recebeu e comprovante para declarar este valor — ou
          zere o valor pago para cadastrar a proposta em aberto.
        </Alert>
      )}
    </Stack>
  );
}
