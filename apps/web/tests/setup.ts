import '@testing-library/jest-dom/vitest';

/**
 * O jsdom não implementa `matchMedia` nem `ResizeObserver`, e o Mantine depende
 * dos dois (esquema de cor e componentes responsivos). Sem estes stubs, todo
 * teste que renderiza um componente do design system quebra.
 *
 * São funções comuns de propósito, e não `vi.fn()`: um `vi.restoreAllMocks()`
 * dentro de um teste apagaria a implementação e derrubaria os testes seguintes.
 */
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList,
});

class ResizeObserverStub implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: ResizeObserverStub,
});

Object.defineProperty(window, 'scrollTo', {
  writable: true,
  configurable: true,
  value: (): void => undefined,
});
