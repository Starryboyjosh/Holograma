import { useCallback, useEffect, useRef, useState } from 'react';
import { resolveBackendUrl, wsUrl } from '../lib/backend';
import type { AssistantState } from '../theme';

interface UseChatSocketOptions {
  /** Surface camera/error events as toasts in the host UI. */
  onToast?: (msg: string) => void;
}

export interface ChatSocket {
  wsConnected: boolean;
  assistantState: AssistantState;
  setAssistantState: (s: AssistantState) => void;
  aiSpokenText: string;
  userSpokenText: string;
  setUserSpokenText: (t: string) => void;
  highlightKeyword: string;
  voiceMode: string;
  personCount: number;
  sendPrompt: (text: string) => void;
  requestServerListen: () => void;
  setVoiceModeRemote: (mode: string) => void;
}

// WebSocket chat connection + assistant state machine. Lifted from the original
// App.tsx connectWebSocket/onmessage so it can be shared across screens (via
// SessionContext) and reused independently inside detachable widget windows.
export function useChatSocket(options: UseChatSocketOptions = {}): ChatSocket {
  const { onToast } = options;
  const onToastRef = useRef(onToast);
  useEffect(() => {
    onToastRef.current = onToast;
  });

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedByUnmount = useRef(false);
  // Referencia a la última `connect` para reconectar desde onclose sin que la
  // callback se referencie a sí misma (evita el acceso antes de declararla).
  const connectRef = useRef<() => void>(() => {});

  const [wsConnected, setWsConnected] = useState(false);
  const [assistantState, setAssistantState] = useState<AssistantState>('idle');
  const [aiSpokenText, setAiSpokenText] = useState('Holograma listo para interactuar.');
  const [userSpokenText, setUserSpokenText] = useState('Listo para recibir comandos.');
  const [highlightKeyword, setHighlightKeyword] = useState('');
  const [voiceMode, setVoiceMode] = useState('ptt');
  const [personCount, setPersonCount] = useState(0);

  const connect = useCallback(async () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) return;
    await resolveBackendUrl();
    const ws = new WebSocket(wsUrl('/ws/chat'));

    ws.onopen = () => {
      setWsConnected(true);
      setUserSpokenText('Conexión WebSocket activa.');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'status' && data.status === 'streaming_started') {
          setAssistantState('thinking');
          setAiSpokenText('');
          setHighlightKeyword('');
          setUserSpokenText('Generando respuesta...');
        } else if (data.type === 'text_chunk') {
          setAssistantState('speaking');
          setAiSpokenText((prev) => prev + data.text);
        } else if (data.type === 'text_done') {
          setAssistantState('speaking');
        } else if (data.type === 'voice_mode') {
          setVoiceMode(data.mode);
        } else if (data.type === 'audio_status') {
          if (data.status === 'processing') {
            setAssistantState('speaking');
            setUserSpokenText('Respondiendo…');
          } else if (data.status === 'completed') {
            setAssistantState('idle');
            setUserSpokenText('');
          }
        } else if (data.type === 'stt_transcript') {
          setUserSpokenText(`Escuchado: "${data.text}"`);
          setAssistantState('thinking');
        } else if (data.type === 'camera_event') {
          if (typeof data.count === 'number') setPersonCount(data.count);
          if (data.event === 'person_entered') {
            onToastRef.current?.('Persona detectada por la cámara.');
          } else if (data.event === 'person_left') {
            setPersonCount(0);
            onToastRef.current?.('La persona se ha retirado.');
          } else if (data.event === 'custom_object_detected') {
            onToastRef.current?.('Objeto entrenado detectado por la cámara.');
          }
        } else if (data.type === 'error') {
          onToastRef.current?.(`Error: ${data.message}`);
          setUserSpokenText('Error en el backend.');
          setAssistantState('idle');
        }
      } catch {
        setAiSpokenText(event.data);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      if (!closedByUnmount.current) {
        reconnectRef.current = setTimeout(() => connectRef.current(), 3000);
      }
    };

    socketRef.current = ws;
  }, []);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    closedByUnmount.current = false;
    void connect();
    return () => {
      closedByUnmount.current = true;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      socketRef.current?.close();
    };
  }, [connect]);

  const sendPrompt = useCallback((promptText: string) => {
    if (!promptText.trim()) return;
    const ws = socketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ prompt: promptText }));
      setUserSpokenText(`Enviado: "${promptText}"`);
    } else {
      onToastRef.current?.('WebSocket no está conectado.');
    }
  }, []);

  const requestServerListen = useCallback(() => {
    setAssistantState((current) => {
      if (current === 'thinking' || current === 'speaking') return current;
      const ws = socketRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'listen' }));
        setUserSpokenText('Te escucho… habla ahora');
        return 'listening';
      }
      onToastRef.current?.('Conectando con el holograma… intenta de nuevo en un momento.');
      void connect();
      return current;
    });
  }, [connect]);

  const setVoiceModeRemote = useCallback((mode: string) => {
    const ws = socketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_mode', mode }));
      setVoiceMode(mode);
    } else {
      onToastRef.current?.('Sin conexión al holograma.');
    }
  }, []);

  return {
    wsConnected,
    assistantState,
    setAssistantState,
    aiSpokenText,
    userSpokenText,
    setUserSpokenText,
    highlightKeyword,
    voiceMode,
    personCount,
    sendPrompt,
    requestServerListen,
    setVoiceModeRemote,
  };
}
