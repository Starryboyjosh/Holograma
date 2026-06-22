import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from '../lib/backend';

interface UseHologramOptions {
  onToast?: (msg: string) => void;
}

// TCP control of the physical MISSYOU hologram fan, lifted from App.tsx.
export function useHologram(options: UseHologramOptions = {}) {
  const onToastRef = useRef(options.onToast);
  onToastRef.current = options.onToast;

  const [holoIp, setHoloIp] = useState('');
  const [holoPort, setHoloPort] = useState(50200);
  const [holoConnected, setHoloConnected] = useState(false);
  const [holoStatusMsg, setHoloStatusMsg] = useState<string | null>(null);
  const [clipNumber, setClipNumber] = useState(0);

  const toast = (msg: string) => onToastRef.current?.(msg);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await apiFetch('/api/hologram/status');
      const data = await res.json();
      setHoloConnected(data.connected);
      if (data.connected) {
        setHoloIp(data.ip);
        setHoloPort(data.port);
        setHoloStatusMsg(`Conectado a ${data.ip}:${data.port}`);
      } else {
        setHoloStatusMsg('Desconectado');
      }
    } catch {
      /* ignorar */
    }
  }, []);

  useEffect(() => {
    void fetchStatus();
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
        setHoloConnected(true);
        setHoloStatusMsg(`Conectado a ${data.ip}:${data.port}`);
        toast(`Conectado a ${data.ip}`);
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

  const command = useCallback(async (cmd: string, index?: number) => {
    try {
      const body: Record<string, unknown> = { command: cmd };
      if (index !== undefined) body.index = index;
      const res = await apiFetch('/api/hologram/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        toast(`Comando: ${cmd}${index !== undefined ? ' #' + index : ''}`);
      } else {
        toast(`Error: ${data.message}`);
      }
    } catch {
      toast('Error enviando comando');
    }
  }, []);

  return {
    holoIp,
    setHoloIp,
    holoPort,
    setHoloPort,
    holoConnected,
    holoStatusMsg,
    clipNumber,
    setClipNumber,
    connect,
    disconnect,
    command,
  };
}
