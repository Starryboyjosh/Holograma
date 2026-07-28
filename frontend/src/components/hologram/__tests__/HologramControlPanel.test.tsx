import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ToastProvider } from '../../../context/ToastContext';
import { HologramControlPanel } from '../HologramControlPanel';

const fetchMock = vi.fn();
vi.mock('../../../lib/backend', () => ({ apiFetch: (...args: unknown[]) => fetchMock(...args) }));

function response(body: unknown, ok = true) { return Promise.resolve({ ok, status: ok ? 200 : 400, json: () => Promise.resolve(body) }); }

describe('HologramControlPanel', () => {
  beforeEach(() => {
    fetchMock.mockImplementation((path: string) => {
      if (path === '/api/hologram/status') return response({ connected: false, ip: '', port: 50200, units: [{ role: 'top', enabled: true, ip: '10.0.0.1', port: 50200, connected: true, current_index: 1, current_media_id: 'idle', last_error: null, worker_alive: true }, { role: 'center', enabled: true, ip: '10.0.0.2', port: 50200, connected: false, current_index: null, current_media_id: null, last_error: 'offline', worker_alive: false }, { role: 'bottom', enabled: true, ip: '10.0.0.3', port: 50200, connected: true, current_index: 8, current_media_id: 'careers', last_error: null, worker_alive: true }], rotation: { active: true, paused: false, current: 'careers', next: 'admissions' } });
      if (path === '/api/hologram/identities') return response({ identities: [{ id: 'holomind', title: 'Holomind', index: 7, enabled: true, default: true, keywords: ['holomind'] }] });
      if (path === '/api/hologram/promotions') return response({ promotions: [] });
      return response({ status: 'ok' });
    });
  });

  it('renders three roles, live state and an empty rotation state', async () => {
    render(<ToastProvider><HologramControlPanel /></ToastProvider>);
    expect(await screen.findByText('Superior — Mascota')).toBeInTheDocument();
    expect(screen.getByText('Central — Identidades')).toBeInTheDocument();
    expect(screen.getByText('Inferior — Promociones')).toBeInTheDocument();
    expect(await screen.findByText(/No hay promociones elegibles/i)).toBeInTheDocument();
  });

  it('uses the administrative connect endpoint and refreshes after an operation', async () => {
    render(<ToastProvider><HologramControlPanel /></ToastProvider>);
    await screen.findByText('Superior — Mascota');
    const connectButton = screen.getByRole('article', { name: 'Central — Identidades' }).querySelectorAll('button')[2] as HTMLButtonElement;
    connectButton.click();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/hologram/units/center/connect', expect.objectContaining({ method: 'POST' })));
  });
});
