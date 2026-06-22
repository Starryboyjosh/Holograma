import { useState } from 'react';
import { useSession } from '../context/SessionContext';
import { useToast } from '../context/ToastContext';
import { Orb } from '../components/Orb';
import { CameraFeed } from '../components/CameraFeed';
import { DetachButton } from '../components/DetachButton';
import { STATE_META } from '../theme';
import type { VoiceMode } from '../theme';

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
          <span key={i} className="text-[#E25C1D] font-semibold underline decoration-orange-500/30 underline-offset-4">
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

export function AssistantScreen() {
  const showToast = useToast();
  const { chat, config, camera } = useSession();
  const [textInputOpen, setTextInputOpen] = useState(false);
  const [customQuery, setCustomQuery] = useState('');

  const stateMeta = STATE_META[chat.assistantState];

  let orbHint = 'Toca el círculo para hablar';
  if (chat.assistantState === 'listening') orbHint = 'Te escucho… habla ahora';
  else if (chat.assistantState === 'thinking') orbHint = 'Estoy pensando…';
  else if (chat.assistantState === 'speaking') orbHint = 'Estoy respondiendo…';
  else if (chat.voiceMode === 'presentation') orbHint = 'Modo presentación: respondo cuando veo gente';

  const submitCustom = () => {
    chat.sendPrompt(customQuery);
    setCustomQuery('');
    setTextInputOpen(false);
  };

  const endConversation = () => {
    chat.setAssistantState('idle');
    showToast('Conversación de voz finalizada.');
  };

  const voiceModes: { value: VoiceMode; label: string }[] = [
    { value: 'ptt', label: '🎙️ Toca para hablar' },
    { value: 'presentation', label: '👥 Presentación' },
  ];

  return (
    <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-5 animate-fade-in">
      {/* CONVERSACIÓN */}
      <div className="lg:col-span-7 rounded-3xl p-6 md:p-8 relative min-h-[560px] flex flex-col bg-[#0B0F19]/80 backdrop-blur-xl border border-white/10 shadow-2xl text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#E25C1D]"></span>
            <span className="text-[#E25C1D] font-bold text-sm tracking-wide">UNEV AI Assistant</span>
          </div>
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold border ${stateMeta.chip}`}>
            <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${stateMeta.dot}`}></span>
            {stateMeta.label}
          </span>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center text-center py-4">
          <Orb state={chat.assistantState} onActivate={chat.requestServerListen} />

          <p className="text-xl md:text-2xl font-bold text-slate-100 mb-1">{orbHint}</p>

          <div className="inline-flex items-center gap-1 p-1 mt-2 mb-5 rounded-full bg-black/30 border border-white/10">
            {voiceModes.map((m) => (
              <button
                key={m.value}
                type="button"
                onClick={() => chat.setVoiceModeRemote(m.value)}
                className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  chat.voiceMode === m.value ? 'bg-[#E25C1D] text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          <h2 className="text-xl md:text-2xl font-normal leading-relaxed text-slate-100 tracking-wide max-w-xl">
            {highlighted(chat.aiSpokenText, chat.highlightKeyword)}
          </h2>
          <div className="flex items-center justify-center gap-2 text-xs text-slate-400 font-medium mt-4">
            {chat.assistantState === 'thinking' && (
              <svg className="w-4 h-4 text-[#E25C1D] animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            )}
            <span>{chat.userSpokenText}</span>
          </div>
        </div>

        {textInputOpen && (
          <div className="mb-3 w-full max-w-md mx-auto p-2 bg-slate-900/80 border border-white/10 rounded-2xl flex gap-2">
            <input
              type="text"
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              placeholder="Escribe tu consulta al holograma..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#E25C1D]"
              onKeyDown={(e) => {
                if (e.key === 'Enter') submitCustom();
              }}
            />
            <button onClick={submitCustom} className="px-4 py-2 bg-[#E25C1D] hover:bg-orange-600 rounded-xl text-xs font-bold">
              Enviar
            </button>
          </div>
        )}

        <div className="flex flex-wrap justify-center items-center gap-2">
          {SUGGESTIONS.map((c) => (
            <button
              key={c.l}
              onClick={() => chat.sendPrompt(c.p)}
              className="px-4 py-2 rounded-full border border-white/10 bg-white/[0.04] hover:bg-white/[0.09] hover:border-[#E25C1D]/40 text-xs font-semibold text-slate-300 hover:text-white transition-all"
            >
              {c.l}
            </button>
          ))}
        </div>

        <div className="flex justify-center items-center mt-5">
          <div className="flex items-center gap-6 px-6 py-3 bg-black/30 border border-white/10 rounded-full shadow-xl">
            <button
              onClick={() => setTextInputOpen((v) => !v)}
              className={`p-2 rounded-full transition-all ${
                textInputOpen ? 'text-[#E25C1D] bg-[#E25C1D]/10' : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
              title="Escribir comando"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"
                />
              </svg>
            </button>

            <button
              onClick={endConversation}
              className="p-3.5 bg-rose-600 hover:bg-rose-700 text-white rounded-full transition-all shadow-md active:scale-95 flex items-center justify-center"
              title="Detener sesión de voz"
            >
              <div className="w-3 h-3 bg-rose-200 rounded-[3px]"></div>
            </button>

            <button
              onClick={() => {
                camera.toggleCamera();
                showToast(camera.cameraOn ? 'Cámara apagada.' : 'Cámara encendida.');
              }}
              className={`p-2 rounded-full transition-all ${
                camera.cameraOn ? 'text-[#E25C1D] bg-[#E25C1D]/10' : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
              title="Visor de cámara"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"
                />
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* CÁMARA YOLO */}
      <div className="lg:col-span-5 rounded-3xl p-5 flex flex-col bg-[#0B0F19]/80 backdrop-blur-xl border border-white/10 shadow-2xl">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold tracking-wider text-slate-300">VISIÓN EN VIVO</span>
          <DetachButton widget="camera" />
        </div>
        <CameraFeed
          enabled={config.yoloEnabled && camera.cameraOn}
          nonce={camera.feedNonce}
          showBadge={false}
          offLabel="Cámara apagada"
          className="flex-1 min-h-[300px] rounded-2xl border border-slate-800"
        />
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${chat.personCount > 0 ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`}></span>
            <span className="text-sm font-semibold text-slate-200">
              {chat.personCount > 0
                ? `${chat.personCount} persona${chat.personCount > 1 ? 's' : ''} frente a mí`
                : 'Sin personas a la vista'}
            </span>
          </div>
          <button
            onClick={() => {
              camera.toggleCamera();
              showToast(camera.cameraOn ? 'Cámara apagada.' : 'Cámara encendida.');
            }}
            className="text-[11px] font-bold px-3 py-1.5 rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 transition-all"
          >
            {camera.cameraOn ? 'Apagar cámara' : 'Encender cámara'}
          </button>
        </div>
      </div>
    </div>
  );
}
