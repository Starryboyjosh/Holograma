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

export const API_KEY_FIELD_BY_PROVIDER: Record<string, string> = {
  openrouter: 'OPENROUTER_API_KEY',
  openai: 'OPENAI_API_KEY',
  claude_native: 'ANTHROPIC_API_KEY',
  nvidia: 'NVIDIA_API_KEY',
};

export const DEFAULT_API_MODEL_BY_PROVIDER: Record<string, string> = {
  openrouter: 'meta-llama/llama-3.3-70b-instruct',
  openai: 'gpt-4o-mini',
  claude_native: 'claude-3-5-sonnet-latest',
  nvidia: 'moonshotai/kimi-k2.6',
};
