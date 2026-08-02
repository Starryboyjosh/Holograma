// Tokens del diseño Holomind-WEB (Figma YkQXNn1SmbJfFPu1ilGWBw).
//
// El diseño define UN solo aspecto: no hay modo oscuro. Las superficies "oscuras"
// son secciones con degradado (el arco navy, la malla naranja), no un tema. Por eso
// ya no existen variantes `dark:` ni ThemeContext — ver AppShell.
//
// Valores extraídos de get_design_context, no aproximados a ojo.

export const COLORS = {
  /** Fondo de página (crema). */
  cream: '#F5EFEC',
  /** Naranja de marca del diseño. */
  orange: '#FF7208',
  /** Naranja oscuro, tramo intermedio del degradado del wordmark. */
  orangeDeep: '#CC5E15',
  /** Navy del diseño — más claro que el navy institucional histórico. */
  navy: '#2E3A70',
  /** Tinta principal. */
  ink: '#0C0C0C',
  /** Texto secundario / placeholder. */
  muted: '#716E6C',
} as const;

export type AssistantState = 'idle' | 'listening' | 'thinking' | 'speaking';
export type VoiceMode = 'ptt' | 'presentation' | 'auto';

// Chip de estado del asistente: pastilla rgba(0,0,0,0.1) con punto de color.
// El diseño solo especifica "EN ESPERA"; los demás estados reusan la misma forma
// cambiando etiqueta y color de punto.
//
// `chip` existe para las ventanas desprendibles (ChatWidget / TranscriptWidget),
// que el diseño no cubre: van sobre panel oscuro y necesitan su propia variante.
export const STATE_META: Record<
  AssistantState,
  { label: string; dot: string; chip: string }
> = {
  idle: {
    label: 'En espera',
    dot: 'bg-[#716E6C]',
    chip: 'text-white/70 border-white/15 bg-white/5',
  },
  listening: {
    label: 'Escuchando',
    dot: 'bg-emerald-500',
    chip: 'text-emerald-300 border-emerald-400/30 bg-emerald-400/10',
  },
  thinking: {
    label: 'Pensando',
    dot: 'bg-amber-500',
    chip: 'text-amber-300 border-amber-400/30 bg-amber-400/10',
  },
  speaking: {
    label: 'Hablando',
    dot: 'bg-[#FF7208]',
    chip: 'text-[#FF7208] border-[#FF7208]/30 bg-[#FF7208]/10',
  },
};

/** Aro del orbe según estado. El orbe es CSS (se anima); solo el micro es asset. */
export const ORB_RING: Record<AssistantState, string> = {
  idle: 'border-[#FF7208]/45',
  listening: 'border-emerald-500 shadow-[0_0_45px_rgba(16,185,129,0.45)]',
  thinking: 'border-amber-500 shadow-[0_0_45px_rgba(245,158,11,0.4)]',
  speaking: 'border-[#FF7208] shadow-[0_0_55px_rgba(255,114,8,0.5)]',
};

// ---------------------------------------------------------------------------
// Fragmentos de superficie compartidos
// ---------------------------------------------------------------------------

/** Tarjeta sobre crema: rgba(0,0,0,0.05), radio 30px (nodo 53:584). */
export const CARD = 'rounded-[30px] bg-black/5';

/** Tarjeta de cristal sobre secciones con degradado (nodo 30:1695). */
export const GLASS =
  'rounded-[30px] bg-white/10 backdrop-blur-xl border border-white/20 ' +
  'shadow-[0_8px_32px_rgba(0,0,0,0.18)] text-white';

/** Chip/pastilla de estado (nodo 31:1867). */
export const CHIP =
  'inline-flex items-center gap-2 rounded-[50px] bg-black/10 px-4 py-1.5 ' +
  'text-[16px] font-semibold italic uppercase text-[#0C0C0C]';

/** Campo de texto sobre crema (nodo 82:x — inputs de CONFIGURACIÓN). */
export const INPUT =
  'w-full rounded-[50px] bg-black/5 px-5 py-3 text-[14px] text-[#0C0C0C] ' +
  'placeholder:text-[#716E6C] focus:outline-none focus:ring-2 focus:ring-[#FF7208]/50';

/** Campo de texto sobre cristal (INFO. UNEV / ENTRENAR VISIÓN). */
export const INPUT_GLASS =
  'w-full rounded-[50px] bg-white/10 border border-white/15 px-5 py-3 text-[14px] ' +
  'text-white placeholder:text-white/60 placeholder:italic focus:outline-none ' +
  'focus:ring-2 focus:ring-[#FF7208]/60';

/** Botón primario naranja (nodo 44:187 "Encender cámara"). */
export const BTN_PRIMARY =
  'inline-flex items-center justify-center rounded-[50px] bg-[#FF7208] px-7 py-2.5 ' +
  'text-[14px] font-semibold uppercase text-white shadow-[0_1px_5px_rgba(0,0,0,0.25)] ' +
  'transition-opacity hover:opacity-90 disabled:opacity-40';

/** Botón destructivo (nodo "Eliminar" de INFO. UNEV). */
export const BTN_DANGER =
  'inline-flex items-center justify-center rounded-[50px] bg-[#E03B33] px-6 py-2 ' +
  'text-[14px] font-semibold italic text-white transition-opacity hover:opacity-90';

/** Título de sección naranja en mayúsculas (nodo "INFORMACIÓN INSTITUCIONAL"). */
export const SECTION_TITLE =
  'text-[20px] font-bold uppercase tracking-wide text-[#FF7208]';

/** Etiqueta de campo (nodo "DIRECCIÓN IP:"). */
export const LABEL = 'text-[12px] font-bold uppercase tracking-wide';

/**
 * Degradado del wordmark "HoloMind" / "UNEV" en los titulares.
 * Extraído literal del nodo 30:1847.
 */
export const WORDMARK_GRADIENT =
  'linear-gradient(90deg, #FFFFFF 42.308%, #FF7208 57.212%, #CC5E15 75.962%, #2E3A70 100%)';
