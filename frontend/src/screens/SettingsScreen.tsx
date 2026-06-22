import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';
import { apiFetch } from '../lib/backend';
import { Card, SectionTitle } from '../components/ui/Card';
import { ToggleGroup } from '../components/ui/ToggleGroup';
import { Field, Select, TextInput } from '../components/ui/Field';
import { DEFAULT_API_MODEL_BY_PROVIDER } from '../types';
import type { AppearanceTheme } from '../context/ThemeContext';

export function SettingsScreen() {
  const navigate = useNavigate();
  const showToast = useToast();
  const { config } = useSession();
  const { appearance, setAppearance } = useTheme();
  const [playingSample, setPlayingSample] = useState(false);

  const playVoicePreview = async () => {
    setPlayingSample(true);
    try {
      await apiFetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: 'Hola, esta es una prueba de voz para la universidad UNEV.',
          voice: config.piperVoice,
        }),
      });
    } catch {
      showToast('Error al reproducir la voz.');
    }
    setTimeout(() => setPlayingSample(false), 2500);
  };

  const onSave = async () => {
    const ok = await config.save({ HOLOGRAM_MODE: appearance });
    if (ok) {
      showToast('Configuración aplicada con éxito.');
      navigate('/');
    } else {
      showToast('Error al guardar la configuración.');
    }
  };

  return (
    <div className="w-full max-w-4xl space-y-6 py-4 text-slate-800 dark:text-slate-100">
      <div className="flex justify-between items-center pb-4 border-b border-gray-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-[#1C2D5A] dark:text-white">Portal de Configuración</h1>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Establece preferencias del Cerebro de la IA y el hardware
          </p>
        </div>
      </div>

      <div className="columns-1 md:columns-2 gap-6 space-y-6 md:space-y-0 [column-fill:balance]">
        {/* Apariencia */}
        <Card masonry>
          <SectionTitle>Apariencia</SectionTitle>
          <ToggleGroup<AppearanceTheme>
            value={appearance}
            onChange={setAppearance}
            options={[
              { value: 'light', label: 'light' },
              { value: 'dark', label: 'dark' },
              { value: 'system', label: 'system' },
            ]}
          />
        </Card>

        {/* Cerebro de la IA */}
        <Card masonry>
          <SectionTitle>Modelo del Cerebro</SectionTitle>
          <ToggleGroup
            value={config.aiEngine}
            onChange={config.setAiEngine}
            options={[
              { value: 'local', label: 'Local (Ollama)' },
              { value: 'api', label: 'API Key' },
            ]}
          />

          {config.aiEngine === 'local' ? (
            <div className="pt-2">
              <Field label="Seleccionar Modelo Ollama">
                <Select value={config.selectedLocalModel} onChange={(e) => config.setSelectedLocalModel(e.target.value)}>
                  <option value="gemma3:1b">Gemma 3 1B - Fallback rápido</option>
                  <option value="gemma4:e4b">Gemma 4 E4B - Balance local</option>
                  <option value="qwen3:8b">Qwen 3:8B - Razonamiento avanzado</option>
                  <option value="llama3.2:3b">Llama 3.2 3b - Optimizado</option>
                </Select>
              </Field>
            </div>
          ) : (
            <div className="space-y-3 pt-2">
              <Field label="Proveedor API">
                <Select
                  value={config.apiProvider}
                  onChange={(e) => {
                    const next = e.target.value;
                    config.setApiProvider(next);
                    config.setApiModel(DEFAULT_API_MODEL_BY_PROVIDER[next] || config.apiModel);
                    config.setApiKey('');
                  }}
                >
                  <option value="openrouter">OpenRouter</option>
                  <option value="openai">OpenAI</option>
                  <option value="claude_native">Anthropic (Claude)</option>
                  <option value="nvidia">NVIDIA NIM</option>
                </Select>
              </Field>
              <Field label="Modelo Remoto">
                <TextInput
                  type="text"
                  value={config.apiModel}
                  onChange={(e) => config.setApiModel(e.target.value)}
                  placeholder="meta-llama/llama-3.3-70b-instruct"
                />
              </Field>
              <Field label="API Key">
                <TextInput
                  type="password"
                  value={config.apiKey}
                  onChange={(e) => config.setApiKey(e.target.value)}
                  placeholder="••••••••••••••••"
                />
              </Field>
            </div>
          )}
        </Card>

        {/* YOLO */}
        <Card masonry>
          <SectionTitle>Detección Visual YOLO</SectionTitle>
          <ToggleGroup
            value={config.yoloEnabled ? 'on' : 'off'}
            onChange={(v) => config.setYoloEnabled(v === 'on')}
            options={[
              { value: 'on', label: 'Activo (ON)' },
              { value: 'off', label: 'Inactivo (OFF)' },
            ]}
          />
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">Intervalo de detección</span>
              <span className="font-extrabold text-[#E25C1D]">{config.yoloInterval} seg</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="5.0"
              step="0.1"
              value={config.yoloInterval}
              onChange={(e) => config.setYoloInterval(e.target.value)}
              className="w-full h-1.5 bg-gray-200 dark:bg-slate-900 rounded-lg appearance-none cursor-pointer accent-[#E25C1D]"
            />
          </div>
        </Card>

        {/* Whisper */}
        <Card masonry>
          <SectionTitle>Transcripción de Voz (Whisper)</SectionTitle>
          <ToggleGroup
            value={config.whisperSize}
            onChange={config.setWhisperSize}
            options={[
              { value: 'small', label: 'small' },
              { value: 'medium', label: 'medium' },
            ]}
          />
        </Card>
      </div>

      {/* Piper */}
      <Card>
        <SectionTitle>Síntesis de Voz (Piper)</SectionTitle>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          <div className="flex-1">
            <Select value={config.piperVoice} onChange={(e) => config.setPiperVoice(e.target.value)}>
              {config.voicesList.map((voice) => (
                <option key={voice} value={voice}>
                  {voice}
                </option>
              ))}
            </Select>
          </div>
          <button
            onClick={playVoicePreview}
            className={`px-5 py-3.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shrink-0 ${
              playingSample
                ? 'bg-[#E25C1D]/20 text-[#E25C1D] border border-[#E25C1D]/50 animate-pulse'
                : 'bg-gray-100 hover:bg-gray-200 border border-gray-200 text-gray-700 dark:bg-slate-900 dark:hover:bg-slate-800 dark:border-slate-800 dark:text-slate-300'
            }`}
          >
            Probar Voz
          </button>
        </div>
      </Card>

      <div className="pt-4 flex justify-end">
        <button
          onClick={onSave}
          className="w-full sm:w-auto px-8 py-4 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-sm rounded-2xl shadow-xl shadow-[#E25C1D]/10 transition-all text-center"
        >
          Guardar y aplicar cambios
        </button>
      </div>
    </div>
  );
}
