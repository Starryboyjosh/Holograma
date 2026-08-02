import type { CSSProperties } from 'react';

/**
 * Óvalos de neón traslúcidos superpuestos al fondo de una sección (ver
 * `ScreenHero` y `HolomindFooter`): manchas de luz de distinta profundidad que
 * dan dinamismo, con zonas de intersección más luminosas donde se solapan.
 *
 * Aproximado en CSS a partir de la descripción del diseño, no extraído de
 * Figma: el plan Starter del MCP de Figma agotó su límite de llamadas en la
 * sesión en la que se hizo esto. Sustituir por los valores exactos del nodo
 * si se libera.
 *
 * Cada óvalo fija `border-radius: 50%` sobre una caja con ancho ≠ alto: así
 * el recorte de la forma es una elipse real, independiente de dónde se
 * desvanezca el degradado interior. Rotado entre -30° y 45° para romper la
 * simetría.
 *
 * IMPORTANTE sobre `blend` + color: con `screen`/`lighten` cualquier parada
 * más oscura que el fondo no aporta nada (screen(oscuro, fondo) ≈ fondo), así
 * que esas dos capas usan degradados de un único tono claro que se desvanece
 * a `transparent` (nunca a un tono "profundo" oscuro) — de lo contrario, tras
 * el blur, solo el núcleo brillante sobrevivía y el resto se leía como una
 * mancha sin forma en vez de una elipse. `soft-light`/`overlay` sí respetan
 * tonos oscuros, así que esas capas conservan el centro brillante → borde
 * profundo del diseño original.
 *
 * El color va en `style`, no en clases de Tailwind: tamaño, gradiente, blur y
 * rotación son numéricos y varían por capa, así que una clase con valor
 * arbitrario por óvalo sería ilegible y frágil frente a datos interpolados.
 */
type BlendMode = 'screen' | 'lighten' | 'overlay' | 'soft-light';
/** `pulse` = respiración de opacidad (conexión "viva"); `float` = deriva de
 *  pocos px + micro-rotación en bucle, muy lenta. Ambas respetan
 *  `prefers-reduced-motion` (ver index.css). */
type Animate = 'pulse' | 'float';

type OvalSpec = {
  widthPx: number;
  heightPx: number;
  top?: string;
  left?: string;
  right?: string;
  bottom?: string;
  /** Degradado radial de 2-3 paradas. */
  gradient: string;
  /** 0.2 - 0.65 según profundidad de capa. */
  opacity: number;
  /** 0 = borde definido (capa cercana); 20-40 = capa media; 60-90 = capa
   *  lejana (mancha de luz / bokeh). */
  blurPx: number;
  rotateDeg: number;
  blend?: BlendMode;
  /** Resplandor exterior suave — solo tiene sentido en capas de borde definido. */
  glow?: string;
  animate?: Animate;
  durationS?: number;
};

const CYAN_BRIGHT = '#7FE8E0';
const ORCHID_BRIGHT = '#C9A6F0';
const BLUE_LIGHT = '#5FA8E0';
const BLUE_DEEP = '#1D2E72';
const BLUE_DEEP_FAINT = 'rgba(29, 46, 114, 0.06)';

/** Núcleo brillante → mismo tono más tenue → transparente. Para capas con
 *  `blend: 'screen' | 'lighten'`: todas las paradas deben ser claras (ver nota
 *  de arriba), así que en vez de virar a un tono "profundo" oscuro, se atenúa
 *  el mismo color brillante. */
function glow(bright: string, mid: string, anchor = '45% 40%') {
  return `radial-gradient(ellipse at ${anchor}, ${bright} 0%, ${mid} 42%, transparent 78%)`;
}

/** Núcleo brillante → borde profundo → borde semi-transparente. Solo para
 *  capas con `blend: 'soft-light' | 'overlay'` o sin blend (esos modos sí
 *  reaccionan a tonos oscuros). */
function deepGlow(bright: string, deep: string, deepFaint: string, anchor = '45% 40%') {
  return `radial-gradient(ellipse at ${anchor}, ${bright} 0%, ${deep} 55%, ${deepFaint} 85%)`;
}

function Oval({
  widthPx,
  heightPx,
  top,
  left,
  right,
  bottom,
  gradient,
  opacity,
  blurPx,
  rotateDeg,
  blend,
  glow: glowShadow,
  animate,
  durationS,
}: OvalSpec) {
  // Las variables `--oval-*` no son propiedades CSS estándar, así que
  // `CSSProperties` no las tipa — se extiende con un índice para poder
  // pasarlas junto al resto del estilo sin un `as` a ciegas.
  const style: CSSProperties & Record<`--oval-${string}`, string | number> = {
    position: 'absolute',
    width: widthPx,
    height: heightPx,
    top,
    left,
    right,
    bottom,
    borderRadius: '50%',
    zIndex: 0,
    background: gradient,
    opacity,
    filter: blurPx ? `blur(${blurPx}px)` : undefined,
    boxShadow: glowShadow,
    mixBlendMode: blend,
    transform: animate === 'float' ? undefined : `rotate(${rotateDeg}deg)`,
    animationDuration: animate ? `${durationS ?? 8}s` : undefined,
    // Variables leídas por @keyframes oval-pulse/oval-float (index.css).
    '--oval-rotate': `${rotateDeg}deg`,
    '--oval-op-min': Math.max(0.15, opacity - 0.15),
    '--oval-op-max': opacity,
  };
  const animClass = animate === 'pulse' ? 'oval-pulse' : animate === 'float' ? 'oval-float' : '';
  return <div className={animClass} style={style} />;
}

const VARIANTS: Record<'hero' | 'navy' | 'settings' | 'footer', OvalSpec[]> = {
  // INICIO: encima de mesh-gradient.webp — discreto, en los bordes, dejando el
  // centro (titular) despejado.
  hero: [
    {
      widthPx: 560,
      heightPx: 360,
      left: '-16%',
      top: '-18%',
      gradient: deepGlow(CYAN_BRIGHT, BLUE_DEEP, BLUE_DEEP_FAINT),
      opacity: 0.4,
      blurPx: 70,
      rotateDeg: -22,
      blend: 'soft-light',
    },
    {
      widthPx: 340,
      heightPx: 210,
      right: '-4%',
      top: '6%',
      gradient: glow(ORCHID_BRIGHT, 'rgba(201, 166, 240, 0.5)'),
      opacity: 0.45,
      blurPx: 26,
      rotateDeg: 34,
      blend: 'screen',
    },
    {
      widthPx: 200,
      heightPx: 120,
      right: '14%',
      bottom: '8%',
      gradient: glow(CYAN_BRIGHT, 'rgba(127, 232, 224, 0.5)'),
      opacity: 0.35,
      blurPx: 0,
      rotateDeg: -8,
      blend: 'screen',
      glow: `0 0 50px 6px rgba(127, 232, 224, 0.25)`,
    },
  ],
  // ENTRENAR VISIÓN: fondo navy liso — juego completo de capas (lejana
  // difuminada + medias + una cercana de borde definido con resplandor).
  navy: [
    {
      widthPx: 600,
      heightPx: 360,
      left: '-14%',
      top: '-16%',
      gradient: glow(CYAN_BRIGHT, 'rgba(127, 232, 224, 0.55)', '42% 38%'),
      opacity: 0.55,
      blurPx: 75,
      rotateDeg: 18,
      blend: 'screen',
      animate: 'float',
      durationS: 11,
    },
    {
      widthPx: 400,
      heightPx: 250,
      right: '-6%',
      top: '24%',
      gradient: glow(ORCHID_BRIGHT, 'rgba(201, 166, 240, 0.5)', '55% 45%'),
      opacity: 0.5,
      blurPx: 30,
      rotateDeg: -28,
      blend: 'lighten',
    },
    {
      widthPx: 300,
      heightPx: 190,
      left: '8%',
      bottom: '4%',
      gradient: glow(BLUE_LIGHT, 'rgba(95, 168, 224, 0.5)', '48% 42%'),
      opacity: 0.45,
      blurPx: 24,
      rotateDeg: 40,
      blend: 'screen',
    },
    {
      widthPx: 170,
      heightPx: 100,
      right: '18%',
      bottom: '14%',
      gradient: glow(CYAN_BRIGHT, 'rgba(127, 232, 224, 0.55)'),
      opacity: 0.4,
      blurPx: 0,
      rotateDeg: -12,
      blend: 'screen',
      glow: '0 0 60px 8px rgba(127, 232, 224, 0.3)',
      animate: 'pulse',
      durationS: 7,
    },
  ],
  // CONFIGURACIÓN: complementa (no reemplaza) los óvalos ya bakeados en
  // `SETTINGS_GRADIENT` — acentos extra en las esquinas que ese degradado no cubre.
  settings: [
    {
      widthPx: 340,
      heightPx: 210,
      left: '-8%',
      bottom: '-8%',
      gradient: deepGlow(CYAN_BRIGHT, BLUE_DEEP, BLUE_DEEP_FAINT),
      opacity: 0.42,
      blurPx: 30,
      rotateDeg: -20,
      blend: 'soft-light',
    },
    {
      widthPx: 190,
      heightPx: 115,
      left: '28%',
      top: '2%',
      gradient: deepGlow(ORCHID_BRIGHT, BLUE_DEEP, BLUE_DEEP_FAINT, '55% 45%'),
      opacity: 0.34,
      blurPx: 20,
      rotateDeg: 26,
      blend: 'overlay',
    },
  ],
  // PIE: arco navy detrás de la tarjeta de cristal — capas grandes y difusas
  // más un acento pequeño y definido para no competir con el logo/enlaces.
  footer: [
    {
      widthPx: 460,
      heightPx: 280,
      left: '-12%',
      top: '-20%',
      gradient: glow(CYAN_BRIGHT, 'rgba(127, 232, 224, 0.5)'),
      opacity: 0.5,
      blurPx: 65,
      rotateDeg: -30,
      blend: 'screen',
    },
    {
      widthPx: 420,
      heightPx: 250,
      right: '-14%',
      bottom: '-16%',
      gradient: glow(BLUE_LIGHT, 'rgba(95, 168, 224, 0.55)', '55% 45%'),
      opacity: 0.6,
      blurPx: 70,
      rotateDeg: 14,
      blend: 'lighten',
    },
    {
      widthPx: 150,
      heightPx: 90,
      right: '20%',
      top: '10%',
      gradient: glow(ORCHID_BRIGHT, 'rgba(201, 166, 240, 0.5)'),
      opacity: 0.32,
      blurPx: 0,
      rotateDeg: -10,
      blend: 'screen',
      glow: '0 0 45px 6px rgba(201, 166, 240, 0.25)',
      animate: 'pulse',
      durationS: 9,
    },
  ],
};

export function BlueOvals({ variant }: { variant: keyof typeof VARIANTS }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {VARIANTS[variant].map((oval, i) => (
        <Oval key={i} {...oval} />
      ))}
    </div>
  );
}

export type BlueOvalsVariant = keyof typeof VARIANTS;
