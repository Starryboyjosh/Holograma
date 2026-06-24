export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  desc: string;
}

export interface SavedObject {
  id: number;
  label: string;
  desc: string;
  x: number;
  y: number;
  w: number;
  h: number;
  thumbnail: string;
}

// Mirror of provider_config.provider_public_info() (GET /api/providers). Carries
// only safe metadata — never a secret, only whether a key is configured.
export interface ProviderInfo {
  id: string;
  label: string;
  description: string;
  kind: 'cloud' | 'local';
  default_model: string;
  current_model: string;
  supports_discovery: boolean;
  needs_base_url: boolean;
  base_url: string;
  requires_key: boolean;
  key_env: string | null;
  key_configured: boolean;
}

// Editable LLM form state (the secret-bearing apiKey is write-only: '' = leave
// the stored key untouched).
export interface LlmConfigForm {
  model: string;
  apiKey: string;
  baseUrl: string;
}

// Payload for POST /api/llm/test (non-persisting connection probe).
export interface LlmTestInput {
  provider: string;
  model?: string;
  api_key?: string;
  base_url?: string;
}

export interface LlmTestResult {
  status: 'ok' | 'error';
  message: string;
}
