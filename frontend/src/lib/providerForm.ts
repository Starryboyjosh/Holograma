// Pure mapping between the Settings form and the backend contract. Kept free of
// React/fetch so the rules ("which env var holds the key", "ollama uses
// OLLAMA_MODEL", "only send a key the operator actually typed") are unit-testable.
import type { LlmConfigForm, LlmTestInput, ProviderInfo } from '../types';

/** Build the LLM slice of the POST /api/config payload for a provider + form.
 *
 *  Rules:
 *  - LLM_PROVIDER is always set to the chosen provider (authoritative).
 *  - ollama writes OLLAMA_MODEL; other LLM providers write the generic LLM_MODEL;
 *    local_only carries no model.
 *  - the API key is write-only: only included when the operator typed one, so an
 *    empty field never wipes a stored key.
 *  - the custom OpenAI endpoint persists its base URL.
 */
export function buildLlmConfigPayload(
  provider: ProviderInfo,
  form: LlmConfigForm,
): Record<string, string> {
  const payload: Record<string, string> = { LLM_PROVIDER: provider.id };
  const model = form.model.trim();

  if (provider.id === 'ollama') {
    payload.OLLAMA_MODEL = model;
  } else if (provider.id !== 'local_only') {
    payload.LLM_MODEL = model;
  }

  if (provider.requires_key && provider.key_env && form.apiKey.trim()) {
    payload[provider.key_env] = form.apiKey.trim();
  }

  if (provider.needs_base_url && form.baseUrl.trim()) {
    payload.OPENAI_COMPAT_BASE_URL = form.baseUrl.trim();
  }

  return payload;
}

/** Build the POST /api/llm/test body. Sends the in-form values (including a
 *  freshly typed key) so the operator can validate before saving. */
export function buildLlmTestInput(
  provider: ProviderInfo,
  form: LlmConfigForm,
): LlmTestInput {
  const input: LlmTestInput = { provider: provider.id };
  if (form.model.trim()) input.model = form.model.trim();
  if (provider.requires_key && form.apiKey.trim()) input.api_key = form.apiKey.trim();
  if (provider.needs_base_url && form.baseUrl.trim()) input.base_url = form.baseUrl.trim();
  return input;
}

/** Placeholder/help text for the API-key field reflecting stored state without
 *  ever revealing the key. */
export function apiKeyPlaceholder(provider: ProviderInfo): string {
  if (!provider.requires_key) return '';
  return provider.key_configured
    ? 'Guardada — escribe una nueva para reemplazarla'
    : 'Pega la API key';
}
