// Registers Testing Library's DOM matchers (toBeInTheDocument, …) on vitest's
// expect and auto-cleans the rendered tree between tests.
import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => cleanup());
