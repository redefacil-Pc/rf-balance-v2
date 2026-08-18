import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { UiProvider } from '@/app/providers/UiProvider';
import { ColorSchemeToggle } from '@/shared/components/ColorSchemeToggle';

describe('ColorSchemeToggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-mantine-color-scheme');
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('alterna para o tema escuro e persiste a preferência', async () => {
    render(
      <UiProvider>
        <ColorSchemeToggle />
      </UiProvider>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Usar tema escuro' }));

    expect(await screen.findByRole('button', { name: 'Usar tema claro' })).toBeInTheDocument();
    expect(localStorage.getItem('rfbalance-color-scheme')).toBe('dark');
  });
});
