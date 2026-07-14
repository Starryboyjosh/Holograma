import { useCallback, useEffect, useState } from 'react';
import { Card, SectionTitle } from './ui/Card';
import { Field, Select, TextInput } from './ui/Field';
import { apiKeyPlaceholder, buildLlmTestInput } from '../lib/providerForm';
import type {
  LlmTestInput,
  LlmTestResult,
  OllamaModelsResult,
  ProviderInfo,
} from '../types';

// Fallback presets when Ollama is down or has no models (free text still allowed).
const OLLAMA_FALLBACK_SUGGESTIONS = ['gemma3:1b', 'gemma4:e4b', 'qwen3:8b', 'llama3.2:3b'];

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
  /** Live list from GET /api/ollama/models (optional; without it, static hints only). */
  listOllamaModels?: () => Promise<OllamaModelsResult>;
  showToast: (message: string) => void;
}

// The AI-brain settings card: one authoritative provider picker driven by
// GET /api/providers (friendly labels, configured state, base-url/discovery
// hints) plus a real "Probar conexión" against POST /api/llm/test.
// When provider is Ollama, the model field becomes a select of installed tags.
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
  listOllamaModels,
  showToast,
}: Props) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<LlmTestResult | null>(null);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaStatus, setOllamaStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');
  const [ollamaMessage, setOllamaMessage] = useState('');

  const selected: ProviderInfo | undefined = providers.find((p) => p.id === llmProvider);
  const cloud = providers.filter((p) => p.kind === 'cloud');
  const local = providers.filter((p) => p.kind === 'local');
  const isOllama = selected?.id === 'ollama';

  const refreshOllamaModels = useCallback(async () => {
    if (!listOllamaModels) {
      setOllamaStatus('idle');
      setOllamaModels([]);
      setOllamaMessage('');
      return;
    }
    setOllamaStatus('loading');
    const result = await listOllamaModels();
    setOllamaModels(result.models);
    setOllamaMessage(result.message);
    setOllamaStatus(result.status === 'ok' ? 'ok' : 'error');
    // If the form model is empty and Ollama has installs, pick the first one.
    if (result.status === 'ok' && result.models.length > 0) {
      // leave caller's model if already set (possibly to a valid tag)
    }
  }, [listOllamaModels]);

  useEffect(() => {
    if (!isOllama) {
      setOllamaStatus('idle');
      setOllamaModels([]);
      setOllamaMessage('');
      return;
    }
    // Fetch installed models whenever Ollama is the selected provider.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshOllamaModels();
  }, [isOllama, refreshOllamaModels]);

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

  // Options for the Ollama select: installed tags + current value if not listed.
  const ollamaSelectOptions = (() => {
    const opts = [...ollamaModels];
    if (model && !opts.includes(model)) {
      opts.unshift(model);
    }
    return opts;
  })();
  const showOllamaSelect = isOllama && ollamaStatus === 'ok' && ollamaModels.length > 0;

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
          {showOllamaSelect ? (
            <div className="space-y-2">
              <Select
                aria-label="Modelo Ollama instalado"
                value={model}
                disabled={loading || ollamaStatus === 'loading'}
                onChange={(e) => setModel(e.target.value)}
              >
                {ollamaSelectOptions.map((m) => (
                  <option key={m} value={m}>
                    {m}
                    {ollamaModels.includes(m) ? '' : ' (no instalado)'}
                  </option>
                ))}
              </Select>
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] text-gray-500 dark:text-gray-400">
                  {ollamaMessage || 'Modelos detectados en este PC (ollama list).'}
                </p>
                <button
                  type="button"
                  onClick={() => void refreshOllamaModels()}
                  disabled={ollamaStatus === 'loading'}
                  className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-[#E25C1D] hover:underline disabled:opacity-50"
                >
                  {ollamaStatus === 'loading' ? 'Actualizando…' : 'Actualizar lista'}
                </button>
              </div>
            </div>
          ) : (
            <>
              <TextInput
                type="text"
                list={isOllama ? 'ollama-model-suggestions' : undefined}
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder={selected?.default_model || 'nombre-del-modelo'}
              />
              {isOllama && (
                <>
                  <datalist id="ollama-model-suggestions">
                    {(ollamaModels.length > 0 ? ollamaModels : OLLAMA_FALLBACK_SUGGESTIONS).map(
                      (m) => (
                        <option key={m} value={m} />
                      ),
                    )}
                  </datalist>
                  <div className="flex items-center justify-between gap-2 pt-1">
                    <p
                      className={`text-[11px] ${
                        ollamaStatus === 'error'
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-gray-500 dark:text-gray-400'
                      }`}
                    >
                      {ollamaStatus === 'loading'
                        ? 'Consultando modelos instalados en Ollama…'
                        : ollamaMessage ||
                          'Escribe el nombre del modelo o inicia Ollama para listarlos.'}
                    </p>
                    {listOllamaModels && (
                      <button
                        type="button"
                        onClick={() => void refreshOllamaModels()}
                        disabled={ollamaStatus === 'loading'}
                        className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-[#E25C1D] hover:underline disabled:opacity-50"
                      >
                        {ollamaStatus === 'loading' ? 'Actualizando…' : 'Actualizar lista'}
                      </button>
                    )}
                  </div>
                </>
              )}
            </>
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
