import type { ReactNode } from 'react';
import { useSurface } from './surfaceContext';

export interface ToggleOption<T extends string> {
  value: T;
  label: ReactNode;
}

interface ToggleGroupProps<T extends string> {
  options: ToggleOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Number of grid columns; defaults to one per option. */
  columns?: number;
  className?: string;
}

/**
 * Selector segmentado del diseño (nodos 58:1168 / 38:26): pastilla contenedora con
 * radio 50px y el activo en naranja pleno. El tono inactivo depende de la superficie
 * (crema o degradado) — ver `surface.tsx`.
 */
export function ToggleGroup<T extends string>({
  options,
  value,
  onChange,
  columns,
  className = '',
}: ToggleGroupProps<T>) {
  const cols = columns ?? options.length;
  const glass = useSurface() === 'glass';
  return (
    <div
      className={`grid gap-1 rounded-[50px] p-1 ${glass ? 'bg-white/10' : 'bg-black/5'} ${className}`}
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`rounded-[50px] py-2.5 text-[12px] font-semibold uppercase transition-colors ${
              active
                ? 'bg-orange text-white'
                : glass
                  ? 'text-white/80 hover:text-white'
                  : 'text-ink hover:text-orange'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
