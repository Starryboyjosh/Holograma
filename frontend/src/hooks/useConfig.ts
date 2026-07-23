import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/backend';
import type { SavedObject } from '../types';

// Settings state + backend load/save. The LLM section is a single authoritative
// provider (matching provider_config.py) instead of the old local/api split:
// `llmProvider` is one of the contract ids, `model`/`baseUrl` are plain fields,
// and `apiKey` is a write-only buffer ('' = leave the stored key untouched).
// Appearance/theme lives in ThemeContext; pass it through save() as an override.
export function useConfig() {
  const [llmProvider, setLlmProvider] = useState('openrouter');
  const [model, setModel] = useState('meta-llama/llama-3.3-70b-instruct');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [yoloInterval, setYoloInterval] = useState('1.0');
  const [yoloEnabled, setYoloEnabled] = useState(true);
  const [whisperSize, setWhisperSize] = useState('medium');
  const [groqApiKey, setGroqApiKey] = useState('');
  const [groqApiKeySet, setGroqApiKeySet] = useState(false);
  const [piperVoice, setPiperVoice] = useState('es_MX-claude-high.onnx');
  const [voicesList, setVoicesList] = useState<string[]>(['es_MX-claude-high.onnx']);
  const [savedTeachingObjects, setSavedTeachingObjects] = useState<SavedObject[]>([]);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await apiFetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        const provider = data.LLM_PROVIDER || 'openrouter';
        setLlmProvider(provider);
        // Each provider stores its model in a different field; show the right one.
        if (provider === 'ollama') {
          setModel(data.OLLAMA_MODEL || '');
        } else if (provider !== 'local_only') {
          setModel(data.LLM_MODEL || '');
        } else {
          setModel('');
        }
        setBaseUrl(data.OPENAI_COMPAT_BASE_URL || '');
        // Keys are never returned by the backend; keep the buffer empty.
        setApiKey('');
        setGroqApiKey('');
        setGroqApiKeySet(!!data.GROQ_API_KEY_SET);
        if (data.HOLOGRAM_CAMERA) setYoloEnabled(data.HOLOGRAM_CAMERA === '1');
        if (data.YOLO_INTERVAL_SECONDS) setYoloInterval(data.YOLO_INTERVAL_SECONDS);
        if (data.WHISPER_MODEL) setWhisperSize(data.WHISPER_MODEL);
        if (data.PIPER_VOICE) setPiperVoice(data.PIPER_VOICE);
      }

      const voicesRes = await apiFetch('/api/voices');
      if (voicesRes.ok) {
        const voicesData = await voicesRes.json();
        if (voicesData.voices) setVoicesList(voicesData.voices);
      }

      const metaRes = await apiFetch('/api/train/metadata');
      if (metaRes.ok) {
        const metaData = await metaRes.json();
        if (metaData.items) setSavedTeachingObjects(metaData.items);
      }
    } catch (err) {
      console.error('Error al obtener la configuración:', err);
    }
  }, []);

  useEffect(() => {
    // Carga inicial de la configuración desde el backend (sincronización con un
    // sistema externo). El setState ocurre tras el await, no de forma síncrona.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchConfig();
  }, [fetchConfig]);

  // Posts the non-LLM fields plus any overrides. The Settings screen builds the
  // LLM slice from provider metadata (see lib/providerForm) and passes it here,
  // so this hook stays unaware of per-provider env-var mapping.
  const save = useCallback(
    async (overrides: Record<string, string> = {}): Promise<boolean> => {
      try {
        // No forzar YOLO_MODEL aquí: el backend / config.json mandan
        // (default yoloe-26n-seg: personas + custom en un solo modelo).
        const payload: Record<string, string> = {
          HOLOGRAM_CAMERA: yoloEnabled ? '1' : '0',
          YOLO_INTERVAL_SECONDS: yoloInterval,
          WHISPER_MODEL: whisperSize,
          PIPER_VOICE: piperVoice,
          ...overrides,
        };

        const res = await apiFetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        return res.ok;
      } catch {
        return false;
      }
    },
    [yoloEnabled, yoloInterval, whisperSize, piperVoice],
  );

  return {
    llmProvider,
    setLlmProvider,
    model,
    setModel,
    apiKey,
    setApiKey,
    baseUrl,
    setBaseUrl,
    yoloInterval,
    setYoloInterval,
    yoloEnabled,
    setYoloEnabled,
    whisperSize,
    setWhisperSize,
    groqApiKey,
    setGroqApiKey,
    groqApiKeySet,
    piperVoice,
    setPiperVoice,
    voicesList,
    savedTeachingObjects,
    setSavedTeachingObjects,
    save,
  };
}
