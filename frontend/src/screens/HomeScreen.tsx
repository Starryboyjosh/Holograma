import { useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';

const CAPABILITIES = [
  { t: 'Conversación natural', d: 'Voz y texto en español' },
  { t: 'Visión en vivo', d: 'Detección de personas con YOLO' },
  { t: 'Información UNEV', d: 'Carreras, admisiones y más' },
];

export function HomeScreen() {
  const navigate = useNavigate();
  const { chat, config, camera } = useSession();

  const startConversation = () => {
    navigate('/assistant');
    chat.setAssistantState('listening');
    chat.sendPrompt('saludar');
    // Tras el saludo, pide una escucha al micrófono del servidor (Whisper).
    setTimeout(chat.requestServerListen, 1200);
  };

  const startWithCamera = () => {
    navigate('/assistant');
    camera.setCameraOn(true);
    chat.setAssistantState('listening');
    chat.sendPrompt('saludar');
  };

  return (
    <div className="w-full max-w-3xl mx-auto py-6 animate-fade-in">
      <div className="relative overflow-hidden rounded-[2rem] px-6 py-12 md:px-12 md:py-14 text-center border shadow-2xl border-gray-200 bg-white shadow-gray-300/40 dark:border-white/10 dark:bg-white/[0.03] dark:backdrop-blur-xl dark:shadow-black/40">
        <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 w-72 h-72 rounded-full bg-[#E25C1D] opacity-20 blur-3xl"></div>

        {/* Estado real */}
        <div className="relative flex items-center justify-center gap-2 mb-9">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold border ${
              chat.wsConnected
                ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                : 'text-amber-400 border-amber-500/30 bg-amber-500/10'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${chat.wsConnected ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
            {chat.wsConnected ? 'Holograma en línea' : 'Reconectando...'}
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold border text-[#1C2D5A] border-gray-200 bg-gray-100 dark:text-slate-300 dark:border-slate-700 dark:bg-slate-800/40">
            <span className={`w-1.5 h-1.5 rounded-full ${config.yoloEnabled ? 'bg-[#E25C1D]' : 'bg-slate-500'}`}></span>
            Visión YOLO {config.yoloEnabled ? 'activa' : 'inactiva'}
          </span>
        </div>

        {/* Orbe decorativo */}
        <div className="relative flex justify-center items-center h-44 mb-8">
          <div className="absolute w-44 h-44 rounded-full bg-[#E25C1D] opacity-15 blur-3xl animate-pulse"></div>
          <div className="absolute w-40 h-40 rounded-full border border-[#E25C1D]/20 spin-slow"></div>
          <div className="absolute w-32 h-32 rounded-full border-2 border-dashed border-[#1C2D5A]/40 organic-orb"></div>
          <div className="relative w-24 h-24 rounded-full bg-gradient-to-tr from-[#E25C1D] to-orange-400 flex items-center justify-center shadow-xl shadow-[#E25C1D]/30">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
        </div>

        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight leading-tight text-[#1C2D5A] dark:text-slate-50">
          Asistente de <span className="text-[#E25C1D]">IA de la UNEV</span>
        </h1>
        <p className="mt-4 text-base md:text-lg font-medium max-w-xl mx-auto text-[#5B6B6B] dark:text-slate-300/90">
          Háblame o escríbeme. Te veo en tiempo real y respondo sobre carreras, admisiones y la vida universitaria.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={startConversation}
            className="w-full sm:w-auto px-10 py-5 bg-[#E25C1D] hover:bg-orange-600 active:scale-95 text-white text-lg font-bold rounded-2xl shadow-xl shadow-[#E25C1D]/25 transition-all"
          >
            Comenzar a hablar
          </button>
          <button
            onClick={startWithCamera}
            className="w-full sm:w-auto px-10 py-5 border font-bold text-lg rounded-2xl transition-all border-[#E25C1D] hover:bg-orange-500/5 text-[#E25C1D] dark:border-white/15 dark:bg-white/[0.04] dark:hover:bg-white/[0.08] dark:text-slate-100"
          >
            Usar la cámara
          </button>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
        {CAPABILITIES.map((f) => (
          <div key={f.t} className="rounded-2xl border px-4 py-4 text-left border-gray-200 bg-white dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-sm font-bold text-[#1C2D5A] dark:text-slate-100">{f.t}</p>
            <p className="text-xs mt-0.5 text-gray-500 dark:text-slate-400">{f.d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
