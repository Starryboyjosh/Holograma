import { describe, expect, it } from 'vitest';
import { apiKeyPlaceholder, buildLlmConfigPayload, buildLlmTestInput } from './providerForm';
import type { ProviderInfo } from '../types';

function provider(overrides: Partial<ProviderInfo> = {}): ProviderInfo {
  return {
    id: 'openrouter',
    label: 'OpenRouter',
    description: '',
    kind: 'cloud',
    default_model: 'meta-llama/llama-3.3-70b-instruct',
    current_model: 'meta-llama/llama-3.3-70b-instruct',
    supports_discovery: true,
    needs_base_url: false,
    base_url: 'https://openrouter.ai/api/v1',
    requires_key: true,
    key_env: 'OPENROUTER_API_KEY',
    key_configured: false,
    ...overrides,
  };
}

describe('buildLlmConfigPayload', () => {
  it('writes LLM_MODEL for a cloud provider and includes a typed key', () => {
    const payload = buildLlmConfigPayload(provider(), {
      model: 'gpt-x',
      apiKey: 'sk-new',
      baseUrl: '',
    });
    expect(payload).toEqual({
      LLM_PROVIDER: 'openrouter',
      LLM_MODEL: 'gpt-x',
      OPENROUTER_API_KEY: 'sk-new',
    });
  });

  it('never sends the key when the field is left blank (no wipe)', () => {
    const payload = buildLlmConfigPayload(provider({ key_configured: true }), {
      model: 'gpt-x',
      apiKey: '   ',
      baseUrl: '',
    });
    expect(payload).not.toHaveProperty('OPENROUTER_API_KEY');
  });

  it('writes OLLAMA_MODEL (not LLM_MODEL) and no key for ollama', () => {
    const ollama = provider({
      id: 'ollama',
      kind: 'local',
      requires_key: false,
      key_env: null,
    });
    const payload = buildLlmConfigPayload(ollama, { model: 'qwen3:8b', apiKey: '', baseUrl: '' });
    expect(payload).toEqual({ LLM_PROVIDER: 'ollama', OLLAMA_MODEL: 'qwen3:8b' });
  });

  it('carries no model for local_only', () => {
    const lo = provider({ id: 'local_only', kind: 'local', requires_key: false, key_env: null });
    expect(buildLlmConfigPayload(lo, { model: '', apiKey: '', baseUrl: '' })).toEqual({
      LLM_PROVIDER: 'local_only',
    });
  });

  it('persists the base URL for the custom OpenAI endpoint', () => {
    const custom = provider({
      id: 'custom_openai',
      needs_base_url: true,
      base_url: '',
      key_env: 'OPENAI_COMPAT_API_KEY',
    });
    const payload = buildLlmConfigPayload(custom, {
      model: 'served',
      apiKey: 'sk-1',
      baseUrl: 'http://127.0.0.1:8080/v1',
    });
    expect(payload).toEqual({
      LLM_PROVIDER: 'custom_openai',
      LLM_MODEL: 'served',
      OPENAI_COMPAT_API_KEY: 'sk-1',
      OPENAI_COMPAT_BASE_URL: 'http://127.0.0.1:8080/v1',
    });
  });
});

describe('buildLlmTestInput', () => {
  it('includes only the filled fields', () => {
    expect(
      buildLlmTestInput(provider(), { model: 'm', apiKey: 'sk', baseUrl: '' }),
    ).toEqual({ provider: 'openrouter', model: 'm', api_key: 'sk' });
  });

  it('omits the key for a keyless provider even if text is present', () => {
    const ollama = provider({ id: 'ollama', requires_key: false, key_env: null });
    expect(buildLlmTestInput(ollama, { model: 'qwen', apiKey: 'x', baseUrl: '' })).toEqual({
      provider: 'ollama',
      model: 'qwen',
    });
  });
});

describe('apiKeyPlaceholder', () => {
  it('reflects configured state without revealing the key', () => {
    expect(apiKeyPlaceholder(provider({ key_configured: true }))).toMatch(/reemplaza/i);
    expect(apiKeyPlaceholder(provider({ key_configured: false }))).toMatch(/pega/i);
  });

  it('is empty for keyless providers', () => {
    expect(apiKeyPlaceholder(provider({ requires_key: false }))).toBe('');
  });
});
