import { useLayoutEffect } from 'react';
import type { RefObject } from 'react';

const MAX_VISIBLE_LINES = 6;

/**
 * Ajusta la altura de un `<textarea>` a su contenido — crece línea a línea al
 * escribir y se encoge al borrar — con un tope de `MAX_VISIBLE_LINES` líneas:
 * a partir de ahí la altura se congela y aparece scroll interno (ver la clase
 * `.thin-scroll`/`.thin-scroll-glass` en `index.css`).
 *
 * Mide con `getComputedStyle` en vez de asumir un alto de línea o un padding
 * fijos: el mismo `<textarea>` (ver `Field.tsx`) se usa sobre superficie
 * "glass" (con borde de 1px) y sobre "cream" (sin borde), así que hardcodear
 * píxeles se desincroniza en cuanto cambie cualquiera de esos tokens. Requiere
 * que el elemento tenga una clase `leading-*` explícita — sin ella,
 * `lineHeight` computado puede resolver a "normal" en vez de un valor en
 * píxeles, y el cálculo de 6 líneas dejaría de ser exacto.
 */
export function useAutosizeTextarea(
  ref: RefObject<HTMLTextAreaElement | null>,
  value: unknown,
): void {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Resetear antes de medir: si no, `scrollHeight` arrastra la altura fijada
    // en el ciclo anterior y nunca detecta que el texto se achicó.
    el.style.height = 'auto';

    const computed = window.getComputedStyle(el);
    const lineHeight = parseFloat(computed.lineHeight) || 0;
    const paddingTop = parseFloat(computed.paddingTop) || 0;
    const paddingBottom = parseFloat(computed.paddingBottom) || 0;
    const borderTop = parseFloat(computed.borderTopWidth) || 0;
    const borderBottom = parseFloat(computed.borderBottomWidth) || 0;
    const maxHeight =
      lineHeight * MAX_VISIBLE_LINES + paddingTop + paddingBottom + borderTop + borderBottom;

    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
    el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden';
  }, [ref, value]);
}
