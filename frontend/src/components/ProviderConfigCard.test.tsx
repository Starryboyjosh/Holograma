import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProviderConfigCard } from './ProviderConfigCard';
import type { LlmTestResult, OllamaModelsResult, ProviderInfo } from '../types';

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
  listOllamaModels,
  initialProvider = 'openrouter',
}: {
  testConnection: (i: { provider: string }) => Promise<LlmTestResult>;
  listOllamaModels?: () => Promise<OllamaModelsResult>;
  initialProvider?: string;
}) {
  const initial =
    PROVIDERS.find((p) => p.id === initialProvider) ?? PROVIDERS[0];
  const [llmProvider, setLlmProvider] = useState(initial.id);
  const [model, setModel] = useState(initial.current_model);
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(initial.base_url);
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
      listOllamaModels={listOllamaModels}
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

    // Without listOllamaModels, free-text field remains (fallback).
    const modelInput = screen.getByPlaceholderText('gemma3:1b') as HTMLInputElement;
    expect(modelInput.value).toBe('qwen3:8b'); // current_model from metadata
    expect(screen.queryByText(/API key/i)).not.toBeInTheDocument();
  });

  it('shows a select of models installed on the PC when Ollama is selected', async () => {
    const user = userEvent.setup();
    const listOllamaModels = vi.fn().mockResolvedValue({
      status: 'ok',
      models: ['gemma3:1b', 'llama3.2:3b'],
      message: '2 modelo(s) instalado(s).',
    });

    render(
      <Harness
        testConnection={vi.fn()}
        listOllamaModels={listOllamaModels}
        initialProvider="ollama"
      />,
    );

    await waitFor(() => expect(listOllamaModels).toHaveBeenCalled());

    const select = await screen.findByLabelText('Modelo Ollama instalado');
    expect(select).toBeInTheDocument();
    // current_model qwen3:8b is kept even if not installed
    expect(select).toHaveValue('qwen3:8b');
    expect(screen.getByRole('option', { name: /gemma3:1b/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /llama3.2:3b/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /qwen3:8b.*no instalado/i })).toBeInTheDocument();

    await user.selectOptions(select, 'gemma3:1b');
    expect(select).toHaveValue('gemma3:1b');
  });

  it('locks Ollama controls while one discovery request is pending and restores them', async () => {
    let resolveModels: (value: OllamaModelsResult) => void = () => {};
    const listOllamaModels = vi.fn(
      () => new Promise<OllamaModelsResult>((resolve) => { resolveModels = resolve; }),
    );
    render(<Harness testConnection={vi.fn()} listOllamaModels={listOllamaModels} initialProvider="ollama" />);

    await waitFor(() => expect(listOllamaModels).toHaveBeenCalledTimes(1));
    const updating = await screen.findByRole('button', { name: 'Actualizando…' });
    expect(updating).toBeDisabled();
    expect(screen.getByPlaceholderText('gemma3:1b')).toBeDisabled();
    await userEvent.setup().click(updating);
    expect(listOllamaModels).toHaveBeenCalledTimes(1);

    resolveModels({ status: 'ok', models: ['gemma3:1b'], message: '1 modelo.' });
    const select = await screen.findByLabelText('Modelo Ollama instalado');
    expect(select).not.toBeDisabled();
    expect(screen.getByRole('button', { name: 'Actualizar lista' })).not.toBeDisabled();
  });
});
