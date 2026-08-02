import { useState } from 'react';
import { useSession } from '../../context/SessionContext';
import { useToast } from '../../context/ToastContext';
import { Orb } from '../../components/Orb';
import { CameraFeed } from '../../components/CameraFeed';
import { DetachButton } from '../../components/DetachButton';
import { ScreenHero } from '../../components/holomind/ScreenHero';
import { Wordmark } from '../../components/holomind/Wordmark';
import { BTN_PRIMARY, CARD, CHIP, STATE_META } from '../../theme';
import type { VoiceMode } from '../../theme';
import writingIcon from '../../assets/holomind/icon-writing.webp';
import cameraIcon from '../../assets/holomind/icon-camera.webp';

const SUGGESTIONS = [
  { l: 'Saludar', p: 'saludar' },
  { l: 'Carreras', p: '¿Qué carreras ofrece la UNEV?' },
  { l: 'Admisiones', p: '¿Cómo es el proceso de admisión?' },
  { l: 'Ayuda', p: 'ayuda' },
];

function highlighted(text: string, highlight: string) {
  if (!highlight) return `"${text}"`;
  const parts = text.split(new RegExp(`(${highlight})`, 'gi'));
  return (
    <span>
      "
      {parts.map((part, i) =>
        part.toLowerCase() === highlight.toLowerCase() ? (
          <span
            key={i}
            className="font-semibold text-orange underline decoration-orange/30 underline-offset-4"
          >
            {part}
          </span>
        ) : (
          part
        ),
      )}
      "
    </span>
  );
}

/** Botón circular de la barra inferior (nodos 30:1861 / 53:580 / 53:581). */
function RoundAction({
  onClick,
  active = false,
  title,
  icon,
}: {
  onClick: () => void;
  active?: boolean;
  title: string;
  icon: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      aria-pressed={active}
      className={`flex h-[30px] w-[30px] items-center justify-center transition-opacity hover:opacity-100 ${
        active ? 'opacity-100' : 'opacity-60'
      }`}
    >
      <img src={icon} alt="" draggable={false} className="h-full w-full object-contain" />
    </button>
  );
}

/**
 * HABLAR (nodo 30:1729).
 *
 * En la landing de una sola página esta es una sección más, ancladas por
 * `ScreenHero id="hablar"` — la cabecera compartida vive en `StickyHeader`, no
 * aquí.
 *
 * Las sugerencias rápidas y el campo de texto no aparecen en el diseño pero ya
 * existían y son funcionales; se conservan con el lenguaje visual nuevo en vez de
 * eliminar funciones que nadie pidió quitar.
 */
export function HablarSection() {
  const showToast = useToast();
  const { chat, config, camera } = useSession();
  const [textInputOpen, setTextInputOpen] = useState(false);
  const [customQuery, setCustomQuery] = useState('');

  const stateMeta = STATE_META[chat.assistantState];

  let orbHint = 'Toca el círculo para hablar';
  if (chat.assistantState === 'listening') orbHint = 'Te escucho… habla ahora';
  else if (chat.assistantState === 'thinking') orbHint = 'Estoy pensando…';
  else if (chat.assistantState === 'speaking') orbHint = 'Estoy respondiendo…';
  else if (chat.voiceMode === 'presentation') orbHint = 'Respondo cuando veo gente';

  const submitCustom = () => {
    chat.sendPrompt(customQuery);
    setCustomQuery('');
    setTextInputOpen(false);
  };

  const endConversation = () => {
    chat.setAssistantState('idle');
    showToast('Conversación de voz finalizada.');
  };

  const toggleCamera = () => {
    camera.toggleCamera();
    showToast(camera.cameraOn ? 'Cámara apagada.' : 'Cámara encendida.');
  };

  const voiceModes: { value: VoiceMode; label: string }[] = [
    { value: 'ptt', label: 'Toca para hablar' },
    { value: 'presentation', label: 'Presentación' },
  ];

  return (
    <ScreenHero id="hablar" backdrop="cream">
      <div className="mx-auto w-full max-w-6xl px-6 pb-16">
        <h1 className="text-center text-[32px] font-normal text-ink md:text-[48px]">
          Habla con <Wordmark onCream>HoloMind</Wordmark>
        </h1>

        <div className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* ---------------- INTERACTÚA CON EL ASISTENTE ---------------- */}
          <div className={`${CARD} flex flex-col p-8 lg:col-span-7`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-[16px] font-semibold uppercase text-ink">
                Interactúa con el asistente
              </h2>
              <span className={CHIP}>
                <span className={`h-2 w-2 rounded-full ${stateMeta.dot}`} />
                {stateMeta.label}
              </span>
            </div>

            <div className="flex flex-1 flex-col items-center justify-center py-8 text-center">
              <Orb state={chat.assistantState} onActivate={chat.requestServerListen} />

              {/* Selector de modo de voz (nodo 38:26). */}
              <div className="mt-8 inline-flex items-center rounded-[50px] bg-black/5 p-1">
                {voiceModes.map((m) => (
                  <button
                    key={m.value}
                    type="button"
                    onClick={() => chat.setVoiceModeRemote(m.value)}
                    className={`rounded-[50px] px-6 py-2 text-[12px] font-semibold uppercase transition-colors ${
                      chat.voiceMode === m.value
                        ? 'bg-orange text-cream'
                        : 'text-ink hover:text-orange'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              <p className="mt-6 text-[18px] font-semibold text-ink">{orbHint}</p>
              <div
                className="mt-1 text-[14px] font-normal text-ink"
                aria-live="polite"
              >
                {highlighted(chat.aiSpokenText, chat.highlightKeyword)}
              </div>

              {chat.userSpokenText && (
                <p className="mt-3 text-[12px] text-muted">{chat.userSpokenText}</p>
              )}

              {/* Sugerencias rápidas — función preexistente, no está en el diseño. */}
              <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
                {SUGGESTIONS.map((c) => (
                  <button
                    key={c.l}
                    onClick={() => chat.sendPrompt(c.p)}
                    className="rounded-[50px] bg-black/5 px-4 py-2 text-[12px] font-semibold text-ink transition-colors hover:bg-orange hover:text-white"
                  >
                    {c.l}
                  </button>
                ))}
              </div>

              {textInputOpen && (
                <div className="mt-4 flex w-full max-w-md gap-2">
                  <input
                    type="text"
                    value={customQuery}
                    onChange={(e) => setCustomQuery(e.target.value)}
                    placeholder="Escribe tu consulta al holograma…"
                    className="flex-1 rounded-[50px] bg-black/5 px-5 py-3 text-[14px] text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-orange/50"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') submitCustom();
                    }}
                  />
                  <button onClick={submitCustom} className={BTN_PRIMARY}>
                    Enviar
                  </button>
                </div>
              )}
            </div>

            {/* Barra de acciones: escribir · detener · cámara (nodo 30:1861). */}
            <div className="flex justify-center">
              <div className="inline-flex items-center gap-8 rounded-[50px] bg-[rgba(210,204,202,0.35)] px-8 py-3 shadow-[0_1px_5px_rgba(0,0,0,0.25)]">
                <RoundAction
                  onClick={() => setTextInputOpen((v) => !v)}
                  active={textInputOpen}
                  title="Escribir comando"
                  icon={writingIcon}
                />
                <button
                  type="button"
                  onClick={endConversation}
                  title="Detener sesión de voz"
                  aria-label="Detener sesión de voz"
                  className="flex h-[51px] w-[51px] items-center justify-center rounded-full bg-[#E03B33] shadow-md transition-transform active:scale-95"
                >
                  <span className="h-[13px] w-[13px] rounded-[2px] bg-cream" />
                </button>
                <RoundAction
                  onClick={toggleCamera}
                  active={camera.cameraOn}
                  title="Visor de cámara"
                  icon={cameraIcon}
                />
              </div>
            </div>
          </div>

          {/* ---------------------- VIDEO EN VIVO ---------------------- */}
          <div className={`${CARD} flex flex-col p-8 lg:col-span-5`}>
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-[16px] font-semibold uppercase text-ink">
                <span
                  className={`h-2 w-2 rounded-full ${
                    camera.cameraOn ? 'bg-emerald-500' : 'bg-muted'
                  }`}
                />
                Video en vivo
              </h2>
              <DetachButton widget="camera" />
            </div>

            <CameraFeed
              enabled={config.yoloEnabled && camera.cameraOn}
              nonce={camera.feedNonce}
              showBadge={false}
              offLabel="Cámara apagada"
              className="mt-6 min-h-[300px] flex-1 rounded-[30px] bg-black/5"
            />

            <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
              <span className="text-[14px] font-semibold text-ink">
                {chat.personCount > 0
                  ? `${chat.personCount} persona${chat.personCount > 1 ? 's' : ''} frente a mí`
                  : 'Sin personas a la vista'}
              </span>
              <button onClick={toggleCamera} className={BTN_PRIMARY}>
                {camera.cameraOn ? 'Apagar cámara' : 'Encender cámara'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </ScreenHero>
  );
}
