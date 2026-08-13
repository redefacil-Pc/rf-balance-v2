import { Alert, Stack, Text, Title } from '@mantine/core';
import { IconLock } from '@tabler/icons-react';

/** Estado obrigatório de tela: sem permissão. */
export function SemPermissao({ permissao }: { permissao: string }) {
  return (
    <Stack maw={560} mx="auto" mt="xl" gap="md">
      <Title order={2} size="h3">
        Acesso não liberado
      </Title>
      <Alert variant="light" color="yellow" icon={<IconLock size={18} />}>
        <Text size="sm">
          Seu perfil não tem a permissão <strong>{permissao}</strong>. Peça a liberação ao
          administrador informando essa permissão.
        </Text>
      </Alert>
    </Stack>
  );
}
