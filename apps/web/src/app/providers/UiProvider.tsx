import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import type { ReactNode } from 'react';

import { theme } from '@/app/theme/theme';

import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

export function UiProvider({ children }: { children: ReactNode }) {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications position="top-right" limit={3} />
      {children}
    </MantineProvider>
  );
}
