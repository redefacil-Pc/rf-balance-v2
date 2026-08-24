import { Button, Card, createTheme, Modal, type MantineColorsTuple } from '@mantine/core';

/**
 * Tokens visuais do RF Balance. Cor, raio e tipografia vivem só aqui —
 * componente nenhum define hex à mão.
 */
const marca: MantineColorsTuple = [
  '#f0f3ff',
  '#e2e7ff',
  '#c7d0fe',
  '#a7b4fb',
  '#8999f5',
  '#7183ee',
  '#6072e5',
  '#4f5fd0',
  '#424fad',
  '#39458a',
];

/** Verde reservado para confirmação de valor recebido. */
const positivo: MantineColorsTuple = [
  '#e6fcf5',
  '#d0f7e9',
  '#a2eed3',
  '#70e3bb',
  '#4bdaa7',
  '#35d69b',
  '#26d393',
  '#16bb7f',
  '#03a670',
  '#00905f',
];

export const theme = createTheme({
  primaryColor: 'marca',
  primaryShade: { light: 7, dark: 5 },
  colors: { marca, positivo },
  defaultRadius: 'lg',
  fontFamily:
    'Aptos, "Segoe UI Variable", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
  fontFamilyMonospace: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  headings: { fontWeight: '650', fontFamily: 'Aptos, "Segoe UI Variable", "Segoe UI", sans-serif' },
  cursorType: 'pointer',
  focusRing: 'auto',
  components: {
    Button: Button.extend({
      defaultProps: { radius: 'lg' },
    }),
    Card: Card.extend({
      defaultProps: { radius: 'lg' },
    }),
    Modal: Modal.extend({
      defaultProps: {
        radius: 'lg',
        overlayProps: { backgroundOpacity: 0.58, blur: 4 },
      },
    }),
  },
  // valor financeiro é tabular: dígitos precisam alinhar em coluna
  other: {
    fonteNumerica: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  },
});
