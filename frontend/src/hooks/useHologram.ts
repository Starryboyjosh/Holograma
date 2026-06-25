import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from '../lib/backend';

interface UseHologramOptions {
  onToast?: (msg: string) => void;
}

// TCP control of the physical MISSYOU hologram fan, lifted from App.tsx.
export function useHologram(options: UseHologramOptions = {}) {
  const onToastRef = useRef(options.onToast);
  useEffect(() => {
    onToastRef.current = options.onToast;
  });

  const [holoIp, setHoloIp] = useState('');
  const [holoPort, setHoloPort] = useState(50200);
  const [holoConnected, setHoloConnected] = useState(false);
  const [holoStatusMsg, setHoloStatusMsg] = useState<string | null>(null);

  const toast = (msg: string) => onToastRef.current?.(msg);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await apiFetch('/api/hologram/status');
      const data = await res.json();
      setHoloConnected(data.connected);
      if (data.ip) setHoloIp(data.ip);
      if (data.port) setHoloPort(data.port);
      if (data.connected) {
        setHoloStatusMsg(`Conectado a ${data.ip}:${data.port}`);
      } else if (data.ip) {
        setHoloStatusMsg(`Configurado para ${data.ip}:${data.port}; reintentando…`);
      } else {
        setHoloStatusMsg('Desconectado');
      }
    } catch {
      /* ignorar */
    }
  }, []);

  useEffect(() => {
    // Carga inicial del estado del holograma desde el backend (sincronización con
    // un sistema externo). El setState ocurre tras el await, no de forma síncrona.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchStatus();
    const interval = window.setInterval(() => void fetchStatus(), 5000);
    return () => window.clearInterval(interval);
  }, [fetchStatus]);

  const connect = useCallback(async () => {
    if (!holoIp) {
      toast('Introduce una IP');
      return;
    }
    try {
      const res = await apiFetch('/api/hologram/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip: holoIp, port: holoPort }),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        setHoloConnected(Boolean(data.connected));
        setHoloStatusMsg(
          data.connected
            ? `Conectado a ${data.ip}:${data.port}`
            : `Conexión configurada para ${data.ip}:${data.port}; reintentando…`,
        );
        toast(data.connected ? `Conectado a ${data.ip}` : 'Conexión configurada; el holograma reintentará automáticamente.');
      } else {
        setHoloConnected(false);
        toast(`Error: ${data.message}`);
      }
    } catch {
      toast('Error de conexión');
    }
  }, [holoIp, holoPort]);

  const disconnect = useCallback(async () => {
    try {
      const res = await apiFetch('/api/hologram/disconnect', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'ok') {
        setHoloConnected(false);
        setHoloStatusMsg('Desconectado');
        toast('Desconectado');
      }
    } catch {
      toast('Error al desconectar');
    }
  }, []);

  return {
    holoIp,
    setHoloIp,
    holoPort,
    setHoloPort,
    holoConnected,
    holoStatusMsg,
    connect,
    disconnect,
  };
}
