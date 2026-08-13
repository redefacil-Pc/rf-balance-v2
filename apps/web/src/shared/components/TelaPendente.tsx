import { Alert, Card, Stack, Text, Title } from '@mantine/core';
import { IconTools } from '@tabler/icons-react';

interface Props {
  titulo: string;
  /** Fase do plano que entrega esta tela. */
  fase: string;
  /** O que a tela vai fazer, para o setor saber o que esperar. */
  descricao: string;
}

/**
 * Placeholder honesto: a rota existe e está protegida, mas a tela depende de
 * endpoints de uma fase seguinte. Nada de dado inventado — dado falso em tela
 * financeira gera decisão errada.
 */
export function TelaPendente({ titulo, fase, descricao }: Props) {
  return (
    <Stack gap="md" maw={720}>
      <Title order={2} size="h3">
        {titulo}
      </Title>
      <Card withBorder radius="md" padding="lg">
        <Alert variant="light" color="blue" icon={<IconTools size={18} />} title={`Fase ${fase}`}>
          <Text size="sm">{descricao}</Text>
        </Alert>
      </Card>
    </Stack>
  );
}
