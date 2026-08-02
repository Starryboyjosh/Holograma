import { useState } from 'react';
import { useToast } from '../context/ToastContext';
import { useChatSocket } from '../hooks/useChatSocket';
import { Orb } from '../components/Orb';
import { STATE_META } from '../theme';
import { WidgetFrame } from './WidgetFrame';

const SUGGESTIONS = [
  { l: 'Saludar', p: 'saludar' },
  { l: 'Carreras', p: '¿Qué carreras ofrece la UNEV?' },
  { l: 'Admisiones', p: '¿Cómo es el proceso de admisión?' },
];

// Detached conversation window. Holds its own WebSocket; the backend broadcasts
// to every connection so this stays in sync with the main window.
export function ChatWidget() {
  const showToast = useToast();
  const chat = useChatSocket({ onToast: showToast });
  const [draft, setDraft] = useState('');
  const meta = STATE_META[chat.assistantState];

  const send = () => {
    chat.sendPrompt(draft);
    setDraft('');
  };

  return (
    <WidgetFrame title="UNEV AI Assistant">
      <div className="flex items-center justify-end">
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold border ${meta.chip}`}>
          <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${meta.dot}`}></span>
          {meta.label}
        </span>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center text-center gap-3">
        <Orb state={chat.assistantState} onActivate={chat.requestServerListen} />
        <h2 className="text-lg font-normal leading-relaxed text-slate-100 max-w-sm">"{chat.aiSpokenText}"</h2>
        <p className="text-xs text-slate-400">{chat.userSpokenText}</p>
      </div>

      <div className="flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((c) => (
          <button
            key={c.l}
            onClick={() => chat.sendPrompt(c.p)}
            className="px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.04] hover:bg-white/[0.09] text-xs font-semibold text-slate-300 hover:text-white transition-all"
          >
            {c.l}
          </button>
        ))}
      </div>

      <div className="p-2 bg-slate-900/80 border border-white/10 rounded-2xl flex gap-2 shrink-0">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Escribe tu consulta..."
          className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#FF7208]"
          onKeyDown={(e) => {
            if (e.key === 'Enter') send();
          }}
        />
        <button onClick={send} className="px-4 py-2 bg-[#FF7208] hover:bg-orange-deep rounded-xl text-xs font-bold">
          Enviar
        </button>
      </div>
    </WidgetFrame>
  );
}
