import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/backend';

export interface UnevProgram {
  name: string;
  desc: string;
}

export interface SaveResult {
  ok: boolean;
  message?: string;
}

// Loads + saves the single authoritative UNEV content (GET/POST /api/unev-content).
// Text fields are kept as a flat record; programs as an editable name/desc list.
export function useUnevContent() {
  const [fields, setFields] = useState<Record<string, string>>({});
  const [programs, setPrograms] = useState<UnevProgram[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch('/api/unev-content');
      if (res.ok) {
        const data = await res.json();
        const content = (data.content ?? {}) as Record<string, unknown>;
        const { programs: progs = {}, ...text } = content;
        setFields(text as Record<string, string>);
        setPrograms(
          Object.entries(progs as Record<string, string>).map(([name, desc]) => ({
            name,
            desc: String(desc),
          })),
        );
      }
    } catch (err) {
      console.error('Error al cargar el contenido de UNEV:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Carga inicial desde el backend (sistema externo); setState tras el await.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const setField = useCallback((key: string, value: string) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  }, []);

  const addProgram = useCallback(() => {
    setPrograms((prev) => [...prev, { name: '', desc: '' }]);
  }, []);

  const updateProgram = useCallback((index: number, patch: Partial<UnevProgram>) => {
    setPrograms((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }, []);

  const removeProgram = useCallback((index: number) => {
    setPrograms((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const save = useCallback(async (): Promise<SaveResult> => {
    setSaving(true);
    try {
      const programsObj: Record<string, string> = {};
      for (const p of programs) {
        const name = p.name.trim();
        if (name) programsObj[name] = p.desc;
      }
      const res = await apiFetch('/api/unev-content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...fields, programs: programsObj }),
      });
      const data = await res.json().catch(() => ({}));
      return { ok: res.ok && data.status === 'ok', message: data.message };
    } catch {
      return { ok: false, message: 'No se pudo contactar al backend.' };
    } finally {
      setSaving(false);
    }
  }, [fields, programs]);

  return {
    fields,
    setField,
    programs,
    addProgram,
    updateProgram,
    removeProgram,
    loading,
    saving,
    save,
    reload: load,
  };
}
