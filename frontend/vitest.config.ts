import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// Separate from vite.config.ts so the app build config stays free of test types.
// jsdom + Testing Library for component tests; pure modules need no DOM.
export default defineConfig({
  plugins: [react()],
  // Use the automatic JSX runtime so test files need no `import React`.
  esbuild: { jsx: 'automatic' },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
  },
});
