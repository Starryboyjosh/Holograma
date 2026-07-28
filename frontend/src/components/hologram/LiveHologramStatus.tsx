import { Card, SectionTitle } from '../ui/Card';
import type { HologramStatus } from '../../lib/hologramApi';

export function LiveHologramStatus({ status, refreshing, error }: { status: HologramStatus | null; refreshing: boolean; error: string | null }) {
  return <Card><div className="flex items-center justify-between"><SectionTitle>Estado en vivo</SectionTitle><span className="text-xs text-gray-500" aria-live="polite">{refreshing ? 'Actualizando…' : 'Polling cada 4 s'}</span></div>{error && <p className="rounded-xl bg-red-500/10 p-3 text-sm text-red-600" role="alert">{error}</p>}{status && <div className="grid gap-2 sm:grid-cols-3">{status.units.map((unit) => <div key={unit.role} className="rounded-xl border border-gray-200 p-3 text-xs dark:border-slate-700"><p className="font-bold uppercase">{unit.role}</p><p>{unit.ip || 'Sin IP'}:{unit.port} · {unit.connected ? 'conectada' : 'desconectada'}</p><p>Índice {unit.current_index ?? '—'} · {unit.current_media_id ?? 'sin contenido'}</p><p className="truncate text-red-500">{unit.last_error ?? 'Sin errores'}</p></div>)}</div>}</Card>;
}
