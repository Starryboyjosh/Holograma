import { useCallback, useState } from 'react';
import { useToast } from '../../context/ToastContext';
import { hologramApi } from '../../lib/hologramApi';
import type { FanRole, IdentityPayload, PromotionPayload, UnitUpdate } from '../../lib/hologramApi';
import { useHologramControl } from '../../hooks/useHologramControl';
import { FanUnitsPanel } from './FanUnitsPanel';
import { IdentityCatalog } from './IdentityCatalog';
import { PromotionCatalog } from './PromotionCatalog';
import { RotationControls } from './RotationControls';
import { LiveHologramStatus } from './LiveHologramStatus';

export function HologramControlPanel() {
  const toast = useToast(); const control = useHologramControl(toast); const [busy, setBusy] = useState(false);
  const run = useCallback(async (operation: () => Promise<unknown>, success: string) => { setBusy(true); const ok = await control.run(operation, success); setBusy(false); return ok; }, [control]);
  const saveUnit = (role: FanRole, payload: UnitUpdate) => run(() => hologramApi.updateUnit(role, payload), `Configuración de ${role} guardada.`);
  const saveIdentity = (payload: IdentityPayload) => run(() => hologramApi.createIdentity(payload), 'Identidad creada.');
  const updateIdentity = (id: string, payload: IdentityPayload) => run(() => hologramApi.updateIdentity(id, payload), 'Identidad actualizada.');
  const deleteIdentity = (id: string) => run(() => hologramApi.deleteIdentity(id), 'Identidad eliminada.');
  const savePromotion = (payload: PromotionPayload) => run(() => hologramApi.createPromotion(payload), 'Promoción creada.');
  const updatePromotion = (id: string, payload: PromotionPayload) => run(() => hologramApi.updatePromotion(id, payload), 'Promoción actualizada.');
  const deletePromotion = (id: string) => run(() => hologramApi.deletePromotion(id), 'Promoción eliminada.');
  if (control.loading && !control.status) return <div className="w-full max-w-6xl py-8" aria-busy="true">Cargando control del holograma…</div>;
  return <div className="w-full max-w-6xl space-y-6 py-4"><div><h2 className="text-2xl font-black text-navy">Control del holograma</h2><p className="text-xs text-muted">Configura Superior, Central e Inferior sin editar el catálogo JSON.</p></div><LiveHologramStatus status={control.status} refreshing={control.refreshing} error={control.error} /><FanUnitsPanel units={control.status?.units ?? []} onSave={saveUnit} onAction={(role, action, index) => control.unitAction(role, action, index)} /><RotationControls rotation={control.status?.rotation ?? {}} onAction={(action) => void control.rotationAction(action)} busy={busy} /><IdentityCatalog items={control.identities} onCreate={saveIdentity} onUpdate={updateIdentity} onDelete={deleteIdentity} onTest={(id) => run(() => hologramApi.testIdentity(id), 'Prueba de identidad enviada.')} /><PromotionCatalog items={control.promotions} onCreate={savePromotion} onUpdate={updatePromotion} onDelete={deletePromotion} onTest={(id) => run(() => hologramApi.testPromotion(id), 'Prueba de promoción enviada.')} onTestCategory={(category) => run(() => hologramApi.testCategory(category), 'Prueba de categoría enviada.')} /></div>;
}
