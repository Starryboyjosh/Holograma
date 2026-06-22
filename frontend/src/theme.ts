// UNEV design tokens + shared class fragments. Theme switching uses Tailwind's
// `dark:` variant (a `.dark` class on <html>) instead of JS ternaries, so most
// components write `bg-white dark:bg-[#131E3B]` once instead of duplicating
// every conditional string.

export const COLORS = {
  navy: '#1C2D5A',
  orange: '#E25C1D',
  navyPanel: '#131E3B',
  bgDark: '#070A12',
  panelDark: '#0B0F19',
} as const;

export type AssistantState = 'idle' | 'listening' | 'thinking' | 'speaking';
export type VoiceMode = 'ptt' | 'presentation' | 'auto';

export const STATE_META: Record<
  AssistantState,
  { label: string; chip: string; dot: string }
> = {
  idle: {
    label: 'En espera',
    chip: 'text-slate-400 border-slate-700 bg-slate-800/40',
    dot: 'bg-slate-400',
  },
  listening: {
    label: 'Escuchando',
    chip: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
    dot: 'bg-emerald-400',
  },
  thinking: {
    label: 'Pensando',
    chip: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    dot: 'bg-amber-400',
  },
  speaking: {
    label: 'Hablando',
    chip: 'text-[#E25C1D] border-[#E25C1D]/30 bg-[#E25C1D]/10',
    dot: 'bg-[#E25C1D]',
  },
};

export const ORB_RING: Record<AssistantState, string> = {
  idle: 'border-[#E25C1D]/40',
  listening: 'border-emerald-400 shadow-[0_0_45px_rgba(16,185,129,0.55)]',
  thinking: 'border-amber-400',
  speaking: 'border-[#E25C1D] shadow-[0_0_45px_rgba(226,92,29,0.5)]',
};

// Shared surface/control fragments (light defaults + dark: variants).
export const CARD =
  'rounded-3xl border shadow-sm bg-white border-gray-200 text-slate-800 ' +
  'dark:bg-[#131E3B] dark:border-slate-800 dark:text-slate-100';

// Always-dark glass panel (assistant + widgets).
export const PANEL =
  'rounded-3xl bg-[#0B0F19]/80 backdrop-blur-xl border border-white/10 shadow-2xl text-white';

export const INPUT =
  'w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] ' +
  'bg-white border-gray-300 text-slate-800 ' +
  'dark:bg-slate-900 dark:border-slate-800 dark:text-white';

export const SECTION_TITLE = 'font-bold text-sm uppercase tracking-wider text-[#E25C1D]';

export const LABEL = 'text-xs font-semibold text-gray-600 dark:text-gray-400';
