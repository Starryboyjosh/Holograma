import React, { useState, useEffect, useRef } from 'react';

const customStyles = `
@keyframes pulse-orange {
  0%, 100% { transform: scale(1); opacity: 0.85; filter: drop-shadow(0 0 0px rgba(226, 92, 29, 0)); }
  50% { transform: scale(1.08); opacity: 1; filter: drop-shadow(0 0 15px rgba(226, 92, 29, 0.45)); }
}
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-6px); }
}
@keyframes rotate-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.organic-orb {
  animation: pulse-orange 3.5s ease-in-out infinite, float 6s ease-in-out infinite;
}
.spin-slow {
  animation: rotate-slow 16s linear infinite;
}
`;

interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  desc: string;
}

interface SavedObject {
  id: number;
  label: string;
  desc: string;
  x: number;
  y: number;
  w: number;
  h: number;
  thumbnail: string;
}

export default function App() {
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [password, setPassword] = useState('');
  const [currentScreen, setCurrentScreen] = useState('home'); // 'home' | 'assistant' | 'settings' | 'teaching'
  const [darkMode, setDarkMode] = useState(true); // Default a dark para emular el vibe de la interfaz
  const [isConversationActive, setIsConversationActive] = useState(false);
  const [assistantState, setAssistantState] = useState('idle'); // 'idle' | 'listening' | 'thinking' | 'speaking'
  const [cameraEnabled, setCameraEnabled] = useState(true); 
  const [cameraOn, setCameraOn] = useState(true); 
  const [textInputOpen, setTextInputOpen] = useState(false); 
  const [customQuery, setCustomQuery] = useState('');

  // Transcripciones reales e interactivas
  const [aiSpokenText, setAiSpokenText] = useState("Introduce la contraseña del holograma para iniciar nuestra interacción.");
  const [userSpokenText, setUserSpokenText] = useState("Listo para recibir comandos.");
  const [highlightKeyword, setHighlightKeyword] = useState("");

  // Ventana flotante Picture-in-Picture (PiP)
  const [pipVisible, setPipVisible] = useState(false);
  const [pipPosition, setPipPosition] = useState({ x: 74, y: 72 });
  const [dragStart, setDragStart] = useState<{ startX: number; startY: number; posStartX: number; posStartY: number } | null>(null);

  // Estados de configuración de Ajustes
  const [appearanceTheme, setAppearanceTheme] = useState('dark'); 
  const [aiEngine, setAiEngine] = useState('local'); // 'local' | 'api'
  const [selectedLocalModel, setSelectedLocalModel] = useState('gemma:4b');
  const [apiProvider, setApiProvider] = useState('openrouter');
  const [apiModel, setApiModel] = useState('meta-llama/llama-3.3-70b-instruct');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [yoloInterval, setYoloInterval] = useState('1.0');
  const [yoloEnabled, setYoloEnabled] = useState(true);
  const [whisperSize, setWhisperSize] = useState('medium');
  const [piperVoice, setPiperVoice] = useState('es_MX-claude-high.onnx');
  const [voicesList, setVoicesList] = useState<string[]>(['es_MX-claude-high.onnx']);
  const [isPlayingVoiceSample, setIsPlayingVoiceSample] = useState(false);

  // Módulo de Entrenamiento Visual (YOLOE Refresher)
  const [teachingTab, setTeachingTab] = useState('visual'); 
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [boundingBoxes, setBoundingBoxes] = useState<BoundingBox[]>([]);
  const [currentLabel, setCurrentLabel] = useState('Carnet UNEV');
  const [currentDesc, setCurrentDesc] = useState('Identificación estudiantil oficial');
  const [savedTeachingObjects, setSavedTeachingObjects] = useState<SavedObject[]>([
    { id: 1, label: 'Escudo UNEV', desc: 'Isotipo institucional bordado', x: 25, y: 30, w: 90, h: 90, thumbnail: 'https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&q=80&w=150' },
    { id: 2, label: 'Telescopio de Aula', desc: 'Ubicado en el laboratorio de física', x: 55, y: 45, w: 100, h: 120, thumbnail: 'https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&q=80&w=150' }
  ]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStartPos, setDrawStartPos] = useState({ x: 0, y: 0 });
  const [tempBox, setTempBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const recognitionRef = useRef<any>(null);

  // Web Speech API: Reconocimiento de Voz (STT) en Navegador
  const startSpeechRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      showToast("Tu navegador no soporta control de voz directo.");
      return;
    }
    
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch(e) {}
    }
    
    const rec = new SpeechRecognition();
    rec.lang = 'es-MX';
    rec.continuous = false;
    rec.interimResults = false;
    
    rec.onstart = () => {
      setAssistantState('listening');
      setUserSpokenText("Te escucho...");
    };
    
    rec.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setUserSpokenText(`Escuchado: "${transcript}"`);
      sendPrompt(transcript);
    };
    
    rec.onerror = (e: any) => {
      console.log("Speech recognition error:", e);
      setAssistantState('idle');
    };
    
    rec.onend = () => {
      // El socket responde al final
    };
    
    recognitionRef.current = rec;
    try {
      rec.start();
    } catch(err) {
      console.error(err);
    }
  };

  // Web Speech API: Síntesis de voz (TTS) en Navegador
  const speakInBrowser = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'es-MX';
      
      utterance.onstart = () => {
        setAssistantState('speaking');
      };
      
      utterance.onend = () => {
        setAssistantState('listening');
        setUserSpokenText("Presiona el orbe o di comandos.");
      };
      
      window.speechSynthesis.speak(utterance);
    }
  };

  // Webcam stream hook
  useEffect(() => {
    let stream: MediaStream | null = null;
    if (cameraOn && currentScreen === 'assistant') {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then((s) => {
          stream = s;
          if (videoRef.current) {
            videoRef.current.srcObject = s;
          }
        })
        .catch((err) => {
          console.warn("No se pudo acceder a la cámara en el navegador:", err);
        });
    }
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [cameraOn, currentScreen]);

  // Alertas personalizadas no bloqueantes
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Cargar configuración inicial del Backend
  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        if (data.HOLOGRAM_MODE) setAppearanceTheme(data.HOLOGRAM_MODE);
        if (data.OLLAMA_MODEL) setSelectedLocalModel(data.OLLAMA_MODEL);
        if (data.OPENROUTER_API_KEY) setApiKey(data.OPENROUTER_API_KEY);
        if (data.LLM_PROVIDER) {
          setApiProvider(data.LLM_PROVIDER);
          setAiEngine(data.LLM_PROVIDER === 'ollama' || data.LLM_PROVIDER === 'local_only' ? 'local' : 'api');
        }
        if (data.LLM_MODEL) setApiModel(data.LLM_MODEL);
        if (data.HOLOGRAM_CAMERA) setYoloEnabled(data.HOLOGRAM_CAMERA === '1');
        if (data.YOLO_INTERVAL_SECONDS) setYoloInterval(data.YOLO_INTERVAL_SECONDS);
        if (data.WHISPER_MODEL) setWhisperSize(data.WHISPER_MODEL);
        if (data.PIPER_VOICE) setPiperVoice(data.PIPER_VOICE);
      }

      const voicesRes = await fetch('/api/voices');
      if (voicesRes.ok) {
        const voicesData = await voicesRes.json();
        if (voicesData.voices) setVoicesList(voicesData.voices);
      }
    } catch (err) {
      console.error("Error al obtener la configuración:", err);
    }
  };

  useEffect(() => {
    if (isUnlocked) {
      fetchConfig();
      connectWebSocket();
    }
    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, [isUnlocked]);

  // Manejo de Conexión de WebSocket
  const connectWebSocket = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/chat`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket conectado al holograma.");
      setWsConnected(true);
      setUserSpokenText("Conexión WebSocket activa.");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'status' && data.status === 'streaming_started') {
          setAssistantState('thinking');
          setAiSpokenText('');
          setHighlightKeyword('');
          setUserSpokenText("Generando respuesta...");
        } else if (data.type === 'text_chunk') {
          setAssistantState('speaking');
          setAiSpokenText(prev => prev + data.text);
        } else if (data.type === 'text_done') {
          setAssistantState('idle');
          setUserSpokenText("Escuchando tu respuesta...");
          speakInBrowser(data.full_text);
        } else if (data.type === 'audio_status') {
          if (data.status === 'processing') {
            setUserSpokenText("Sintetizando voz (XTTS/Piper)...");
          } else if (data.status === 'completed') {
            setUserSpokenText("Escuchando tu respuesta...");
          }
        } else if (data.type === 'stt_transcript') {
          setUserSpokenText(`Escuchado: "${data.text}"`);
          setAssistantState('thinking');
        } else if (data.type === 'camera_event') {
          if (data.event === 'person_entered') {
            showToast("Persona detectada por la cámara.");
          } else if (data.event === 'person_left') {
            showToast("La persona se ha retirado.");
          }
        } else if (data.type === 'error') {
          showToast(`Error: ${data.message}`);
          setUserSpokenText("Error en el backend.");
          setAssistantState('idle');
        }
      } catch (err) {
        // En caso de que recibamos texto plano
        setAiSpokenText(event.data);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket desconectado. Reintentando...");
      setWsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };

    socketRef.current = ws;
  };

  // Enviar mensaje al backend
  const sendPrompt = (promptText: string) => {
    if (!promptText.trim()) return;
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ prompt: promptText }));
      setUserSpokenText(`Enviado: "${promptText}"`);
    } else {
      showToast("WebSocket no está conectado.");
    }
  };

  // Guardar configuración del Backend
  const saveConfig = async () => {
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          OLLAMA_MODEL: aiEngine === 'local' ? selectedLocalModel : null,
          LLM_PROVIDER: aiEngine === 'local' ? 'ollama' : apiProvider,
          LLM_MODEL: aiEngine === 'api' ? apiModel : null,
          OPENROUTER_API_KEY: aiEngine === 'api' ? apiKey : '',
          HOLOGRAM_CAMERA: yoloEnabled ? '1' : '0',
          YOLO_INTERVAL_SECONDS: yoloInterval,
          YOLO_MODEL: 'yoloe26.pt',
          WHISPER_MODEL: whisperSize,
          PIPER_VOICE: piperVoice,
          HOLOGRAM_MODE: appearanceTheme
        })
      });
      if (response.ok) {
        showToast("Configuración aplicada con éxito.");
        setCurrentScreen('home');
      } else {
        showToast("Error al guardar la configuración.");
      }
    } catch (err) {
      showToast("Error de conexión al guardar configuración.");
    }
  };

  // Verificar Contraseña de Acceso
  const verifyPassword = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      const response = await fetch('/api/verify-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      const data = await response.json();
      if (data.status === 'ok') {
        setIsUnlocked(true);
        setAiSpokenText("Holograma listo para interactuar.");
        setHighlightKeyword("");
        setUserSpokenText("Presiona el botón para hablar.");
      } else {
        alert("Contraseña incorrecta. Acceso denegado.");
      }
    } catch (err) {
      alert("Error al conectar con el servidor para la autenticación.");
    }
  };

  useEffect(() => {
    if (appearanceTheme === 'dark') {
      setDarkMode(true);
    } else if (appearanceTheme === 'light') {
      setDarkMode(false);
    } else {
      const hour = new Date().getHours();
      setDarkMode(hour < 7 || hour > 18);
    }
  }, [appearanceTheme]);

  useEffect(() => {
    if (cameraOn && currentScreen !== 'assistant') {
      setPipVisible(true);
    } else {
      setPipVisible(false);
    }
  }, [cameraOn, currentScreen]);

  const handleStartConversation = () => {
    setIsConversationActive(true);
    setCurrentScreen('assistant');
    setAssistantState('listening');
    sendPrompt("saludar");
    setTimeout(startSpeechRecognition, 800);
  };

  const handleEndConversation = () => {
    setIsConversationActive(false);
    setAssistantState('idle');
    showToast("Conversación de voz finalizada.");
  };

  const renderHighlightedText = (text: string, highlight: string) => {
    if (!highlight) return `"${text}"`;
    const parts = text.split(new RegExp(`(${highlight})`, 'gi'));
    return (
      <span>
        "
        {parts.map((part, i) => 
          part.toLowerCase() === highlight.toLowerCase() ? (
            <span key={i} className="text-[#E25C1D] font-semibold underline decoration-orange-500/30 underline-offset-4">
              {part}
            </span>
          ) : (
            part
          )
        )}
        "
      </span>
    );
  };

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (!uploadedImage || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setIsDrawing(true);
    setDrawStartPos({ x, y });
    setTempBox({ x, y, w: 0, h: 0 });
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (!isDrawing || !tempBox || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    setTempBox({
      x: Math.min(drawStartPos.x, currentX),
      y: Math.min(drawStartPos.y, currentY),
      w: Math.abs(currentX - drawStartPos.x),
      h: Math.abs(currentY - drawStartPos.y)
    });
  };

  const handleCanvasMouseUp = () => {
    if (!isDrawing) return;
    setIsDrawing(false);
    if (tempBox && tempBox.w > 10 && tempBox.h > 10) {
      setBoundingBoxes([...boundingBoxes, { ...tempBox, label: currentLabel, desc: currentDesc }]);
    }
    setTempBox(null);
  };

  const handleSaveTeaching = async () => {
    if (boundingBoxes.length === 0) {
      showToast("Dibuja un cuadro sobre el objeto primero.");
      return;
    }
    
    // Transmitir al backend la información de entrenamiento visual
    try {
      const response = await fetch('/api/train/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: uploadedImage,
          boundingBoxes: boundingBoxes
        })
      });
      
      if (response.ok) {
        const newItems = boundingBoxes.map((box, idx) => ({
          id: Date.now() + idx,
          label: box.label || currentLabel,
          desc: box.desc || currentDesc,
          x: box.x,
          y: box.y,
          w: box.w,
          h: box.h,
          thumbnail: uploadedImage || ''
        }));

        setSavedTeachingObjects([...savedTeachingObjects, ...newItems]);
        setBoundingBoxes([]);
        setUploadedImage(null);
        showToast("¡Objeto guardado y entrenado con éxito!");
      } else {
        showToast("Error al enviar el entrenamiento al servidor.");
      }
    } catch (err) {
      showToast("Error de red al guardar el entrenamiento.");
    }
  };

  const handleCompileVocabulary = async (terms: string) => {
    try {
      const response = await fetch('/api/train/vocabulary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vocabulary: terms })
      });
      if (response.ok) {
        showToast("Vocabulario textual cargado al motor YOLOE.");
      } else {
        showToast("Error al compilar el vocabulario.");
      }
    } catch (err) {
      showToast("Error de red al compilar vocabulario.");
    }
  };

  const handlePipDragStart = (e: React.MouseEvent) => {
    setDragStart({
      startX: e.clientX,
      startY: e.clientY,
      posStartX: pipPosition.x,
      posStartY: pipPosition.y
    });
  };

  const handlePipDragMove = (e: React.MouseEvent) => {
    if (!dragStart) return;
    const dx = ((e.clientX - dragStart.startX) / window.innerWidth) * 100;
    const dy = ((e.clientY - dragStart.startY) / window.innerHeight) * 100;
    
    setPipPosition({
      x: Math.min(Math.max(dragStart.posStartX + dx, 2), 85),
      y: Math.min(Math.max(dragStart.posStartY + dy, 5), 90)
    });
  };

  const handlePlayVoicePreview = async () => {
    setIsPlayingVoiceSample(true);
    try {
      await fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: "Hola, esta es una prueba de voz para la universidad UNEV.",
          voice: piperVoice
        })
      });
    } catch (err) {
      showToast("Error al reproducir la voz.");
    }
    setTimeout(() => setIsPlayingVoiceSample(false), 2500);
  };

  // Si no está desbloqueado, muestra el modal de contraseña
  if (!isUnlocked) {
    return (
      <div className="min-h-screen bg-[#0B0F19] text-white flex items-center justify-center font-sans">
        <style>{customStyles}</style>
        <form onSubmit={verifyPassword} className="w-11/12 max-w-md p-10 bg-slate-900/70 border border-slate-800 rounded-3xl shadow-2xl backdrop-blur-md text-center">
          <h2 className="text-3xl font-extrabold mb-4 bg-gradient-to-r from-orange-400 to-[#E25C1D] bg-clip-text text-transparent">
            Acceso Encriptado
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            Introduce la clave para habilitar la interfaz del holograma UNEV.
          </p>
          <div className="mb-6">
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••" 
              className="w-full py-3 px-4 text-center text-lg bg-slate-950 border border-slate-800 rounded-xl outline-none focus:border-[#E25C1D] focus:shadow-[0_0_10px_rgba(226,92,29,0.1)] transition-all"
              autoFocus
            />
          </div>
          <button type="submit" className="w-full py-3 bg-[#E25C1D] hover:bg-orange-600 active:scale-[0.98] text-white font-bold rounded-xl transition-all shadow-lg shadow-[#E25C1D]/20">
            Desbloquear Consola
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className={`min-h-screen font-sans transition-colors duration-500 flex flex-col justify-between ${darkMode ? 'dark bg-[#0B0F19]' : 'bg-[#F4F6FA] text-[#1C2D5A]'}`}>
      <style>{customStyles}</style>

      {/* TOAST NOTIFICACIONES */}
      {toastMessage && (
        <div className="fixed bottom-6 left-6 z-50 bg-[#1C2D5A] border border-[#E25C1D]/30 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 animate-bounce">
          <svg className="w-5 h-5 text-[#E25C1D]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* BARRA DE NAVEGACIÓN GLOBAL */}
      <header className={`sticky top-0 z-40 backdrop-blur-md border-b transition-colors ${darkMode ? 'bg-[#0B0F19]/90 border-slate-800' : 'bg-white/90 border-gray-200'} py-4 px-6 md:px-12 flex justify-between items-center`}>
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentScreen('home')}>
          <div className="w-9 h-9 rounded-xl bg-[#1C2D5A] border border-[#E25C1D]/20 flex items-center justify-center shadow-lg shadow-[#1C2D5A]/30">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="#E25C1D" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9s2.015-9 4.5-9m0 18c-1.18 0-2.053-.94-2.28-2.191M15.5 15.5c0 1.1-.9 2-2 2h-3c-1.1 0-2-.9-2-2" />
            </svg>
          </div>
          
          <span className="font-extrabold text-xl tracking-tight inline-flex items-center">
            <span className="text-[#E25C1D]">U</span>
            <span className="text-[#1C2D5A]">NE</span>
            <span className="relative inline-block font-extrabold select-none">
              <span className="text-[#1C2D5A]">V</span>
              <span className="absolute top-0 left-0 text-[#E25C1D]" style={{ clipPath: 'inset(0 0 0 50%)' }}>V</span>
            </span>
            <span className="ml-1 text-[10px] font-bold tracking-widest text-[#E25C1D] uppercase border border-[#E25C1D]/30 px-1.5 py-0.5 rounded-md align-middle">AI</span>
          </span>
        </div>

        <nav className="hidden md:flex items-center gap-6">
          <button 
            onClick={() => setCurrentScreen('home')} 
            className={`font-semibold text-sm transition-all py-1.5 px-3.5 rounded-xl flex items-center gap-2 ${currentScreen === 'home' ? 'bg-[#E25C1D]/10 text-[#E25C1D] font-bold' : `hover:text-[#E25C1D] ${darkMode ? 'text-slate-300 hover:bg-slate-800/20' : 'text-[#5B6B6B] hover:bg-gray-200/50'}`}`}
          >
            Inicio
          </button>
          <button 
            onClick={() => setCurrentScreen('assistant')} 
            className={`font-semibold text-sm transition-all py-1.5 px-3.5 rounded-xl flex items-center gap-2 ${currentScreen === 'assistant' ? 'bg-[#E25C1D]/10 text-[#E25C1D] font-bold' : `hover:text-[#E25C1D] ${darkMode ? 'text-slate-300 hover:bg-slate-800/20' : 'text-[#5B6B6B] hover:bg-gray-200/50'}`}`}
          >
            Hablar
          </button>
          <button 
            onClick={() => setCurrentScreen('teaching')} 
            className={`font-semibold text-sm transition-all py-1.5 px-3.5 rounded-xl flex items-center gap-2 ${currentScreen === 'teaching' ? 'bg-[#E25C1D]/10 text-[#E25C1D] font-bold' : `hover:text-[#E25C1D] ${darkMode ? 'text-slate-300 hover:bg-slate-800/20' : 'text-[#5B6B6B] hover:bg-gray-200/50'}`}`}
          >
            Entrenar Visión
          </button>
          <button 
            onClick={() => setCurrentScreen('settings')} 
            className={`font-semibold text-sm transition-all py-1.5 px-3.5 rounded-xl flex items-center gap-2 ${currentScreen === 'settings' ? 'bg-[#E25C1D]/10 text-[#E25C1D] font-bold' : `hover:text-[#E25C1D] ${darkMode ? 'text-slate-300 hover:bg-slate-800/20' : 'text-[#5B6B6B] hover:bg-gray-200/50'}`}`}
          >
            Configuración
          </button>
        </nav>

        <div className="flex items-center gap-4">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${wsConnected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400 animate-pulse'}`}></span>
            {wsConnected ? 'Conectado' : 'Reconectando...'}
          </span>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            className={`p-2 rounded-xl transition-all ${darkMode ? 'bg-orange-950/40 text-[#E25C1D] border border-orange-500/10' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
            title="Cambiar Tema"
          >
            {darkMode ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-11.314l.707.707m11.314 11.314l.707.707M12 17a5 5 0 110-10 5 5 0 010 10z"/></svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
            )}
          </button>
        </div>
      </header>

      {/* CONTENEDOR PRINCIPAL */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 flex flex-col justify-center items-center relative">
        
        {/* PANTALLA 1: INICIO */}
        {currentScreen === 'home' && (
          <div className="w-full max-w-3xl text-center space-y-12 py-8 animate-fade-in">
            <div className="relative flex justify-center items-center h-52">
              <div className="absolute w-44 h-44 rounded-full bg-[#E25C1D] opacity-15 filter blur-3xl animate-pulse"></div>
              <div className="absolute w-36 h-36 rounded-full border-2 border-dashed border-[#E25C1D]/20 organic-orb"></div>
              <div className="relative w-24 h-24 rounded-full bg-gradient-to-tr from-[#E25C1D] to-orange-400 flex items-center justify-center shadow-xl shadow-[#E25C1D]/25 transition-all duration-500 transform hover:scale-110">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>
              </div>
            </div>

            <div className="space-y-4">
              <h1 className={`text-4xl md:text-5xl font-extrabold tracking-tight leading-tight ${darkMode ? 'text-slate-100' : 'text-[#1C2D5A]'}`}>
                Hola, soy el asistente de <span className="text-[#E25C1D]">IA de la UNEV</span>.
              </h1>
              <p className={`text-lg md:text-xl font-medium max-w-xl mx-auto ${darkMode ? 'text-slate-300' : 'text-[#5B6B6B]'}`}>
                Háblame o escribe consultas. Estoy sincronizado con tu holograma local en tiempo real.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button 
                onClick={handleStartConversation}
                className="w-full sm:w-auto px-8 py-4 bg-[#E25C1D] hover:bg-orange-600 active:scale-95 text-white text-base font-bold rounded-2xl shadow-xl shadow-[#E25C1D]/20 flex items-center justify-center gap-3 transition-all"
              >
                Comenzar a hablar
              </button>
              
              <button 
                onClick={() => {
                  setIsConversationActive(true);
                  setCurrentScreen('assistant');
                  setCameraOn(true);
                  setAssistantState('listening');
                  sendPrompt("saludar");
                }}
                className={`w-full sm:w-auto px-8 py-4 border-2 font-bold text-base rounded-2xl flex items-center justify-center gap-3 transition-all ${darkMode ? 'border-orange-500/30 hover:bg-orange-500/10 text-orange-300' : 'border-[#E25C1D] hover:bg-orange-500/5 text-[#E25C1D]'}`}
              >
                Usar la cámara
              </button>
            </div>
          </div>
        )}

        {/* PANTALLA 2: ASISTENTE EN VIVO */}
        {currentScreen === 'assistant' && (
          <div className="w-full max-w-5xl rounded-3xl p-8 relative min-h-[580px] flex flex-col justify-between transition-all bg-[#0B0F19]/95 border border-slate-800 shadow-2xl text-white">
            
            <div className="flex justify-between items-center w-full absolute top-6 left-0 px-8">
              <span className="text-[#E25C1D] font-bold text-sm tracking-wide">UNEV AI Assistant</span>
            </div>

            {/* PIP VIEWPORT DE LA CÁMARA */}
            <div className="absolute top-16 right-8 z-30">
              {yoloEnabled && cameraOn ? (
                <div className="w-56 h-36 rounded-2xl overflow-hidden border border-slate-800 shadow-lg relative bg-slate-950 flex items-center justify-center">
                  <video 
                    ref={videoRef}
                    autoPlay 
                    playsInline 
                    muted 
                    className="w-full h-full object-cover opacity-80"
                  />
                  <div className="absolute top-2 left-2 bg-slate-900/95 border border-red-500/40 px-2 py-0.5 rounded-full flex items-center gap-1 text-[9px] text-white font-semibold">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse"></span>
                    <span>LIVE</span>
                  </div>
                  <div className="absolute inset-x-6 inset-y-8 border border-[#E25C1D]/40 bg-[#E25C1D]/5 rounded flex items-center justify-center text-[10px] text-[#E25C1D] font-extrabold">
                    Detector YOLO
                  </div>
                </div>
              ) : (
                <div className="w-56 h-36 rounded-2xl border border-slate-800 bg-slate-900/80 flex flex-col items-center justify-center p-3 text-center">
                  <span className="text-[10px] text-slate-500 font-bold">Cámara apagada</span>
                </div>
              )}
            </div>

            {/* ORBE CENTRAL DE VOZ */}
            <div className="flex flex-col items-center justify-center mt-12 w-full">
              <div 
                onClick={startSpeechRecognition}
                className="relative flex justify-center items-center h-48 w-48 mb-6 cursor-pointer hover:scale-105 transition-all"
                title="Presiona para hablar"
              >
                <div className="absolute w-40 h-40 rounded-full bg-[#E25C1D] opacity-10 filter blur-xl animate-pulse"></div>
                <div className="absolute w-36 h-36 rounded-full bg-[#0B0F19] border border-slate-800 flex items-center justify-center">
                  <div className="absolute w-32 h-32 rounded-full border border-orange-500/20 spin-slow"></div>
                  <div className="relative w-24 h-24 rounded-full bg-gradient-to-tr from-[#0F172A] to-[#2B1B15] border-2 border-[#E25C1D]/40 flex items-center justify-center shadow-inner">
                    <div className="flex items-end gap-1.5 h-10">
                      <span className="w-1 bg-[#E25C1D] rounded-full animate-pulse h-6" style={{ animationDelay: '0.1s' }}></span>
                      <span className="w-1 bg-orange-400 rounded-full animate-pulse h-10" style={{ animationDelay: '0.3s' }}></span>
                      <span className="w-1 bg-[#E25C1D] rounded-full animate-pulse h-8" style={{ animationDelay: '0.5s' }}></span>
                      <span className="w-1 bg-orange-400 rounded-full animate-pulse h-5" style={{ animationDelay: '0.2s' }}></span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* CAPTIONS DE ALTA VISIBILIDAD */}
            <div className="max-w-3xl mx-auto text-center space-y-6 px-4">
              <h2 className="text-2xl md:text-3xl font-normal leading-relaxed text-slate-100 tracking-wide">
                {renderHighlightedText(aiSpokenText, highlightKeyword)}
              </h2>
              
              <div className="flex items-center justify-center gap-2.5 text-xs text-slate-400 font-medium">
                {assistantState === 'thinking' && (
                  <svg className="w-4 h-4 text-[#E25C1D] animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                <span>{userSpokenText}</span>
              </div>
            </div>

            {/* CHIPS DE RESPUESTA SUGERIDA */}
            <div className="flex flex-wrap justify-center items-center gap-3 mt-6">
              <button 
                onClick={() => sendPrompt("saludar")}
                className="px-5 py-2.5 rounded-full border border-slate-800 bg-slate-900/60 hover:bg-slate-800 hover:border-[#E25C1D]/40 text-xs font-semibold text-slate-300 hover:text-white transition-all shadow-sm"
              >
                Saludar
              </button>
              <button 
                onClick={() => sendPrompt("backend")}
                className="px-5 py-2.5 rounded-full border border-slate-800 bg-slate-900/60 hover:bg-slate-800 hover:border-[#E25C1D]/40 text-xs font-semibold text-slate-300 hover:text-white transition-all shadow-sm"
              >
                Chequear Backend
              </button>
              <button 
                onClick={() => sendPrompt("ayuda")}
                className="px-5 py-2.5 rounded-full border border-slate-800 bg-slate-900/60 hover:bg-slate-800 hover:border-[#E25C1D]/40 text-xs font-semibold text-slate-300 hover:text-white transition-all shadow-sm"
              >
                Ayuda
              </button>
            </div>

            {/* CONSOLA DE ACCIÓN DE CONTROL INFERIOR */}
            <div className="flex justify-center items-center mt-8 pb-4">
              <div className="flex items-center justify-between gap-6 px-6 py-3 bg-[#0B0F19]/90 border border-slate-800 rounded-full shadow-xl">
                <button 
                  onClick={() => setTextInputOpen(!textInputOpen)}
                  className={`p-2 rounded-full transition-all ${textInputOpen ? 'text-[#E25C1D] bg-[#E25C1D]/10' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
                  title="Escribir comando"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                  </svg>
                </button>

                <button 
                  onClick={handleEndConversation}
                  className="p-3.5 bg-rose-600 hover:bg-rose-700 text-white rounded-full transition-all shadow-md active:scale-95 flex items-center justify-center animate-pulse"
                  title="Detener sesión de voz"
                >
                  <div className="w-3 h-3 bg-rose-200 rounded-[3px]"></div>
                </button>

                <button 
                  onClick={() => {
                    setCameraOn(!cameraOn);
                    showToast(cameraOn ? "Cámara apagada." : "Cámara encendida.");
                  }}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full"
                  title="Visor de cámara"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Caja de consulta de texto manual */}
            {textInputOpen && (
              <div className="absolute bottom-24 left-1/2 transform -translate-x-1/2 w-full max-w-md p-4 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl flex gap-2">
                <input 
                  type="text" 
                  value={customQuery}
                  onChange={(e) => setCustomQuery(e.target.value)}
                  placeholder="Escribe tu consulta al holograma..."
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#E25C1D]"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      sendPrompt(customQuery);
                      setCustomQuery('');
                      setTextInputOpen(false);
                    }
                  }}
                />
                <button 
                  onClick={() => {
                    sendPrompt(customQuery);
                    setCustomQuery('');
                    setTextInputOpen(false);
                  }}
                  className="px-4 py-2 bg-[#E25C1D] hover:bg-orange-600 rounded-xl text-xs font-bold"
                >
                  Enviar
                </button>
              </div>
            )}

          </div>
        )}

        {/* PANTALLA 3: CONFIGURACIÓN */}
        {currentScreen === 'settings' && (
          <div className={`w-full max-w-4xl space-y-6 py-4 ${darkMode ? 'text-slate-100' : 'text-slate-800'}`}>
            <div className={`flex justify-between items-center pb-4 border-b ${darkMode ? 'border-slate-800' : 'border-gray-200'}`}>
              <div>
                <h1 className={`text-2xl font-black ${darkMode ? 'text-white' : 'text-[#1C2D5A]'}`}>Portal de Configuración</h1>
                <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Establece preferencias del Cerebro de la IA y el hardware</p>
              </div>
            </div>

            <div className="columns-1 md:columns-2 gap-6 space-y-6 md:space-y-0 [column-fill:balance]">
              {/* Apariencia */}
              <div className={`break-inside-avoid inline-block w-full mb-6 p-6 rounded-3xl border shadow-sm space-y-4 ${darkMode ? 'bg-[#131E3B] border-slate-800' : 'bg-white border-gray-200 text-slate-800'}`}>
                <h3 className="font-bold text-sm uppercase tracking-wider text-[#E25C1D]">Apariencia</h3>
                <div className="space-y-2">
                  <div className={`grid grid-cols-3 gap-2 p-1 rounded-xl ${darkMode ? 'bg-slate-900/60' : 'bg-gray-100'}`}>
                    {['light', 'dark', 'system'].map((theme) => (
                      <button 
                        key={theme}
                        onClick={() => setAppearanceTheme(theme)}
                        className={`py-2 text-xs font-bold uppercase rounded-lg transition-all ${appearanceTheme === theme ? 'bg-[#E25C1D] text-white shadow-md' : (darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900')}`}
                      >
                        {theme}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Cerebro de la IA (Local vs API Key) */}
              <div className={`break-inside-avoid inline-block w-full mb-6 p-6 rounded-3xl border shadow-sm space-y-4 ${darkMode ? 'bg-[#131E3B] border-slate-800' : 'bg-white border-gray-200 text-slate-800'}`}>
                <h3 className="font-bold text-sm uppercase tracking-wider text-[#E25C1D]">Modelo del Cerebro</h3>
                <div className={`grid grid-cols-2 gap-2 p-1 rounded-xl ${darkMode ? 'bg-slate-900/60' : 'bg-gray-100'}`}>
                  <button 
                    onClick={() => setAiEngine('local')}
                    className={`py-2 text-xs font-bold uppercase rounded-lg transition-all ${aiEngine === 'local' ? 'bg-[#E25C1D] text-white shadow-md' : (darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900')}`}
                  >
                    Local (Ollama)
                  </button>
                  <button 
                    onClick={() => setAiEngine('api')}
                    className={`py-2 text-xs font-bold uppercase rounded-lg transition-all ${aiEngine === 'api' ? 'bg-[#E25C1D] text-white shadow-md' : (darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900')}`}
                  >
                    API Key
                  </button>
                </div>

                {aiEngine === 'local' ? (
                  <div className="space-y-3 pt-2">
                    <label className={`text-xs font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Seleccionar Modelo Ollama</label>
                    <select 
                      value={selectedLocalModel}
                      onChange={(e) => setSelectedLocalModel(e.target.value)}
                      className={`w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-gray-300 text-slate-800'}`}
                    >
                      <option value="gemma:4b">Gemma 4b - Ligero y Veloz</option>
                      <option value="qwen3.7:8b">qwen3.7:8b - Razonamiento Avanzado</option>
                      <option value="llama3.2:3b">Llama 3.2 3b - Optimizado</option>
                    </select>
                  </div>
                ) : (
                  <div className="space-y-3 pt-2">
                    <div>
                      <label className={`text-xs font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Proveedor API</label>
                      <select 
                        value={apiProvider}
                        onChange={(e) => setApiProvider(e.target.value)}
                        className={`w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-gray-300 text-slate-800'}`}
                      >
                        <option value="openrouter">OpenRouter</option>
                        <option value="openai">OpenAI</option>
                        <option value="claude_native">Anthropic (Claude)</option>
                        <option value="nvidia">NVIDIA NIM</option>
                      </select>
                    </div>
                    <div>
                      <label className={`text-xs font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Modelo Remoto</label>
                      <input 
                        type="text" 
                        value={apiModel}
                        onChange={(e) => setApiModel(e.target.value)}
                        placeholder="meta-llama/llama-3.3-70b-instruct"
                        className={`w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-gray-300 text-slate-800'}`}
                      />
                    </div>
                    <div>
                      <label className={`text-xs font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>API Key</label>
                      <input 
                        type="password" 
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="••••••••••••••••"
                        className={`w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-gray-300 text-slate-800'}`}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Cámara y Visión (YOLOe26) */}
              <div className={`break-inside-avoid inline-block w-full mb-6 p-6 rounded-3xl border shadow-sm space-y-4 ${darkMode ? 'bg-[#131E3B] border-slate-800' : 'bg-white border-gray-200 text-slate-800'}`}>
                <h3 className="font-bold text-sm uppercase tracking-wider text-[#E25C1D]">Detección Visual YOLOe26</h3>
                <div className={`grid grid-cols-2 gap-2 p-1 rounded-xl ${darkMode ? 'bg-slate-900/60' : 'bg-gray-100'}`}>
                  <button 
                    onClick={() => setYoloEnabled(true)}
                    className={`py-2 text-xs font-bold uppercase rounded-lg transition-all ${yoloEnabled ? 'bg-[#E25C1D] text-white shadow-md' : (darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900')}`}
                  >
                    Activo (ON)
                  </button>
                  <button 
                    onClick={() => setYoloEnabled(false)}
                    className={`py-2 text-xs font-bold uppercase rounded-lg transition-all ${!yoloEnabled ? 'bg-[#E25C1D] text-white shadow-md' : (darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900')}`}
                  >
                    Inactivo (OFF)
                  </button>
                </div>

                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Intervalo de detección</span>
                    <span className="font-extrabold text-[#E25C1D]">{yoloInterval} seg</span>
                  </div>
                  <input 
                    type="range" 
                    min="0.1" 
                    max="5.0" 
                    step="0.1"
                    value={yoloInterval}
                    onChange={(e) => setYoloInterval(e.target.value)}
                    className="w-full h-1.5 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-[#E25C1D]"
                  />
                </div>
              </div>

              {/* Reconocimiento de Voz */}
              <div className={`break-inside-avoid inline-block w-full mb-6 p-6 rounded-3xl border shadow-sm space-y-4 ${darkMode ? 'bg-[#131E3B] border-slate-800' : 'bg-white border-gray-200 text-slate-800'}`}>
                <h3 className="font-bold text-sm uppercase tracking-wider text-[#E25C1D]">Transcripción de Voz (Whisper)</h3>
                <div className={`grid grid-cols-2 gap-2 p-1 rounded-xl ${darkMode ? 'bg-slate-900/60' : 'bg-gray-100'}`}>
                  {['small', 'medium'].map((size) => (
                    <button 
                      key={size}
                      onClick={() => setWhisperSize(size)}
                      className={`py-2 text-xs font-bold rounded-lg transition-all uppercase ${whisperSize === size ? 'bg-[#E25C1D] text-white shadow-md' : (darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900')}`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Síntesis de voz (Piper) */}
            <div className={`p-6 rounded-3xl border shadow-sm space-y-4 ${darkMode ? 'bg-[#131E3B] border-slate-800' : 'bg-white border-gray-200 text-slate-800'}`}>
              <h3 className="font-bold text-sm uppercase tracking-wider text-[#E25C1D]">Síntesis de Voz (Piper)</h3>
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
                <div className="flex-1">
                  <select 
                    value={piperVoice}
                    onChange={(e) => setPiperVoice(e.target.value)}
                    className={`w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-gray-300 text-slate-800'}`}
                  >
                    {voicesList.map((voice) => (
                      <option key={voice} value={voice}>{voice}</option>
                    ))}
                  </select>
                </div>
                <button 
                  onClick={handlePlayVoicePreview}
                  className={`px-5 py-3.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shrink-0 ${isPlayingVoiceSample ? 'bg-[#E25C1D]/20 text-[#E25C1D] border border-[#E25C1D]/50 animate-pulse' : 'bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300'}`}
                >
                  Probar Voz
                </button>
              </div>
            </div>

            <div className="pt-4 flex justify-end">
              <button 
                onClick={saveConfig}
                className="w-full sm:w-auto px-8 py-4 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-sm rounded-2xl shadow-xl shadow-[#E25C1D]/10 transition-all text-center"
              >
                Guardar y aplicar cambios
              </button>
            </div>
          </div>
        )}

        {/* PANTALLA 4: ENTRENAR VISIÓN */}
        {currentScreen === 'teaching' && (
          <div className={`w-full max-w-5xl space-y-6 py-4 ${darkMode ? 'text-slate-100' : 'text-slate-800'}`}>
            <div className={`pb-4 border-b ${darkMode ? 'border-slate-800' : 'border-gray-200'}`}>
              <h1 className={`text-2xl font-black ${darkMode ? 'text-white' : 'text-[#1C2D5A]'}`}>Entrena la visión de la IA</h1>
              <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Define referencias visuales para el modelo espacial YOLO</p>
            </div>

            <div className={`flex border-b ${darkMode ? 'border-slate-800' : 'border-gray-200'}`}>
              <button 
                onClick={() => setTeachingTab('visual')}
                className={`py-3 px-6 text-sm font-bold border-b-2 transition-all ${teachingTab === 'visual' ? 'border-[#E25C1D] text-[#E25C1D]' : `border-transparent ${darkMode ? 'text-slate-400 hover:text-[#E25C1D]' : 'text-slate-500 hover:text-[#E25C1D]'}`}`}
              >
                Entrenamiento Visual
              </button>
              <button 
                onClick={() => setTeachingTab('text')}
                className={`py-3 px-6 text-sm font-bold border-b-2 transition-all ${teachingTab === 'text' ? 'border-[#E25C1D] text-[#E25C1D]' : `border-transparent ${darkMode ? 'text-slate-400 hover:text-[#E25C1D]' : 'text-slate-500 hover:text-[#E25C1D]'}`}`}
              >
                Vocabulario Rápido
              </button>
            </div>

            {teachingTab === 'visual' ? (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                <div className="lg:col-span-8 flex flex-col space-y-4">
                  <div className={`flex-1 rounded-3xl border-2 border-dashed p-6 flex flex-col items-center justify-center min-h-[350px] relative transition-all ${
                    uploadedImage 
                      ? (darkMode ? 'border-[#E25C1D]/50 bg-slate-900/10' : 'border-[#E25C1D]/50 bg-orange-50')
                      : (darkMode ? 'border-slate-800 bg-slate-900/10' : 'border-gray-300 bg-gray-50')
                  }`}>
                    {uploadedImage ? (
                      <div className="relative max-w-full overflow-hidden select-none">
                        <img src={uploadedImage} alt="Referencia" className="max-h-[350px] rounded-xl object-contain pointer-events-none" />
                        <div 
                          ref={canvasRef}
                          onMouseDown={handleCanvasMouseDown}
                          onMouseMove={handleCanvasMouseMove}
                          onMouseUp={handleCanvasMouseUp}
                          className="absolute inset-0 w-full h-full cursor-crosshair z-20"
                        >
                          {boundingBoxes.map((box, idx) => (
                            <div 
                              key={idx}
                              className="absolute border-2 border-[#E25C1D] bg-[#E25C1D]/25 flex flex-col justify-between p-1 text-white"
                              style={{ left: box.x, top: box.y, width: box.w, height: box.h }}
                            >
                              <span className="text-[9px] font-bold bg-[#E25C1D] px-1 rounded">{box.label}</span>
                            </div>
                          ))}
                          {tempBox && (
                            <div 
                              className="absolute border-2 border-dashed border-[#E25C1D] bg-[#E25C1D]/15"
                              style={{ left: tempBox.x, top: tempBox.y, width: tempBox.w, height: tempBox.h }}
                            />
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center space-y-4 p-8">
                        <p className="font-bold">Elige una imagen de ejemplo</p>
                        <div className="flex justify-center gap-2">
                          <button 
                            onClick={() => setUploadedImage('https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&q=80&w=800')}
                            className="px-3 py-1.5 bg-[#E25C1D]/10 text-[#E25C1D] text-xs font-bold rounded-lg border border-[#E25C1D]/20 hover:bg-[#E25C1D]/20"
                          >
                            Muestra: Carnet
                          </button>
                          <button 
                            onClick={() => setUploadedImage('https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&q=80&w=800')}
                            className="px-3 py-1.5 bg-[#E25C1D]/10 text-[#E25C1D] text-xs font-bold rounded-lg border border-[#E25C1D]/20 hover:bg-[#E25C1D]/20"
                          >
                            Muestra: Telescopio
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {uploadedImage && (
                    <div className={`p-4 rounded-2xl border space-y-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-gray-200'}`}>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <label className={`text-[10px] uppercase tracking-wider font-bold ${darkMode ? 'text-gray-500' : 'text-gray-600'}`}>Clase del Objeto</label>
                          <input 
                            type="text" 
                            value={currentLabel}
                            onChange={(e) => setCurrentLabel(e.target.value)}
                            className={`w-full text-sm p-2.5 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-[#0B0F19] border-slate-800 text-white' : 'bg-white border-gray-300 text-slate-800'}`}
                          />
                        </div>
                        <div className="space-y-1">
                          <label className={`text-[10px] uppercase tracking-wider font-bold ${darkMode ? 'text-gray-500' : 'text-gray-600'}`}>Descripción Semántica</label>
                          <input 
                            type="text" 
                            value={currentDesc}
                            onChange={(e) => setCurrentDesc(e.target.value)}
                            className={`w-full text-sm p-2.5 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-[#0B0F19] border-slate-800 text-white' : 'bg-white border-gray-300 text-slate-800'}`}
                          />
                        </div>
                      </div>

                      <div className="flex justify-between items-center pt-2">
                        <button 
                          onClick={() => setBoundingBoxes(boundingBoxes.slice(0, -1))}
                          className={`px-4 py-2 text-xs font-bold rounded-xl ${darkMode ? 'bg-slate-950 hover:bg-rose-500/10 text-rose-400' : 'bg-rose-50 hover:bg-rose-100 text-rose-600'}`}
                        >
                          Deshacer caja
                        </button>
                        <div className="flex gap-2">
                          <button 
                            onClick={() => setUploadedImage(null)}
                            className={`px-4 py-2 text-xs font-bold rounded-xl ${darkMode ? 'text-rose-500 hover:bg-rose-500/10' : 'text-rose-600 hover:bg-rose-50'}`}
                          >
                            Cancelar
                          </button>
                          <button 
                            onClick={handleSaveTeaching}
                            className="px-6 py-2.5 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-xs rounded-xl"
                          >
                            Guardar y entrenar
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className={`lg:col-span-4 rounded-3xl p-6 border flex flex-col space-y-4 ${darkMode ? 'bg-[#131E3B] border-slate-800' : 'bg-white border-gray-200 shadow-sm'}`}>
                  <h3 className="font-extrabold text-sm text-[#E25C1D] uppercase tracking-widest">Base de Datos YOLO</h3>
                  <div className="flex-1 overflow-y-auto space-y-3 max-h-[400px]">
                    {savedTeachingObjects.map((item) => (
                      <div key={item.id} className={`p-2.5 rounded-2xl border flex items-center gap-3 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-gray-50 border-gray-200'}`}>
                        <img src={item.thumbnail} alt={item.label} className="w-12 h-12 rounded-xl object-cover shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className={`font-bold text-xs truncate ${darkMode ? 'text-white' : 'text-slate-800'}`}>{item.label}</p>
                          <p className={`text-[10px] truncate ${darkMode ? 'text-gray-500' : 'text-gray-600'}`}>{item.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className={`p-8 rounded-3xl border text-center space-y-6 ${darkMode ? 'bg-[#131E3B] border-slate-800' : 'bg-white border-gray-200 shadow-sm'}`}>
                <div className="max-w-md mx-auto space-y-4">
                  <h3 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-slate-800'}`}>Vocabulario abierto instantáneo</h3>
                  <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                    Define términos que el modelo de visión identificará sin requerir bounding boxes. Separa los elementos por comas.
                  </p>
                  <textarea 
                    id="vocabList"
                    rows={3} 
                    defaultValue="mochila, cuaderno, laptop, credencial de estudiante, telefono"
                    className={`w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] ${darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-gray-50 border-gray-300 text-slate-800'}`}
                  />
                  <button 
                    onClick={() => {
                      const el = document.getElementById('vocabList') as HTMLTextAreaElement;
                      if (el) handleCompileVocabulary(el.value);
                    }}
                    className="w-full py-3 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition-all"
                  >
                    Compilar términos
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* PIP VIEWPORT REPRODUCTOR FLOTANTE */}
        {pipVisible && (
          <div 
            style={{ left: `${pipPosition.x}%`, top: `${pipPosition.y}%` }}
            onMouseMove={handlePipDragMove}
            onMouseUp={() => setDragStart(null)}
            onMouseLeave={() => setDragStart(null)}
            className="fixed w-64 p-3 rounded-2xl shadow-2xl backdrop-blur-md bg-slate-900/95 border border-[#E25C1D]/30 select-none z-50 cursor-grab flex items-stretch gap-2"
          >
            <div onMouseDown={handlePipDragStart} className="flex flex-col justify-center gap-1 cursor-grabbing p-1 text-[#E25C1D]">
              <div className="w-1.5 h-1.5 rounded-full bg-[#E25C1D]"></div>
              <div className="w-1.5 h-1.5 rounded-full bg-[#E25C1D]"></div>
              <div className="w-1.5 h-1.5 rounded-full bg-[#E25C1D]"></div>
            </div>

            <div className="flex-1 min-w-0 flex flex-col justify-center gap-2 text-white relative">
              <div className="w-full h-36 rounded-xl overflow-hidden border border-slate-800 relative bg-slate-950 flex items-center justify-center">
                <img 
                  src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&q=80&w=350" 
                  alt="Inferencia en tiempo real PIP" 
                  className="w-full h-full object-cover opacity-60 pointer-events-none"
                />
                <div className="absolute top-1 left-1 bg-slate-900/95 border border-red-500/40 px-1.5 py-0.5 rounded-full flex items-center gap-1 text-[8px] text-white font-semibold">
                  <span className="h-1 w-1 rounded-full bg-red-500 animate-pulse"></span>
                  <span>LIVE</span>
                </div>
              </div>
              
              <button 
                onClick={() => setCurrentScreen('assistant')}
                className="absolute top-1 right-1 p-1.5 bg-slate-900/80 hover:bg-[#E25C1D] text-white rounded-lg text-xs border border-slate-700 hover:border-[#E25C1D] transition-colors"
                title="Maximizar al Asistente"
              >
                ⛶
              </button>
            </div>
          </div>
        )}

      </main>

      {/* MOBILE NAV BAR */}
      <div className={`md:hidden sticky bottom-0 z-40 border-t flex justify-around items-center py-3.5 backdrop-blur-md transition-colors ${darkMode ? 'bg-[#0B0F19]/95 border-slate-850 text-white' : 'bg-white/95 border-gray-200 text-[#1C2D5A]'}`}>
        <button onClick={() => setCurrentScreen('home')} className={`flex flex-col items-center gap-1 text-[10px] font-bold ${currentScreen === 'home' ? 'text-[#E25C1D]' : (darkMode ? 'text-slate-400' : 'text-[#5B6B6B]')}`}>
          Inicio
        </button>
        <button onClick={() => setCurrentScreen('assistant')} className={`flex flex-col items-center gap-1 text-[10px] font-bold ${currentScreen === 'assistant' ? 'text-[#E25C1D]' : (darkMode ? 'text-slate-400' : 'text-[#5B6B6B]')}`}>
          Hablar
        </button>
        <button onClick={() => setCurrentScreen('teaching')} className={`flex flex-col items-center gap-1 text-[10px] font-bold ${currentScreen === 'teaching' ? 'text-[#E25C1D]' : (darkMode ? 'text-slate-400' : 'text-[#5B6B6B]')}`}>
          Entrenar
        </button>
        <button onClick={() => setCurrentScreen('settings')} className={`flex flex-col items-center gap-1 text-[10px] font-bold ${currentScreen === 'settings' ? 'text-[#E25C1D]' : (darkMode ? 'text-slate-400' : 'text-[#5B6B6B]')}`}>
          Ajustes
        </button>
      </div>

    </div>
  );
}
