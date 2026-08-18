import { ActionIcon, Tooltip, useComputedColorScheme, useMantineColorScheme } from '@mantine/core';
import { IconMoonStars, IconSunHigh } from '@tabler/icons-react';

export function ColorSchemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const colorScheme = useComputedColorScheme('light');
  const dark = colorScheme === 'dark';
  const label = dark ? 'Usar tema claro' : 'Usar tema escuro';

  return (
    <Tooltip label={label} position="bottom" withArrow>
      <ActionIcon
        variant="subtle"
        color="gray"
        size="lg"
        radius="xl"
        aria-label={label}
        onClick={() => setColorScheme(dark ? 'light' : 'dark')}
      >
        {dark ? <IconSunHigh size={19} stroke={1.7} /> : <IconMoonStars size={19} stroke={1.7} />}
      </ActionIcon>
    </Tooltip>
  );
}
