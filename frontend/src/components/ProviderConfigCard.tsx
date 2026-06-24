import { useState } from 'react';
import { Card, SectionTitle } from './ui/Card';
import { Field, Select, TextInput } from './ui/Field';
import { apiKeyPlaceholder, buildLlmTestInput } from '../lib/providerForm';
import type { LlmTestInput, LlmTestResult, ProviderInfo } from '../types';

// Convenience presets for the Ollama model field (free text is still allowed).
const OLLAMA_SUGGESTIONS = ['gemma3:1b', 'gemma4:e4b', 'qwen3:8b', 'llama3.2:3b'];

interface Props {
  llmProvider: string;
  setLlmProvider: (v: string) => void;
  model: string;
  setModel: (v: string) => void;
  apiKey: string;
  setApiKey: (v: string) => void;
  baseUrl: string;
  setBaseUrl: (v: string) => void;
  providers: ProviderInfo[];
  loading: boolean;
  testConnection: (input: LlmTestInput) => Promise<LlmTestResult>;
  showToast: (message: string) => void;
}

// The AI-brain settings card: one authoritative provider picker driven by
// GET /api/providers (friendly labels, configured state, base-url/discovery
// hints) plus a real "Probar conexión" against POST /api/llm/test.
export function ProviderConfigCard({
  llmProvider,
  setLlmProvider,
  model,
  setModel,
  apiKey,
  setApiKey,
  baseUrl,
  setBaseUrl,
  providers,
  loading,
  testConnection,
  showToast,
}: Props) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<LlmTestResult | null>(null);

  const selected: ProviderInfo | undefined = providers.find((p) => p.id === llmProvider);
  const cloud = providers.filter((p) => p.kind === 'cloud');
  const local = providers.filter((p) => p.kind === 'local');

  const onProviderChange = (id: string) => {
    setLlmProvider(id);
    setTestResult(null);
    setApiKey('');
    const next = providers.find((p) => p.id === id);
    if (next) {
      setModel(next.current_model || next.default_model);
      setBaseUrl(next.base_url || '');
    }
  };

  const onTest = async () => {
    if (!selected) return;
    setTesting(true);
    setTestResult(null);
    const result = await testConnection(buildLlmTestInput(selected, { model, apiKey, baseUrl }));
    setTestResult(result);
    showToast(result.message);
    setTesting(false);
  };

  const usesModel = selected ? selected.id !== 'local_only' : true;

  return (
    <Card>
      <div className="flex items-center justify-between">
        <SectionTitle>Cerebro de la IA</SectionTitle>
        {selected?.requires_key && (
          <span
            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full ${
              selected.key_configured
                ? 'bg-emerald-500/15 text-emerald-500'
                : 'bg-amber-500/15 text-amber-500'
            }`}
          >
            {selected.key_configured ? 'API key configurada' : 'Sin API key'}
          </span>
        )}
      </div>

      <Field label="Proveedor de IA">
        <Select
          aria-label="Proveedor de IA"
          value={llmProvider}
          disabled={loading}
          onChange={(e) => onProviderChange(e.target.value)}
        >
          <optgroup label="En la nube (requiere internet)">
            {cloud.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </optgroup>
          <optgroup label="Local (sin internet)">
            {local.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </optgroup>
        </Select>
      </Field>

      {selected && (
        <p className="text-xs text-gray-600 dark:text-gray-400 -mt-1">{selected.description}</p>
      )}

      {usesModel && (
        <Field label="Modelo">
          <TextInput
            type="text"
            list={selected?.id === 'ollama' ? 'ollama-model-suggestions' : undefined}
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={selected?.default_model || 'nombre-del-modelo'}
          />
          {selected?.id === 'ollama' && (
            <datalist id="ollama-model-suggestions">
              {OLLAMA_SUGGESTIONS.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          )}
        </Field>
      )}

      {selected?.needs_base_url && (
        <Field label="URL base del endpoint (compatible con OpenAI)">
          <TextInput
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://127.0.0.1:8080/v1"
          />
        </Field>
      )}

      {selected?.requires_key && (
        <Field label="API Key">
          <TextInput
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={apiKeyPlaceholder(selected)}
          />
        </Field>
      )}

      {!usesModel && (
        <p className="text-xs text-gray-600 dark:text-gray-400">
          Este modo no usa un modelo de IA: responde solo con las skills locales de UNEV.
        </p>
      )}

      {usesModel && (
        <div className="space-y-2 pt-1">
          <button
            type="button"
            onClick={onTest}
            disabled={testing || loading || !selected}
            className={`w-full px-4 py-3 rounded-xl text-xs font-bold uppercase tracking-wider transition-all ${
              testing
                ? 'bg-[#E25C1D]/20 text-[#E25C1D] border border-[#E25C1D]/50 animate-pulse'
                : 'bg-gray-100 hover:bg-gray-200 border border-gray-200 text-gray-700 dark:bg-slate-900 dark:hover:bg-slate-800 dark:border-slate-800 dark:text-slate-300'
            }`}
          >
            {testing ? 'Probando…' : 'Probar conexión'}
          </button>
          {testResult && (
            <p
              role="status"
              className={`text-xs font-medium ${
                testResult.status === 'ok' ? 'text-emerald-500' : 'text-red-500'
              }`}
            >
              {testResult.message}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
