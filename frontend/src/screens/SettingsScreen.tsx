import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import { apiFetch } from "../lib/backend";
import { Card, SectionTitle } from "../components/ui/Card";
import { ToggleGroup } from "../components/ui/ToggleGroup";
import { Field, Select, TextInput } from "../components/ui/Field";
import { ProviderConfigCard } from "../components/ProviderConfigCard";
import { HologramConnection } from "../components/HologramConnection";
import { buildLlmConfigPayload } from "../lib/providerForm";
import { useProviders } from "../hooks/useProviders";
import type { AppearanceTheme } from "../context/ThemeContext";

export function SettingsScreen() {
  const navigate = useNavigate();
  const showToast = useToast();
  const { config, hologram } = useSession();
  const { appearance, setAppearance } = useTheme();
  const {
    providers,
    loading: providersLoading,
    testConnection,
    listOllamaModels,
  } = useProviders();
  const [playingSample, setPlayingSample] = useState(false);

  const playVoicePreview = async () => {
    setPlayingSample(true);
    try {
      await apiFetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: "Hola, esta es una prueba de voz para la universidad UNEV.",
          voice: config.piperVoice,
        }),
      });
    } catch {
      showToast("Error al reproducir la voz.");
    }
    setTimeout(() => setPlayingSample(false), 2500);
  };

  const onSave = async () => {
    const selected = providers.find((p) => p.id === config.llmProvider);
    const llmPayload = selected
      ? buildLlmConfigPayload(selected, {
          model: config.model,
          apiKey: config.apiKey,
          baseUrl: config.baseUrl,
        })
      : { LLM_PROVIDER: config.llmProvider };

    const extraPayload: Record<string, string> = {};
    if (config.groqApiKey.trim()) {
      extraPayload.GROQ_API_KEY = config.groqApiKey.trim();
    }

    const ok = await config.save({
      ...llmPayload,
      ...extraPayload,
      HOLOGRAM_MODE: appearance,
      HOLOGRAM_TCP_IP: hologram.holoIp.trim(),
      HOLOGRAM_TCP_PORT: String(hologram.holoPort),
    });
    if (ok) {
      showToast("Configuración aplicada con éxito.");
      navigate("/assistant");
    } else {
      showToast("Error al guardar la configuración.");
    }
  };

  return (
    <div className="w-full max-w-4xl space-y-6 py-4 text-slate-800 dark:text-slate-100">
      <div className="flex justify-between items-center pb-4 border-b border-gray-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-[#1C2D5A] dark:text-white">
            Configuración
          </h1>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Conecta el holograma y ajusta la IA, la voz y la visión.
          </p>
        </div>
      </div>

      <HologramConnection holo={hologram} />

      {/* AI brain (headline) — full width and driven by the live provider catalogue. */}
      <ProviderConfigCard
        llmProvider={config.llmProvider}
        setLlmProvider={config.setLlmProvider}
        model={config.model}
        setModel={config.setModel}
        apiKey={config.apiKey}
        setApiKey={config.setApiKey}
        baseUrl={config.baseUrl}
        setBaseUrl={config.setBaseUrl}
        providers={providers}
        loading={providersLoading}
        testConnection={testConnection}
        listOllamaModels={listOllamaModels}
        showToast={showToast}
      />

      <div className="columns-1 md:columns-2 gap-6 space-y-6 md:space-y-0 [column-fill:balance]">
        {/* Apariencia */}
        <Card masonry>
          <SectionTitle>Apariencia</SectionTitle>
          <ToggleGroup<AppearanceTheme>
            value={appearance}
            onChange={setAppearance}
            options={[
              { value: "light", label: "light" },
              { value: "dark", label: "dark" },
              { value: "system", label: "system" },
            ]}
          />
        </Card>

        {/* YOLO */}
        <Card masonry>
          <SectionTitle>Detección Visual YOLO</SectionTitle>
          <ToggleGroup
            value={config.yoloEnabled ? "on" : "off"}
            onChange={(v) => config.setYoloEnabled(v === "on")}
            options={[
              { value: "on", label: "Activo (ON)" },
              { value: "off", label: "Inactivo (OFF)" },
            ]}
          />
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">
                Intervalo de detección
              </span>
              <span className="font-extrabold text-[#E25C1D]">
                {config.yoloInterval} seg
              </span>
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
          <div className="space-y-4">
            <ToggleGroup
              value={config.whisperSize}
              onChange={config.setWhisperSize}
              options={[
                { value: "small", label: "small" },
                { value: "medium", label: "medium" },
                {
                  value: "whisper-large-v3-turbo",
                  label: "large-v3-turbo (cloud)",
                },
              ]}
            />
            {config.whisperSize === "whisper-large-v3-turbo" && (
              <div className="pt-2">
                <Field label="Groq API Key">
                  <TextInput
                    type="password"
                    autoComplete="off"
                    value={config.groqApiKey}
                    onChange={(e) => config.setGroqApiKey(e.target.value)}
                    placeholder={
                      config.groqApiKeySet
                        ? "Guardada — escribe una nueva para reemplazarla"
                        : "Pega la API key de Groq"
                    }
                  />
                </Field>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Piper */}
      <Card>
        <SectionTitle>Síntesis de Voz (Piper)</SectionTitle>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          <div className="flex-1">
            <Field label="Voz">
              <Select
                value={config.piperVoice}
                onChange={(e) => config.setPiperVoice(e.target.value)}
              >
                {config.voicesList.map((voice) => (
                  <option key={voice} value={voice}>
                    {voice}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <button
            onClick={playVoicePreview}
            className={`px-5 py-3.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shrink-0 self-end ${
              playingSample
                ? "bg-[#E25C1D]/20 text-[#E25C1D] border border-[#E25C1D]/50 animate-pulse"
                : "bg-gray-100 hover:bg-gray-200 border border-gray-200 text-gray-700 dark:bg-slate-900 dark:hover:bg-slate-800 dark:border-slate-800 dark:text-slate-300"
            }`}
          >
            Probar Voz
          </button>
        </div>
      </Card>

      <div className="pt-4 flex justify-end">
        <button
          onClick={onSave}
          disabled={providersLoading}
          className="w-full sm:w-auto px-8 py-4 bg-[#E25C1D] hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm rounded-2xl shadow-xl shadow-[#E25C1D]/10 transition-all text-center"
        >
          {providersLoading
            ? "Cargando proveedores…"
            : "Guardar y aplicar cambios"}
        </button>
      </div>
    </div>
  );
}
