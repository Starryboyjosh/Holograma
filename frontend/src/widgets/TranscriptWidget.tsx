import { useToast } from '../context/ToastContext';
import { useChatSocket } from '../hooks/useChatSocket';
import { STATE_META } from '../theme';
import { WidgetFrame } from './WidgetFrame';

// Read-only transcript window: streams what the visitor said and what the
// assistant is answering. Useful as a caption monitor on a vertical screen.
export function TranscriptWidget() {
  const showToast = useToast();
  const chat = useChatSocket({ onToast: showToast });
  const meta = STATE_META[chat.assistantState];

  return (
    <WidgetFrame title="Transcripción en vivo">
      <span className={`inline-flex self-start items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold border ${meta.chip}`}>
        <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${meta.dot}`}></span>
        {meta.label}
      </span>

      <div className="flex-1 flex flex-col justify-center gap-6 py-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Visitante</p>
          <p className="text-base text-slate-300">{chat.userSpokenText}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[#FF7208] font-bold mb-1">Holograma</p>
          <p className="text-xl leading-relaxed text-slate-100">"{chat.aiSpokenText}"</p>
        </div>
      </div>
    </WidgetFrame>
  );
}
