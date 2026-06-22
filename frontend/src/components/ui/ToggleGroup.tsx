import type { ReactNode } from 'react';

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

// The segmented "pill" selector repeated across Settings (theme, engine, YOLO,
// Whisper) and the assistant voice-mode switch. Active = orange, inactive =
// muted with a hover, in both themes.
export function ToggleGroup<T extends string>({
  options,
  value,
  onChange,
  columns,
  className = '',
}: ToggleGroupProps<T>) {
  const cols = columns ?? options.length;
  return (
    <div
      className={`grid gap-2 p-1 rounded-xl bg-gray-100 dark:bg-slate-900/60 ${className}`}
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`py-2 text-xs font-bold uppercase rounded-lg transition-all ${
              active
                ? 'bg-[#E25C1D] text-white shadow-md'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
