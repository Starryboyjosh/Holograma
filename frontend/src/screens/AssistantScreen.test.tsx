import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AssistantScreen } from './AssistantScreen';

const requestServerListen = vi.fn();

vi.mock('../context/SessionContext', () => ({
  useSession: () => ({
    chat: {
      assistantState: 'idle',
      voiceMode: 'ptt',
      aiSpokenText: 'Holograma listo para interactuar.',
      userSpokenText: '',
      highlightKeyword: '',
      personCount: 0,
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

vi.mock('../context/ToastContext', () => ({ useToast: () => vi.fn() }));
vi.mock('../components/CameraFeed', () => ({ CameraFeed: () => <div>Cámara en vivo</div> }));
vi.mock('../components/DetachButton', () => ({ DetachButton: () => <button>Separar cámara</button> }));

describe('AssistantScreen', () => {
  beforeEach(() => requestServerListen.mockClear());

  it('presenta Hablar como flujo principal y activa el micrófono', async () => {
    render(<AssistantScreen />);

    expect(screen.getByRole('heading', { name: 'Hablar con el asistente' })).toBeInTheDocument();
    screen.getByRole('button', { name: 'Toca para hablar' }).click();
    expect(requestServerListen).toHaveBeenCalledOnce();
  });
});
