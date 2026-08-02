import type { CSSProperties, ReactNode } from 'react';
import meshGradient from '../../assets/holomind/mesh-gradient.webp';
import { BlueOvals } from './BlueOvals';

export type Backdrop = 'mesh' | 'navy' | 'cream' | 'settings';

/** Alto aproximado de la cabecera sticky — compensa el ancla de scroll para que la
 *  sección no quede oculta debajo de ella (nodo 79:2, cabecera flotante).
 *
 *  IMPORTANTE: `bleedTop` más abajo necesita el mismo valor, pero como clase de
 *  Tailwind LITERAL (`top-[-132px]`) — Tailwind analiza el código fuente en busca
 *  de strings de clase completos en tiempo de build, así que una clase armada con
 *  interpolación de esta constante (`` `top-[-${HEADER_SCROLL_OFFSET}px]` ``)
 *  nunca generaría CSS real. Si este número cambia, hay que actualizar también
 *  las clases `top-[-132px]`/`top-[-242px]` de `bleedTop`. */
const HEADER_SCROLL_OFFSET = 132;

/**
 * Degradado CSS de la sección CONFIGURACIÓN (nodo 63:36): navy oscuro
 * arriba-izquierda hacia gris claro arriba-derecha, con dos óvalos difuminados
 * azul-navy superpuestos — aproximación del fondo real del Figma (que usa un
 * asset propio, distinto de `mesh-gradient.webp`). Se recreó en CSS por no
 * poder exportar el asset original (límite de la API de Figma agotado en la
 * sesión en la que se hizo esto); sustituir por el asset real si se libera.
 */
// Una sola línea, sin concatenación: Tailwind necesita ver la clase completa
// como texto literal contiguo en el archivo para generar su CSS — construirla
// con `+` (como el resto de constantes de esta función) rompería el escaneo
// igual que pasaría con una interpolación de variable.
const SETTINGS_GRADIENT = 'bg-[radial-gradient(ellipse_460px_240px_at_64%_28%,rgba(46,58,112,0.85),transparent_70%),radial-gradient(ellipse_320px_170px_at_92%_6%,rgba(46,58,112,0.55),transparent_70%),linear-gradient(135deg,#1b2140_0%,#333a5e_26%,#7c8296_55%,#c7c4c9_78%,#ece8e4_100%)]';

/** Qué variante de `BlueOvals` corresponde a cada fondo (`cream` no lleva). */
const OVAL_VARIANT: Partial<Record<Backdrop, 'hero' | 'navy' | 'settings'>> = {
  mesh: 'hero',
  navy: 'navy',
  settings: 'settings',
};

/**
 * Bloque de fondo de cada sección del diseño (INICIO en malla, CONFIGURACIÓN en
 * su propio degradado, ENTRENAR VISIÓN en navy, HABLAR/INFO. UNEV en crema).
 *
 * En la landing de una sola página la cabecera es única y flota por encima de
 * todas las secciones (ver `StickyHeader`), así que este componente ya no la
 * renderiza — solo aporta el fondo, el arco y el ancla de scroll (`id`).
 *
 * `arc` recorta el borde inferior con la curva característica del diseño. Se hace
 * con `border-radius` elíptico en vez de un SVG de 1440px para que la curva siga el
 * ancho real de la ventana.
 */
export function ScreenHero({
  id,
  backdrop,
  arc = true,
  topArc = false,
  bleedTop = false,
  className = '',
  children,
}: {
  /** Ancla de scroll para el nav/footer (p. ej. "hablar" → `#hablar`). */
  id?: string;
  backdrop: Backdrop;
  arc?: boolean;
  /** Arco navy asomando por arriba, como en INFO. UNEV (nodo 48:334). */
  topArc?: boolean;
  /**
   * Extiende el fondo por detrás de la cabecera sticky en vez de empezar en el
   * borde superior de la sección. Solo tiene sentido en la sección que queda
   * primera bajo la cabecera al cargar la página (Inicio en la landing,
   * Configuración en su propia ruta) — de lo contrario, al hacer scroll=0, el
   * fondo no llega hasta arriba y detrás de la cabecera se ve el `bg-cream` del
   * shell en vez del degradado de la sección. La cabecera sigue pintándose
   * encima: la sección es `isolate`, así que este fondo (`-z-10`) nunca puede
   * escapar por encima de ella.
   */
  bleedTop?: boolean;
  className?: string;
  children?: ReactNode;
}) {
  const style: CSSProperties | undefined = id
    ? { scrollMarginTop: HEADER_SCROLL_OFFSET }
    : undefined;

  // Misma posición/tamaño para el color de fondo y los óvalos: comparten
  // caja, pero NO el mismo elemento — ver nota junto a `BlueOvals` más abajo.
  const backdropBox = `absolute inset-x-[-8%] bottom-0 -z-10 ${
    bleedTop ? 'top-[-242px] md:top-[-132px]' : 'top-0'
  }`;

  return (
    <section id={id} style={style} className={`relative isolate ${className}`}>
      {topArc && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-[-8%] top-[-90px] -z-10 h-[120px] rounded-b-[50%/100%] bg-navy"
        />
      )}
      {backdrop !== 'cream' && (
        <div
          aria-hidden
          className={`${backdropBox} overflow-hidden ${arc ? 'rounded-b-[50%/22%]' : ''} ${
            backdrop === 'navy' ? 'bg-navy' : ''
          } ${backdrop === 'settings' ? SETTINGS_GRADIENT : ''}`}
        >
          {backdrop === 'mesh' && (
            <img
              src={meshGradient}
              alt=""
              draggable={false}
              className="h-full w-full object-cover"
            />
          )}
        </div>
      )}
      {/* Óvalos como objeto propio detrás de la sección, NO anidado en el div de
          arriba: ese div recorta con `overflow-hidden` + el arco (`rounded-b`)
          para que el color/imagen siga la curva del diseño, pero los óvalos deben
          poder sangrar más allá de esa curva en vez de quedar cortados por ella. */}
      {OVAL_VARIANT[backdrop] && (
        <div aria-hidden className={backdropBox}>
          <BlueOvals variant={OVAL_VARIANT[backdrop]!} />
        </div>
      )}

      {children}
    </section>
  );
}
