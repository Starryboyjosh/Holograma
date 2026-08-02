import { useState } from "react";
import { useSession } from "../context/SessionContext";
import { useToast } from "../context/ToastContext";
import { apiFetch } from "../lib/backend";
import { Card, SectionTitle } from "../components/ui/Card";
import { ToggleGroup } from "../components/ui/ToggleGroup";
import { Field, Select, TextInput } from "../components/ui/Field";
import { ProviderConfigCard } from "../components/ProviderConfigCard";
import { HologramConnection } from "../components/HologramConnection";
import { AdvancedHologramPanel } from "../components/hologram/AdvancedHologramPanel";
import { SurfaceProvider } from "../components/ui/SurfaceProvider";
import { ScreenHero } from "../components/holomind/ScreenHero";
import { StickyHeader } from "../components/holomind/StickyHeader";
import { buildLlmConfigPayload } from "../lib/providerForm";
import { useProviders } from "../hooks/useProviders";
import { BTN_PRIMARY } from "../theme";

/**
 * CONFIGURACIÓN (nodo 63:36).
 *
 * A diferencia de INICIO/HABLAR/ENTRENAR VISIÓN/INFO. UNEV (fusionadas en
 * `LandingScreen`), esta sigue siendo una ruta aparte — el diseño la trata como
 * un frame independiente, no como parte del recorrido de una sola página — así
 * que trae su propia `StickyHeader` en vez de compartir la de la landing.
 *
 * El diseño divide el resto de la pantalla en dos bloques: la conexión del
 * holograma sobre un degradado navy/gris propio de esta pantalla — no el mesh
 * naranja de Inicio, ver `backdrop="settings"` en `ScreenHero` — (tarjeta de
 * cristal, solo IP + puerto) y el "cerebro" sobre crema (tarjeta neutra:
 * proveedor, modelo, API key). Las tarjetas de YOLO, Whisper y Piper no están en
 * el diseño pero son funciones existentes; se conservan bajo el bloque crema con
 * los tokens nuevos.
 *
 * Rotación / Identidades / Promociones / unidades físicas por ventilador tampoco
 * están en el diseño (que solo pide un IP + puerto único) — van al repliegue
 * `AdvancedHologramPanel`, al final, antes del pie: ver ese componente para el
 * porqué no se eliminan.
 *
 * La tarjeta de "Apariencia" sí se eliminó: el diseño tiene un solo aspecto y el
 * tema claro/oscuro se retiró por completo.
 */
export function SettingsScreen() {
  const showToast = useToast();
  const { config, hologram } = useSession();
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

    // HOLOGRAM_MODE ya no se envía desde aquí: era la preferencia de tema, que se
    // retiró con el rediseño. La clave sigue existiendo en el backend (call.py la
    // lee con otro sentido), así que se deja intacta en vez de sobrescribirla.
    const ok = await config.save({
      ...llmPayload,
      ...extraPayload,
      HOLOGRAM_TCP_IP: hologram.holoIp.trim(),
      HOLOGRAM_TCP_PORT: String(hologram.holoPort),
    });
    if (ok) {
      // Ya no navega a /assistant: esa ruta no existe (HABLAR ahora es una
      // sección de la landing, no una pantalla aparte). Configuración se queda
      // en su propia ruta; el toast confirma el guardado.
      showToast("Configuración aplicada con éxito.");
    } else {
      showToast("Error al guardar la configuración.");
    }
  };

  return (
    <>
      <StickyHeader tone="light" />

      {/* ---- Bloque 1: conexión del holograma sobre el degradado propio (nodo 63:36) ----
           El diseño la presenta como un solo IP + puerto TCP; el detalle por
           ventilador (top/center/bottom, cada uno con su propia IP porque el
           router MISSYOU los distingue por dirección, no por puerto) vive en el
           repliegue de más abajo, no aquí.
           `SurfaceProvider tone="glass"` hace que las tarjetas y campos anidados
           adopten la variante de cristal, que es lo que pide el diseño aquí. */}
      <ScreenHero backdrop="settings" bleedTop className="pb-28">
        <div className="mx-auto w-full max-w-5xl px-6">
          <h1 className="text-center text-[32px] font-normal italic text-white md:text-[44px]">
            Configuración
          </h1>
          <SurfaceProvider tone="glass">
            <div className="mt-8 space-y-6">
              <HologramConnection holo={hologram} />
            </div>
          </SurfaceProvider>
        </div>
      </ScreenHero>

      {/* ---- Bloque 2: el resto, sobre crema ---- */}
      <div className="mx-auto w-full max-w-5xl px-6 pb-16 pt-16">
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

        <div className="mt-8 columns-1 gap-6 space-y-6 md:columns-2 md:space-y-0 [column-fill:balance]">
          {/* YOLO */}
          <Card masonry>
            <SectionTitle>Detección visual YOLO</SectionTitle>
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
                <span className="text-[12px] font-semibold text-muted">
                  Intervalo de detección
                </span>
                <span className="font-bold text-orange">{config.yoloInterval} seg</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="5.0"
                step="0.1"
                value={config.yoloInterval}
                onChange={(e) => config.setYoloInterval(e.target.value)}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-black/10 accent-orange"
              />
            </div>
          </Card>

          {/* Whisper */}
          <Card masonry>
            <SectionTitle>Transcripción de voz (Whisper)</SectionTitle>
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
        <Card className="mt-8">
          <SectionTitle>Síntesis de voz (Piper)</SectionTitle>
          <div className="flex flex-col items-stretch gap-4 sm:flex-row sm:items-end">
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
              className={`${BTN_PRIMARY} shrink-0 ${playingSample ? "animate-pulse" : ""}`}
            >
              Probar voz
            </button>
          </div>
        </Card>

        <div className="flex justify-end pt-8">
          <button
            onClick={onSave}
            disabled={providersLoading}
            className={`${BTN_PRIMARY} w-full py-4 sm:w-auto`}
          >
            {providersLoading
              ? "Cargando proveedores…"
              : "Guardar y aplicar cambios"}
          </button>
        </div>

        {/* Rotación / Identidades / Promociones / unidades por ventilador — ver
            AdvancedHologramPanel para el porqué se repliegan en vez de
            eliminarse. Va al final, antes del pie (HolomindFooter, en AppShell). */}
        <AdvancedHologramPanel />
      </div>
    </>
  );
}
