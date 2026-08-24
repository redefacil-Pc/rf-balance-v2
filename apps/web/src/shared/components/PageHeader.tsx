import { Badge, Group, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core';
import type { Icon } from '@tabler/icons-react';
import type { ReactNode } from 'react';

interface Props {
  title: ReactNode;
  description: string;
  eyebrow: string;
  icon: Icon;
  badge?: ReactNode;
  badgeColor?: string;
  actions?: ReactNode;
}

export function PageHeader({
  title,
  description,
  eyebrow,
  icon: IconComponent,
  badge,
  badgeColor,
  actions,
}: Props) {
  return (
    <Paper className="rf-page-header" p={{ base: 'md', sm: 'xl' }}>
      <Group justify="space-between" align="center" wrap="wrap" gap="lg">
        <Group align="flex-start" wrap="nowrap" gap="md">
          <ThemeIcon className="rf-page-header-icon" size={48} radius="xl" aria-hidden="true">
            <IconComponent size={23} stroke={1.7} />
          </ThemeIcon>
          <Stack gap={4}>
            <Group gap="xs">
              <Text className="rf-eyebrow" size="xs" fw={700} tt="uppercase">
                {eyebrow}
              </Text>
              {badge && <Badge variant="light" color={badgeColor}>{badge}</Badge>}
            </Group>
            <Title order={1} className="rf-page-title">{title}</Title>
            <Text c="dimmed" size="sm" maw={720}>{description}</Text>
          </Stack>
        </Group>
        {actions && <Group gap="sm">{actions}</Group>}
      </Group>
    </Paper>
  );
}
