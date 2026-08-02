import { useState } from 'react';
import { HologramControlPanel } from './HologramControlPanel';

/**
 * Repliegue "Opciones avanzadas del holograma", al final de Configuración antes
 * del pie.
 *
 * Rotación / Identidades / Promociones no son redundantes en el backend —
 * `HologramDirector` y `MediaRouter` las consumen en cada turno de conversación —
 * pero hoy administran un catálogo vacío: `data/hologram_media.json` no existe,
 * así que el sistema corre sobre `HologramConfig.default()` (una identidad fija,
 * "holomind", y cero promociones), y la rotación automática ya arranca sola al
 * iniciar el backend. Por eso se repliegan en vez de eliminarse: siguen siendo la
 * única vía de autoría del catálogo si UNEV decide poblarlo más adelante, sin
 * ocupar espacio permanente en una pantalla pensada para personal no técnico.
 *
 * Montar `HologramControlPanel` solo mientras está abierto (en vez de ocultarlo
 * con CSS) es intencional: su hook `useHologramControl` sondea el backend cada
 * 4 s desde que se monta, y esta sección casi nunca se abre.
 */
export function AdvancedHologramPanel() {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-8">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between rounded-[30px] bg-black/5 px-6 py-4 text-left text-[14px] font-bold uppercase tracking-wide text-navy transition-colors hover:bg-black/10"
      >
        Opciones avanzadas del holograma
        <span
          aria-hidden
          className={`text-lg transition-transform ${open ? 'rotate-180' : ''}`}
        >
          ⌄
        </span>
      </button>
      {open && (
        <div className="pt-6">
          <HologramControlPanel />
        </div>
      )}
    </div>
  );
}
