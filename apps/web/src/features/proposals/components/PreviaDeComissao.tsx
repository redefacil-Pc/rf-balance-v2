import { Alert, Card, Group, Loader, Stack, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import type { UseQueryResult } from '@tanstack/react-query';

import type { CommissionPreview } from '@/features/proposals/queries/useCommissionPreview';
import type { ApiError } from '@/shared/api/problem-details';
import { formatarMoeda } from '@/shared/formatters/currency';

/**
 * Comissão da empresa e do consultor conferidas antes de salvar.
 *
 * Os dois números vêm prontos da API, que roda o motor de comissão. Nada aqui
 * multiplica ou soma dinheiro — a conta na tela divergiria da conta que paga no
 * primeiro ajuste de regra, e o operador confiaria na errada.
 */
export function PreviaDeComissao({
  previa,
}: {
  previa: UseQueryResult<CommissionPreview, ApiError>;
}) {
  const dados = previa.data;

  return (
    <Card withBorder padding="sm" bg="var(--mantine-color-body)">
      <Group grow align="flex-start">
        <Valor
          rotulo="Comissão da Empresa"
          descricao="Valor da operação × TPS ÷ 100"
          valor={dados?.company_commission_amount}
          carregando={previa.isFetching}
        />
        <Valor
          rotulo="Comissão do Consultor"
          descricao={
            dados?.strategy === 'SCALED_CONSULTANT'
              ? 'Consultor escalonado — produção acumulada'
              : 'Faixa de TPS da regra vigente'
          }
          valor={dados?.consultant_commission_amount ?? undefined}
          carregando={previa.isFetching}
          estimativa={dados?.estimate ?? false}
        />
      </Group>

      {dados?.note && (
        <Alert
          mt="sm"
          color={dados.estimate ? 'yellow' : 'blue'}
          icon={dados.estimate ? <IconAlertTriangle size={16} /> : undefined}
        >
          <Text size="xs">{dados.note}</Text>
        </Alert>
      )}

      {previa.error && (
        <Text size="xs" c="dimmed" mt="sm">
          Não foi possível calcular a prévia agora. O valor é conferido no servidor ao salvar.
        </Text>
      )}
    </Card>
  );
}

function Valor({
  rotulo,
  descricao,
  valor,
  carregando,
  estimativa = false,
}: {
  rotulo: string;
  descricao: string;
  valor?: string;
  carregando: boolean;
  estimativa?: boolean;
}) {
  return (
    <Stack gap={2}>
      <Text size="sm" fw={500}>
        {rotulo}
      </Text>
      <Group gap="xs">
        <Text size="lg" fw={700} c={valor === undefined ? 'dimmed' : undefined}>
          {valor === undefined ? formatarMoeda('0') : formatarMoeda(valor)}
        </Text>
        {carregando && <Loader size="xs" />}
        {estimativa && !carregando && (
          <Text size="xs" c="yellow" fw={500}>
            estimativa
          </Text>
        )}
      </Group>
      <Text size="xs" c="dimmed">
        {descricao}
      </Text>
    </Stack>
  );
}
