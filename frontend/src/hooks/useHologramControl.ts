import { useCallback, useEffect, useRef, useState } from 'react';
import { hologramApi } from '../lib/hologramApi';
import type { FanRole, HologramStatus, IdentityMedia, PromotionMedia } from '../lib/hologramApi';

export function useHologramControl(onMessage?: (message: string) => void) {
  const [status, setStatus] = useState<HologramStatus | null>(null);
  const [identities, setIdentities] = useState<IdentityMedia[]>([]);
  const [promotions, setPromotions] = useState<PromotionMedia[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestInFlight = useRef(false);

  const refresh = useCallback(async (quiet = false) => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    if (!quiet) setRefreshing(true);
    try {
      const [nextStatus, nextIdentities, nextPromotions] = await Promise.all([
        hologramApi.getStatus(),
        hologramApi.getIdentities(),
        hologramApi.getPromotions(),
      ]);
      setStatus(nextStatus);
      setIdentities(nextIdentities.identities);
      setPromotions(nextPromotions.promotions);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo consultar el holograma.');
    } finally {
      requestInFlight.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => void refresh());
    const timer = window.setInterval(() => void refresh(true), 4000);
    return () => {
      window.clearInterval(timer);
    };
  }, [refresh]);

  const run = useCallback(async (operation: () => Promise<unknown>, success: string) => {
    try {
      await operation();
      onMessage?.(success);
      await refresh(true);
      return true;
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'La operación fue rechazada.';
      setError(message);
      onMessage?.(`Error: ${message}`);
      return false;
    }
  }, [onMessage, refresh]);

  const unitAction = useCallback((role: FanRole, action: 'connect' | 'disconnect' | 'identify' | 'test', index?: number) =>
    run(() => hologramApi.unitAction(role, action, index), action === 'identify' ? `Identificación enviada a ${role}.` : 'Unidad actualizada.'), [run]);

  const rotationAction = useCallback((action: 'start' | 'pause' | 'resume' | 'stop') =>
    run(() => hologramApi.rotationAction(action), `Rotación: ${action}.`), [run]);

  return { status, identities, promotions, loading, refreshing, error, refresh, run, unitAction, rotationAction, setIdentities, setPromotions };
}
