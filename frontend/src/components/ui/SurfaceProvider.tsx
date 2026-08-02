import type { ReactNode } from 'react';
import { SurfaceCtx } from './surfaceContext';
import type { SurfaceTone } from './surfaceContext';

export function SurfaceProvider({
  tone,
  children,
}: {
  tone: SurfaceTone;
  children: ReactNode;
}) {
  return <SurfaceCtx.Provider value={tone}>{children}</SurfaceCtx.Provider>;
}
