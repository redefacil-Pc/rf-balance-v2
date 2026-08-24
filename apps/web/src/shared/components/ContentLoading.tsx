import { Skeleton, Stack } from '@mantine/core';

interface Props {
  label?: string;
  minHeight?: number;
}

export function ContentLoading({ label = 'Carregando conteúdo', minHeight = 220 }: Props) {
  return (
    <Stack
      gap="md"
      mih={minHeight}
      role="status"
      aria-label={label}
      aria-live="polite"
      pt="xs"
    >
      <Skeleton height={32} width="38%" radius="md" />
      <Skeleton height={18} width="64%" radius="md" />
      <Skeleton height={120} radius="lg" mt="sm" />
      <Skeleton height={72} radius="lg" />
    </Stack>
  );
}
