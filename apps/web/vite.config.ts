import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
// `vitest/config` em vez de `vite`: é o que aceita a chave `test`
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // Bind mount do Windows não propaga inotify para dentro do container: sem
    // polling, o Vite não vê a alteração e o HMR falha em silêncio — o navegador
    // continua servindo o bundle antigo.
    watch: { usePolling: true, interval: 300 },
    // em dev o front chama /api e o Vite encaminha para o container da API
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://api:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Dependencias estaveis ficam fora do entrypoint e podem permanecer no
        // cache entre deploys de regra de negocio.
        manualChunks: {
          'vendor-framework': ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}', 'tests/**/*.test.{ts,tsx}'],
    exclude: ['tests/e2e/**'],
    // Teste de componente aqui monta o provider do Mantine e navega por Select
    // e upload; isolado leva ~1,5 s, mas sob a carga da suíte cheia passa dos
    // 5 s padrão. O limite existe para pegar teste travado, não para medir a
    // máquina — 20 s continua acusando travamento sem reprovar quem só ficou
    // lento porque a suíte cresceu.
    testTimeout: 20_000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/main.tsx'],
      // Baseline real da suite. O CI impede regressao e a meta de evolucao e 70%.
      thresholds: {
        statements: 54,
        branches: 70,
        functions: 55,
        lines: 54,
      },
    },
  },
});
