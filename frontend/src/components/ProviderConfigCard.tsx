import { useCallback, useEffect, useRef, useState } from 'react';
import { Card } from './ui/Card';
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
  const ollamaRequestInFlight = useRef(false);

  const selected: ProviderInfo | undefined = providers.find((p) => p.id === llmProvider);
  const cloud = providers.filter((p) => p.kind === 'cloud');
  const local = providers.filter((p) => p.kind === 'local');
  const isOllama = selected?.id === 'ollama';

  const refreshOllamaModels = useCallback(async () => {
    if (ollamaRequestInFlight.current) return;
    if (!listOllamaModels) {
      setOllamaStatus('idle');
      setOllamaModels([]);
      setOllamaMessage('');
      return;
    }
    ollamaRequestInFlight.current = true;
    setOllamaStatus('loading');
    try {
      const result = await listOllamaModels();
      setOllamaModels(result.models);
      setOllamaMessage(result.message);
      setOllamaStatus(result.status === 'ok' ? 'ok' : 'error');
    } catch {
      setOllamaModels([]);
      setOllamaMessage('No se pudieron consultar los modelos de Ollama.');
      setOllamaStatus('error');
    } finally {
      ollamaRequestInFlight.current = false;
    }
  }, [listOllamaModels]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (isOllama) {
        void refreshOllamaModels();
      } else {
        setOllamaModels([]);
        setOllamaMessage('');
        setOllamaStatus('idle');
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [isOllama, refreshOllamaModels]);

  const onProviderChange = (id: string) => {
    setLlmProvider(id);
    setTestResult(null);
    setApiKey('');
    if (id !== 'ollama') {
      setOllamaModels([]);
      setOllamaMessage('');
      setOllamaStatus('idle');
    }
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
  const ollamaLoading = ollamaStatus === 'loading';

  return (
    <Card>
      {/* El diseño titula esta tarjeta "CEREBRO DEL HOLOGRAMA", centrado y en navy
          (no en naranja como el resto de títulos de sección). */}
      <div className="relative flex items-center justify-center">
        <h3 className="text-center text-[20px] font-bold uppercase tracking-wide text-navy md:text-[24px]">
          Cerebro del holograma
        </h3>
        {selected?.requires_key && (
          <span
            className={`absolute end-0 rounded-[50px] px-3 py-1 text-[10px] font-bold uppercase tracking-wider ${
              selected.key_configured
                ? 'bg-emerald-500/15 text-emerald-600'
                : 'bg-amber-500/15 text-amber-600'
            }`}
          >
            {selected.key_configured ? 'API key configurada' : 'Sin API key'}
          </span>
        )}
      </div>

      <Field label="Proveedor de IA:">
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
        <p className="text-xs text-muted -mt-1">{selected.description}</p>
      )}

      {usesModel && (
        <Field label="Modelo:">
          {showOllamaSelect ? (
            <div className="space-y-2">
              <Select
                aria-label="Modelo Ollama instalado"
                value={model}
                disabled={loading || ollamaLoading}
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
                <p className="text-[11px] text-muted">
                  {ollamaMessage || 'Modelos detectados en este PC (ollama list).'}
                </p>
                <button
                  type="button"
                  onClick={() => void refreshOllamaModels()}
                  disabled={loading || ollamaLoading}
                  className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-orange hover:underline disabled:opacity-50"
                >
                  {ollamaLoading ? 'Actualizando…' : 'Actualizar lista'}
                </button>
              </div>
            </div>
          ) : (
            <>
              <TextInput
                type="text"
                list={isOllama ? 'ollama-model-suggestions' : undefined}
                value={model}
                disabled={loading || ollamaLoading}
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
                          ? 'text-amber-600'
                          : 'text-muted'
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
                        disabled={loading || ollamaLoading}
                        className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-orange hover:underline disabled:opacity-50"
                      >
                        {ollamaLoading ? 'Actualizando…' : 'Actualizar lista'}
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
        <Field label="URL base del endpoint (compatible con OpenAI):">
          <TextInput
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://127.0.0.1:8080/v1"
          />
        </Field>
      )}

      {selected?.requires_key && (
        <Field label="API Key:">
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
        <p className="text-xs text-muted">
          Este modo no usa un modelo de IA: responde solo con las skills locales de UNEV.
        </p>
      )}

      {usesModel && (
        <div className="space-y-2 pt-1">
          <button
            type="button"
            onClick={onTest}
            disabled={testing || loading || !selected}
            // Pastilla naranja centrada, como "PROBAR CONEXIÓN" en el diseño.
            className={`mx-auto block rounded-[50px] bg-orange px-8 py-2.5 text-[12px] font-semibold uppercase text-white shadow-[0_1px_5px_rgba(0,0,0,0.25)] transition-opacity hover:opacity-90 disabled:opacity-40 ${
              testing ? 'animate-pulse' : ''
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
