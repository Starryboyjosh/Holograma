import { useState } from 'react';
import { Card, SectionTitle } from '../ui/Card';
import { Field, TextInput } from '../ui/Field';
import type { FanRole, FanUnitStatus, UnitUpdate } from '../../lib/hologramApi';

const ROLE_LABELS: Record<FanRole, string> = { top: 'Superior — Mascota', center: 'Central — Identidades', bottom: 'Inferior — Promociones' };

export function FanUnitsPanel({ units, onSave, onAction }: { units: FanUnitStatus[]; onSave: (role: FanRole, payload: UnitUpdate) => Promise<boolean>; onAction: (role: FanRole, action: 'connect' | 'disconnect' | 'identify' | 'test', index?: number) => Promise<boolean> }) {
  return <Card><SectionTitle>Unidades físicas</SectionTitle><div className="grid gap-4 lg:grid-cols-3">{(['top', 'center', 'bottom'] as FanRole[]).map((role) => {
    const unit = units.find((item) => item.role === role);
    return <FanUnitCard key={role} role={role} unit={unit} onSave={onSave} onAction={onAction} />;
  })}</div></Card>;
}

function FanUnitCard({ role, unit, onSave, onAction }: { role: FanRole; unit?: FanUnitStatus; onSave: (role: FanRole, payload: UnitUpdate) => Promise<boolean>; onAction: (role: FanRole, action: 'connect' | 'disconnect' | 'identify' | 'test', index?: number) => Promise<boolean> }) {
  const [ip, setIp] = useState(unit?.ip ?? '');
  const [port, setPort] = useState(unit?.port ?? 50200);
  const [identifyIndex, setIdentifyIndex] = useState(255);
  const [enabled, setEnabled] = useState(unit?.enabled ?? true);
  const [index, setIndex] = useState(255);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const save = async () => {
    if (!ip.trim() && enabled) return setMessage('La IP es obligatoria.');
    if (!Number.isInteger(port) || port < 1 || port > 65535) return setMessage('El puerto debe estar entre 1 y 65535.');
    if (!Number.isInteger(identifyIndex) || identifyIndex < 0 || identifyIndex > 255) return setMessage('El índice debe estar entre 0 y 255.');
    setBusy(true); setMessage('');
    const ok = await onSave(role, { ip: ip.trim(), port, enabled, identify_index: identifyIndex });
    setBusy(false); if (ok) setMessage('Guardado.');
  };
  const action = async (name: 'connect' | 'disconnect' | 'identify' | 'test') => { setBusy(true); await onAction(role, name, name === 'test' ? index : undefined); setBusy(false); };
  return <article className="rounded-2xl border border-gray-200 p-4 dark:border-slate-700" aria-label={ROLE_LABELS[role]}>
    <div className="flex items-start justify-between gap-2"><div><h4 className="font-bold">{ROLE_LABELS[role]}</h4><p className="text-xs text-gray-500">{unit?.connected ? 'Conectada' : 'Desconectada'} · {unit?.current_media_id ?? 'Sin contenido'}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${unit?.connected ? 'bg-emerald-500/15 text-emerald-600' : 'bg-slate-500/15 text-slate-500'}`}>{unit?.connected ? 'ONLINE' : 'OFFLINE'}</span></div>
    <div className="grid grid-cols-2 gap-2"><Field label="IP"><TextInput value={ip} onChange={(e) => setIp(e.target.value)} placeholder="10.10.2.212" /></Field><Field label="Puerto"><TextInput type="number" min={1} max={65535} value={port} onChange={(e) => setPort(Number(e.target.value))} /></Field></div>
    <div className="grid grid-cols-2 gap-2"><Field label="Índice identificación"><TextInput type="number" min={0} max={255} value={identifyIndex} onChange={(e) => setIdentifyIndex(Number(e.target.value))} /></Field><Field label="Probar índice"><TextInput type="number" min={0} max={255} value={index} onChange={(e) => setIndex(Number(e.target.value))} /></Field></div>
    <label className="flex items-center gap-2 text-xs font-semibold"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /> Unidad habilitada</label>
    <p className="min-h-4 text-xs text-red-500" aria-live="polite">{message || unit?.last_error || ''}</p>
    <div className="flex flex-wrap gap-2"><button type="button" disabled={busy} onClick={() => void save()} className="rounded-xl bg-[#E25C1D] px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Guardar</button><button type="button" disabled={busy || !unit?.connected} onClick={() => void action('identify')} className="rounded-xl border px-3 py-2 text-xs font-bold disabled:opacity-40">Identificar</button><button type="button" disabled={busy} onClick={() => void action(unit?.connected ? 'disconnect' : 'connect')} className="rounded-xl border px-3 py-2 text-xs font-bold disabled:opacity-40">{unit?.connected ? 'Desconectar' : 'Conectar'}</button><button type="button" disabled={busy || !unit?.connected || index < 0 || index > 255} onClick={() => void action('test')} className="rounded-xl border px-3 py-2 text-xs font-bold disabled:opacity-40">Probar</button></div>
  </article>;
}
