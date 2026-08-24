import { Button, Center, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <Center mih="60vh" p="md">
      <Stack align="center">
        <Title order={1}>Página não encontrada</Title>
        <Text c="dimmed">Confira o endereço ou volte para o início.</Text>
        <Button component={Link} to="/">
          Voltar para o início
        </Button>
      </Stack>
    </Center>
  );
}
