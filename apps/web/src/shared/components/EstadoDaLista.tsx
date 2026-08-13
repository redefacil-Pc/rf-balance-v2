import { Alert, Button, Center, Loader, Stack, Text } from '@mantine/core';
import { IconAlertTriangle, IconInbox } from '@tabler/icons-react';
import type { ReactNode } from 'react';

import { ApiError } from '@/shared/api/problem-details';

interface Props {
  carregando: boolean;
  erro: ApiError | null;
  vazio: boolean;
  onTentarNovamente?: () => void;
  mensagemVazio?: string;
  children: ReactNode;
}

/**
 * Os quatro estados obrigatórios de uma listagem (seção 10.6), num só lugar —
 * para nenhuma tela "esquecer" o estado de erro ou o vazio.
 */
export function EstadoDaLista({
  carregando,
  erro,
  vazio,
  onTentarNovamente,
  mensagemVazio = 'Nenhum registro encontrado com os filtros atuais.',
  children,
}: Props) {
  if (carregando) {
    return (
      <Center mih={220}>
        <Loader aria-label="Carregando registros" />
      </Center>
    );
  }

  if (erro) {
    return (
      <Alert
        variant="light"
        color="red"
        icon={<IconAlertTriangle size={18} />}
        title={erro.problem.title}
        role="alert"
      >
        <Stack gap="xs" align="flex-start">
          <Text size="sm">{erro.problem.detail}</Text>
          {erro.correlationId && (
            <Text size="xs" c="dimmed">
              Código para o suporte: {erro.correlationId.slice(0, 8)}
            </Text>
          )}
          {onTentarNovamente && (
            <Button size="xs" variant="default" onClick={onTentarNovamente}>
              Tentar novamente
            </Button>
          )}
        </Stack>
      </Alert>
    );
  }

  if (vazio) {
    return (
      <Center mih={220}>
        <Stack align="center" gap="xs">
          <IconInbox size={32} stroke={1.4} />
          <Text size="sm" c="dimmed" ta="center" maw={360}>
            {mensagemVazio}
          </Text>
        </Stack>
      </Center>
    );
  }

  return <>{children}</>;
}
