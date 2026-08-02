import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react';
import { useRef } from 'react';
import { INPUT, INPUT_GLASS, LABEL } from '../../theme';
import { useSurface } from './surfaceContext';
import { useAutosizeTextarea } from '../../hooks/useAutosizeTextarea';

export function Field({ label, children }: { label: string; children: ReactNode }) {
  const tone = useSurface();
  return (
    <div className="space-y-1.5">
      <label className={`${LABEL} ${tone === 'glass' ? 'text-white/85' : 'text-ink'}`}>
        {label}
      </label>
      {children}
    </div>
  );
}

/** Base del campo según la superficie que lo contiene (ver `surface.tsx`). */
function useFieldBase() {
  return useSurface() === 'glass' ? INPUT_GLASS : INPUT;
}

// Los campos de una línea son pastillas (radio 50px en el diseño); las áreas de
// texto usan radio 30px porque son bloques, no pastillas.
export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const { className = '', ...rest } = props;
  return <input {...rest} className={`${useFieldBase()} ${className}`} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  const { className = '', children, ...rest } = props;
  return (
    <select {...rest} className={`${useFieldBase()} ${className}`}>
      {children}
    </select>
  );
}

// Autoajustable: crece línea a línea con el contenido y se congela a partir de
// 6 líneas visibles, con scroll interno delgado (ver `useAutosizeTextarea` y
// `.thin-scroll`/`.thin-scroll-glass` en index.css). Sin `resize-y`: dejar que
// el usuario arrastre el asa a mano competiría con el auto-ajuste en la
// siguiente pulsación de tecla. `leading-6` fija el interlineado a un valor
// exacto en píxeles — el cálculo de 6 líneas depende de poder leerlo de vuelta
// con `getComputedStyle`.
export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const { className = '', rows = 3, value, ...rest } = props;
  const tone = useSurface();
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosizeTextarea(ref, value);
  return (
    <textarea
      {...rest}
      value={value}
      ref={ref}
      rows={rows}
      className={`${useFieldBase()} rounded-[30px] leading-6 ${
        tone === 'glass' ? 'thin-scroll-glass' : 'thin-scroll'
      } ${className}`}
    />
  );
}
