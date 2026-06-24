import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProviderConfigCard } from './ProviderConfigCard';
import type { LlmTestResult, ProviderInfo } from '../types';

const PROVIDERS: ProviderInfo[] = [
  {
    id: 'openrouter',
    label: 'OpenRouter',
    description: 'Acceso unificado a muchos modelos.',
    kind: 'cloud',
    default_model: 'meta-llama/llama-3.3-70b-instruct',
    current_model: 'meta-llama/llama-3.3-70b-instruct',
    supports_discovery: true,
    needs_base_url: false,
    base_url: 'https://openrouter.ai/api/v1',
    requires_key: true,
    key_env: 'OPENROUTER_API_KEY',
    key_configured: true,
  },
  {
    id: 'ollama',
    label: 'Ollama local',
    description: 'Modelos locales sin internet.',
    kind: 'local',
    default_model: 'gemma3:1b',
    current_model: 'qwen3:8b',
    supports_discovery: true,
    needs_base_url: false,
    base_url: 'http://127.0.0.1:11434',
    requires_key: false,
    key_env: null,
    key_configured: true,
  },
];

function Harness({
  testConnection,
}: {
  testConnection: (i: { provider: string }) => Promise<LlmTestResult>;
}) {
  const [llmProvider, setLlmProvider] = useState('openrouter');
  const [model, setModel] = useState('meta-llama/llama-3.3-70b-instruct');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://openrouter.ai/api/v1');
  return (
    <ProviderConfigCard
      llmProvider={llmProvider}
      setLlmProvider={setLlmProvider}
      model={model}
      setModel={setModel}
      apiKey={apiKey}
      setApiKey={setApiKey}
      baseUrl={baseUrl}
      setBaseUrl={setBaseUrl}
      providers={PROVIDERS}
      loading={false}
      testConnection={testConnection}
      showToast={vi.fn()}
    />
  );
}

describe('ProviderConfigCard', () => {
  it('shows the configured badge and never reveals the stored key', () => {
    render(<Harness testConnection={vi.fn()} />);

    expect(screen.getByText(/API key configurada/i)).toBeInTheDocument();

    const keyInput = screen.getByPlaceholderText(/reemplaza/i) as HTMLInputElement;
    expect(keyInput.type).toBe('password');
    expect(keyInput.value).toBe(''); // the real key is never sent to the form
  });

  it('runs a real connection probe and shows the returned message', async () => {
    const user = userEvent.setup();
    const testConnection = vi
      .fn()
      .mockResolvedValue({ status: 'ok', message: 'Conexión correcta con OpenRouter.' });

    render(<Harness testConnection={testConnection} />);
    await user.click(screen.getByRole('button', { name: /probar conexión/i }));

    expect(testConnection).toHaveBeenCalledWith(
      expect.objectContaining({ provider: 'openrouter' }),
    );
    expect(await screen.findByText(/Conexión correcta con OpenRouter/i)).toBeInTheDocument();
  });

  it('switching to Ollama loads its model and hides the API-key field', async () => {
    const user = userEvent.setup();
    render(<Harness testConnection={vi.fn()} />);

    await user.selectOptions(screen.getByLabelText('Proveedor de IA'), 'ollama');

    const modelInput = screen.getByPlaceholderText('gemma3:1b') as HTMLInputElement;
    expect(modelInput.value).toBe('qwen3:8b'); // current_model from metadata
    expect(screen.queryByText(/API key/i)).not.toBeInTheDocument();
  });
});
