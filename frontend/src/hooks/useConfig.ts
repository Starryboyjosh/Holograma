import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/backend';
import { API_KEY_FIELD_BY_PROVIDER } from '../types';
import type { SavedObject } from '../types';

// Settings state + backend load/save, lifted from App.tsx fetchConfig/saveConfig.
// Appearance/theme lives in ThemeContext; pass it through save() as an override.
export function useConfig() {
  const [aiEngine, setAiEngine] = useState<'local' | 'api'>('local');
  const [selectedLocalModel, setSelectedLocalModel] = useState('gemma3:1b');
  const [apiProvider, setApiProvider] = useState('openrouter');
  const [apiModel, setApiModel] = useState('meta-llama/llama-3.3-70b-instruct');
  const [apiKey, setApiKey] = useState('');
  const [yoloInterval, setYoloInterval] = useState('1.0');
  const [yoloEnabled, setYoloEnabled] = useState(true);
  const [whisperSize, setWhisperSize] = useState('medium');
  const [piperVoice, setPiperVoice] = useState('es_MX-claude-high.onnx');
  const [voicesList, setVoicesList] = useState<string[]>(['es_MX-claude-high.onnx']);
  const [savedTeachingObjects, setSavedTeachingObjects] = useState<SavedObject[]>([]);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await apiFetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        if (data.OLLAMA_MODEL) setSelectedLocalModel(data.OLLAMA_MODEL);
        if (data.LLM_PROVIDER) {
          setApiProvider(data.LLM_PROVIDER);
          setAiEngine(
            data.LLM_PROVIDER === 'ollama' || data.LLM_PROVIDER === 'local_only'
              ? 'local'
              : 'api',
          );
          const apiKeyField = API_KEY_FIELD_BY_PROVIDER[data.LLM_PROVIDER];
          if (apiKeyField && data[apiKeyField]) setApiKey(data[apiKeyField]);
        }
        if (data.LLM_MODEL) setApiModel(data.LLM_MODEL);
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

  const save = useCallback(
    async (overrides: Record<string, string> = {}): Promise<boolean> => {
      try {
        const payload: Record<string, string> = {
          OLLAMA_MODEL: aiEngine === 'local' ? selectedLocalModel : '',
          LLM_PROVIDER: aiEngine === 'local' ? 'ollama' : apiProvider,
          HOLOGRAM_CAMERA: yoloEnabled ? '1' : '0',
          YOLO_INTERVAL_SECONDS: yoloInterval,
          YOLO_MODEL: 'yolo26n.pt',
          WHISPER_MODEL: whisperSize,
          PIPER_VOICE: piperVoice,
          ...overrides,
        };

        if (aiEngine === 'api') {
          payload.LLM_MODEL = apiModel;
          const apiKeyField = API_KEY_FIELD_BY_PROVIDER[apiProvider];
          if (apiKeyField && apiKey.trim()) payload[apiKeyField] = apiKey.trim();
        }

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
    [aiEngine, selectedLocalModel, apiProvider, apiModel, apiKey, yoloEnabled, yoloInterval, whisperSize, piperVoice],
  );

  return {
    aiEngine,
    setAiEngine,
    selectedLocalModel,
    setSelectedLocalModel,
    apiProvider,
    setApiProvider,
    apiModel,
    setApiModel,
    apiKey,
    setApiKey,
    yoloInterval,
    setYoloInterval,
    yoloEnabled,
    setYoloEnabled,
    whisperSize,
    setWhisperSize,
    piperVoice,
    setPiperVoice,
    voicesList,
    savedTeachingObjects,
    setSavedTeachingObjects,
    save,
  };
}
