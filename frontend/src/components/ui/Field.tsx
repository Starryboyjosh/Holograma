import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react';
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

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const { className = '', rows = 3, ...rest } = props;
  return <textarea {...rest} rows={rows} className={`${INPUT} resize-y ${className}`} />;
}
