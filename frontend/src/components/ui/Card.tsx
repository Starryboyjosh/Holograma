import type { ReactNode } from 'react';
import { CARD, SECTION_TITLE } from '../../theme';

interface CardProps {
  children: ReactNode;
  /** Use inside a masonry `columns-*` container (break-inside-avoid). */
  masonry?: boolean;
  className?: string;
}

// The repeated settings/remote panel: rounded-3xl bordered surface that works in
// both themes via the shared CARD token. `masonry` adds the column-break guard.
export function Card({ children, masonry = false, className = '' }: CardProps) {
  return (
    <div
      className={`${CARD} p-6 space-y-4 ${
        masonry ? 'break-inside-avoid inline-block w-full mb-6' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className={SECTION_TITLE}>{children}</h3>;
}
