import { useRef, useState } from 'react';
import type { DragEvent as ReactDragEvent, MouseEvent as ReactMouseEvent } from 'react';
import { useSession } from '../context/SessionContext';
import { useToast } from '../context/ToastContext';
import { apiFetch, mediaUrl } from '../lib/backend';
import type { BoundingBox } from '../types';

export function TeachingScreen() {
  const showToast = useToast();
  const { config } = useSession();

  const [teachingTab, setTeachingTab] = useState<'visual' | 'text'>('visual');
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [boundingBoxes, setBoundingBoxes] = useState<BoundingBox[]>([]);
  const [currentLabel, setCurrentLabel] = useState('Carnet UNEV');
  const [currentDesc, setCurrentDesc] = useState('Identificación estudiantil oficial');
  const [dragOver, setDragOver] = useState(false);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState({ x: 0, y: 0 });
  const [tempBox, setTempBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  const canvasRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const readImage = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => setUploadedImage(reader.result as string);
    reader.readAsDataURL(file);
  };

  const onDrop = (e: ReactDragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) readImage(file);
  };

  const onCanvasDown = (e: ReactMouseEvent) => {
    if (!uploadedImage || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setIsDrawing(true);
    setDrawStart({ x, y });
    setTempBox({ x, y, w: 0, h: 0 });
  };

  const onCanvasMove = (e: ReactMouseEvent) => {
    if (!isDrawing || !tempBox || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    setTempBox({
      x: Math.min(drawStart.x, cx),
      y: Math.min(drawStart.y, cy),
      w: Math.abs(cx - drawStart.x),
      h: Math.abs(cy - drawStart.y),
    });
  };

  const onCanvasUp = () => {
    if (!isDrawing) return;
    setIsDrawing(false);
    if (tempBox && tempBox.w > 10 && tempBox.h > 10) {
      setBoundingBoxes([...boundingBoxes, { ...tempBox, label: currentLabel, desc: currentDesc }]);
    }
    setTempBox(null);
  };

  const saveTeaching = async () => {
    if (boundingBoxes.length === 0) {
      showToast('Dibuja un cuadro sobre el objeto primero.');
      return;
    }
    try {
      const res = await apiFetch('/api/train/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: uploadedImage, boundingBoxes }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.items) config.setSavedTeachingObjects(data.items);
        setBoundingBoxes([]);
        setUploadedImage(null);
        showToast('¡Objeto guardado y entrenado con éxito!');
      } else {
        showToast('Error al enviar el entrenamiento al servidor.');
      }
    } catch {
      showToast('Error de red al guardar el entrenamiento.');
    }
  };

  const compileVocabulary = async (terms: string) => {
    try {
      const res = await apiFetch('/api/train/vocabulary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vocabulary: terms }),
      });
      showToast(res.ok ? 'Vocabulario textual cargado al motor YOLO.' : 'Error al compilar el vocabulario.');
    } catch {
      showToast('Error de red al compilar vocabulario.');
    }
  };

  const tabClass = (active: boolean) =>
    `py-3 px-6 text-sm font-bold border-b-2 transition-all ${
      active ? 'border-[#E25C1D] text-[#E25C1D]' : 'border-transparent text-slate-500 hover:text-[#E25C1D] dark:text-slate-400'
    }`;

  return (
    <div className="w-full max-w-5xl space-y-6 py-4 text-slate-800 dark:text-slate-100">
      <div className="pb-4 border-b border-gray-200 dark:border-slate-800">
        <h1 className="text-2xl font-black text-[#1C2D5A] dark:text-white">Entrena la visión de la IA</h1>
        <p className="text-xs text-gray-600 dark:text-gray-400">Define referencias visuales para el modelo espacial YOLO</p>
      </div>

      <div className="flex border-b border-gray-200 dark:border-slate-800">
        <button onClick={() => setTeachingTab('visual')} className={tabClass(teachingTab === 'visual')}>
          Entrenamiento Visual
        </button>
        <button onClick={() => setTeachingTab('text')} className={tabClass(teachingTab === 'text')}>
          Vocabulario Rápido
        </button>
      </div>

      {teachingTab === 'visual' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          <div className="lg:col-span-8 flex flex-col space-y-4">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => !uploadedImage && fileInputRef.current?.click()}
              className={`flex-1 rounded-3xl border-2 border-dashed p-6 flex flex-col items-center justify-center min-h-[350px] relative transition-all cursor-pointer ${
                uploadedImage
                  ? 'border-[#E25C1D]/50 bg-orange-50 dark:bg-slate-900/10'
                  : dragOver
                    ? 'border-[#E25C1D] bg-[#E25C1D]/10'
                    : 'border-gray-300 bg-gray-50 dark:border-slate-800 dark:bg-slate-900/10'
              }`}
            >
              {uploadedImage ? (
                <div className="relative max-w-full overflow-hidden select-none">
                  <img src={uploadedImage} alt="Referencia" className="max-h-[350px] rounded-xl object-contain pointer-events-none" />
                  <div
                    ref={canvasRef}
                    onMouseDown={onCanvasDown}
                    onMouseMove={onCanvasMove}
                    onMouseUp={onCanvasUp}
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
                  <p className="font-bold">Arrastra una imagen o haz clic aquí</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">O elige una imagen de ejemplo</p>
                  <div className="flex justify-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setUploadedImage('https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&q=80&w=800');
                      }}
                      className="px-3 py-1.5 bg-[#E25C1D]/10 text-[#E25C1D] text-xs font-bold rounded-lg border border-[#E25C1D]/20 hover:bg-[#E25C1D]/20"
                    >
                      Muestra: Carnet
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setUploadedImage('https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&q=80&w=800');
                      }}
                      className="px-3 py-1.5 bg-[#E25C1D]/10 text-[#E25C1D] text-xs font-bold rounded-lg border border-[#E25C1D]/20 hover:bg-[#E25C1D]/20"
                    >
                      Muestra: Telescopio
                    </button>
                  </div>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) readImage(file);
                }}
                className="hidden"
              />
            </div>

            {uploadedImage && (
              <div className="p-4 rounded-2xl border space-y-4 bg-white border-gray-200 dark:bg-slate-900 dark:border-slate-800">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] uppercase tracking-wider font-bold text-gray-600 dark:text-gray-500">Clase del Objeto</label>
                    <input
                      type="text"
                      value={currentLabel}
                      onChange={(e) => setCurrentLabel(e.target.value)}
                      className="w-full text-sm p-2.5 rounded-xl border focus:outline-none focus:border-[#E25C1D] bg-white border-gray-300 text-slate-800 dark:bg-[#0B0F19] dark:border-slate-800 dark:text-white"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] uppercase tracking-wider font-bold text-gray-600 dark:text-gray-500">Descripción Semántica</label>
                    <input
                      type="text"
                      value={currentDesc}
                      onChange={(e) => setCurrentDesc(e.target.value)}
                      className="w-full text-sm p-2.5 rounded-xl border focus:outline-none focus:border-[#E25C1D] bg-white border-gray-300 text-slate-800 dark:bg-[#0B0F19] dark:border-slate-800 dark:text-white"
                    />
                  </div>
                </div>
                <div className="flex justify-between items-center pt-2">
                  <button
                    onClick={() => setBoundingBoxes(boundingBoxes.slice(0, -1))}
                    className="px-4 py-2 text-xs font-bold rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-600 dark:bg-slate-950 dark:hover:bg-rose-500/10 dark:text-rose-400"
                  >
                    Deshacer caja
                  </button>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setUploadedImage(null)}
                      className="px-4 py-2 text-xs font-bold rounded-xl text-rose-600 hover:bg-rose-50 dark:text-rose-500 dark:hover:bg-rose-500/10"
                    >
                      Cancelar
                    </button>
                    <button onClick={saveTeaching} className="px-6 py-2.5 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-xs rounded-xl">
                      Guardar y entrenar
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="lg:col-span-4 rounded-3xl p-6 border flex flex-col space-y-4 bg-white border-gray-200 shadow-sm dark:bg-[#131E3B] dark:border-slate-800">
            <h3 className="font-extrabold text-sm text-[#E25C1D] uppercase tracking-widest">Base de Datos YOLO</h3>
            <div className="flex-1 overflow-y-auto space-y-3 max-h-[400px]">
              {config.savedTeachingObjects.map((item) => (
                <div key={item.id} className="p-2.5 rounded-2xl border flex items-center gap-3 bg-gray-50 border-gray-200 dark:bg-slate-900 dark:border-slate-800">
                  <img src={mediaUrl(item.thumbnail)} alt={item.label} className="w-12 h-12 rounded-xl object-cover shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-xs truncate text-slate-800 dark:text-white">
                      <span className="text-[#E25C1D] uppercase text-[9px] mr-1">Clase:</span>
                      {item.label}
                    </p>
                    <p className="text-[10px] truncate text-gray-600 dark:text-gray-400">
                      <span className="font-semibold mr-1 opacity-70">Desc:</span>
                      {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 rounded-3xl border text-center space-y-6 bg-white border-gray-200 shadow-sm dark:bg-[#131E3B] dark:border-slate-800">
          <div className="max-w-md mx-auto space-y-4">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white">Vocabulario abierto instantáneo</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Define términos que el modelo de visión identificará sin requerir bounding boxes. Separa los elementos por comas.
            </p>
            <textarea
              id="vocabList"
              rows={3}
              defaultValue="mochila, cuaderno, laptop, credencial de estudiante, telefono"
              className="w-full text-sm p-3 rounded-xl border focus:outline-none focus:border-[#E25C1D] bg-gray-50 border-gray-300 text-slate-800 dark:bg-slate-900 dark:border-slate-800 dark:text-white"
            />
            <button
              onClick={() => {
                const el = document.getElementById('vocabList') as HTMLTextAreaElement | null;
                if (el) compileVocabulary(el.value);
              }}
              className="w-full py-3 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition-all"
            >
              Compilar términos
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
