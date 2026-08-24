import { Alert, Button, Center, Stack, Text, Title } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { isRouteErrorResponse, useRouteError } from 'react-router-dom';

function mensagemDoErro(error: unknown): string {
  if (isRouteErrorResponse(error)) {
    return error.status === 404
      ? 'A página solicitada não existe.'
      : `O servidor respondeu com o código ${error.status}.`;
  }
  return 'Não foi possível carregar esta página. Isso pode acontecer após uma atualização.';
}

export function RouteErrorPage() {
  const error = useRouteError();

  return (
    <Center mih="70vh" p="md">
      <Stack maw={520} w="100%">
        <Title order={1}>Algo deu errado</Title>
        <Alert icon={<IconAlertTriangle />} color="red" title="Falha ao abrir a página">
          <Text>{mensagemDoErro(error)}</Text>
        </Alert>
        <Button onClick={() => window.location.reload()}>Recarregar aplicação</Button>
      </Stack>
    </Center>
  );
}
