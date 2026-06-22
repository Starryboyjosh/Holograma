import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';
import { INPUT, LABEL } from '../../theme';

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <label className={LABEL}>{label}</label>
      {children}
    </div>
  );
}

// Themed <input>/<select> that reuse the shared INPUT token so the focus ring,
// borders, and dark-mode colors stay identical everywhere.
export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const { className = '', ...rest } = props;
  return <input {...rest} className={`${INPUT} ${className}`} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  const { className = '', children, ...rest } = props;
  return (
    <select {...rest} className={`${INPUT} ${className}`}>
      {children}
    </select>
  );
}
