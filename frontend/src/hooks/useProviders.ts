import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/backend';
import type {
  LlmTestInput,
  LlmTestResult,
  OllamaModelsResult,
  ProviderInfo,
} from '../types';

// Provider catalogue for the Settings picker, sourced from GET /api/providers
// (friendly labels/descriptions, configured state, base-url/discovery hints).
// Also exposes the non-persisting connection probe (POST /api/llm/test) and the
// live Ollama model list (GET /api/ollama/models ≈ `ollama list`).
export function useProviders() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await apiFetch('/api/providers');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.providers)) setProviders(data.providers as ProviderInfo[]);
      }
    } catch (err) {
      console.error('Error al obtener proveedores de IA:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Carga inicial del catálogo desde el backend (sistema externo): el setState
    // ocurre tras el await, no de forma síncrona.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  const testConnection = useCallback(
    async (input: LlmTestInput): Promise<LlmTestResult> => {
      try {
        const res = await apiFetch('/api/llm/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(input),
        });
        const data = await res.json();
        return {
          status: data.status === 'ok' ? 'ok' : 'error',
          message: data.message ?? 'Respuesta inesperada del servidor.',
        };
      } catch {
        return { status: 'error', message: 'No se pudo contactar al backend.' };
      }
    },
    [],
  );

  const listOllamaModels = useCallback(async (): Promise<OllamaModelsResult> => {
    try {
      const res = await apiFetch('/api/ollama/models');
      const data = await res.json();
      const models = Array.isArray(data.models)
        ? (data.models as unknown[]).filter((m): m is string => typeof m === 'string')
        : [];
      return {
        status: data.status === 'ok' ? 'ok' : 'error',
        models,
        message: typeof data.message === 'string' ? data.message : '',
      };
    } catch {
      return {
        status: 'error',
        models: [],
        message: 'No se pudo contactar al backend para listar modelos de Ollama.',
      };
    }
  }, []);

  return { providers, loading, refresh, testConnection, listOllamaModels };
}
