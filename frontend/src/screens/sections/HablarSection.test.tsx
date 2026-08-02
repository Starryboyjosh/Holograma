import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HablarSection } from './HablarSection';

const requestServerListen = vi.fn();

vi.mock('../../context/SessionContext', () => ({
  useSession: () => ({
    chat: {
      assistantState: 'idle',
      voiceMode: 'ptt',
      aiSpokenText: 'Holograma listo para interactuar.',
      userSpokenText: '',
      highlightKeyword: '',
      personCount: 0,
      wsConnected: true,
      requestServerListen,
      sendPrompt: vi.fn(),
      setAssistantState: vi.fn(),
      setVoiceModeRemote: vi.fn(),
    },
    config: { yoloEnabled: true },
    camera: {
      cameraOn: true,
      feedNonce: 0,
      toggleCamera: vi.fn(),
    },
  }),
}));

vi.mock('../../context/ToastContext', () => ({ useToast: () => vi.fn() }));
vi.mock('../../components/CameraFeed', () => ({ CameraFeed: () => <div>Cámara en vivo</div> }));
vi.mock('../../components/DetachButton', () => ({ DetachButton: () => <button>Separar cámara</button> }));

describe('HablarSection', () => {
  beforeEach(() => requestServerListen.mockClear());

  // Antes esto era AssistantScreen, una pantalla propia en /assistant. En la
  // landing de una sola página es la sección "hablar" (ver LandingScreen), pero
  // el contenido y el contrato de accesibilidad no cambiaron: mismo heading,
  // mismo botón para activar el micrófono.
  it('presenta Hablar como flujo principal y activa el micrófono', async () => {
    render(
      <MemoryRouter>
        <HablarSection />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('heading', { name: 'Interactúa con el asistente' }),
    ).toBeInTheDocument();
    screen.getByRole('button', { name: 'Activar micrófono' }).click();
    expect(requestServerListen).toHaveBeenCalledOnce();
  });
});
