import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/backend';
import type { LlmTestInput, LlmTestResult, ProviderInfo } from '../types';

// Provider catalogue for the Settings picker, sourced from GET /api/providers
// (friendly labels/descriptions, configured state, base-url/discovery hints).
// Also exposes the non-persisting connection probe (POST /api/llm/test).
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

  return { providers, loading, refresh, testConnection };
}
