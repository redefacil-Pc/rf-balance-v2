import { Button, Card, createTheme, Modal, type MantineColorsTuple } from '@mantine/core';

/**
 * Tokens visuais do RF Balance. Cor, raio e tipografia vivem só aqui —
 * componente nenhum define hex à mão.
 */
const marca: MantineColorsTuple = [
  '#eef3ff',
  '#dce4f5',
  '#b9c7e2',
  '#94a8d0',
  '#748dc0',
  '#5f7cb8',
  '#5474b4',
  '#44639f',
  '#3a5890',
  '#2c4b80',
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
  defaultRadius: 'md',
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  fontFamilyMonospace: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  headings: { fontWeight: '600' },
  cursorType: 'pointer',
  focusRing: 'auto',
  components: {
    Button: Button.extend({
      defaultProps: { radius: 'md' },
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
