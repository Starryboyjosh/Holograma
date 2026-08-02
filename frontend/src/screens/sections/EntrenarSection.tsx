import { useRef, useState } from 'react';
import type { DragEvent as ReactDragEvent, MouseEvent as ReactMouseEvent } from 'react';
import { useSession } from '../../context/SessionContext';
import { useToast } from '../../context/ToastContext';
import { apiFetch, mediaUrl } from '../../lib/backend';
import { ScreenHero } from '../../components/holomind/ScreenHero';
import { Wordmark } from '../../components/holomind/Wordmark';
import { BTN_PRIMARY, GLASS, INPUT_GLASS, SECTION_TITLE } from '../../theme';
import type { BoundingBox } from '../../types';

/**
 * Miniatura de un objeto entrenado, con fallback si el archivo no existe (el
 * catálogo puede desincronizarse del disco — ver main.py `train_image`). Sin
 * esto, un thumbnail roto se ve exactamente igual que "no hay nada" (el icono
 * roto del navegador es casi invisible a 48×48px); con el fallback, al menos
 * se distingue "hay un registro pero falta la imagen" de "no hay registro".
 */
function TrainedThumbnail({ src, label }: { src: string; label: string }) {
  const [broken, setBroken] = useState(false);
  if (broken || !src) {
    return (
      <div
        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[14px] bg-white/10 text-[9px] text-white/50"
        title="Sin miniatura"
      >
        Sin img.
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={label}
      onError={() => setBroken(true)}
      className="h-12 w-12 shrink-0 rounded-[14px] object-cover"
    />
  );
}

/**
 * ENTRENAR VISIÓN (nodo 44:220).
 *
 * El diseño pone esta pantalla sobre fondo navy con arco superior y una tarjeta de
 * cristal. En Figma casi todo el texto está exportado como imagen (por el degradado
 * del titular); aquí se escribe como texto real y el degradado se hace en CSS
 * (`Wordmark`), porque texto rasterizado no es seleccionable, traducible ni legible
 * por un lector de pantalla.
 */
export function EntrenarSection() {
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
  const [tempBox, setTempBox] = useState<{ x: number; y: number; w: number; h: number } | null>(
    null,
  );

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
    // WAVE-18 (I8): normalizar la caja a fracciones de la imagen natural antes
    // de enviarla. La caja se dibuja en píxeles CSS del recorte mostrado
    // (max-h-[350px] object-contain), pero el backend (_crop_training_roi)
    // interpreta x,y,w,h como fracciones (<=1.5) o píxeles de la imagen
    // natural (>1.5). Sin normalizar, una foto grande guardada en píxeles CSS
    // display produce un crop plano -> el logo deja de detectarse.
    const rect = canvasRef.current?.getBoundingClientRect();
    const dw = rect?.width || 1;
    const dh = rect?.height || 1;
    const normalizedBoxes = boundingBoxes.map((b) => ({
      ...b,
      x: b.x / dw,
      y: b.y / dh,
      w: b.w / dw,
      h: b.h / dh,
    }));
    try {
      const res = await apiFetch('/api/train/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: uploadedImage, boundingBoxes: normalizedBoxes }),
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

  const deleteTeachingObject = async (id: number) => {
    try {
      const res = await apiFetch(`/api/train/image/${id}`, { method: 'DELETE' });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        config.setSavedTeachingObjects(data.items);
        showToast('Objeto eliminado.');
      } else {
        showToast(data.message || 'Error al eliminar el objeto.');
      }
    } catch {
      showToast('Error de red al eliminar el objeto.');
    }
  };

  const compileVocabulary = async (terms: string) => {
    try {
      const res = await apiFetch('/api/train/vocabulary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vocabulary: terms }),
      });
      showToast(
        res.ok ? 'Vocabulario textual cargado al motor YOLO.' : 'Error al compilar el vocabulario.',
      );
    } catch {
      showToast('Error de red al compilar vocabulario.');
    }
  };

  return (
    <ScreenHero id="entrenar" backdrop="navy" className="pb-24">
      <div className="mx-auto w-full max-w-6xl px-6">
        <header className="text-center">
          <h1 className="text-[32px] font-normal text-white md:text-[44px]">
            Entrena la visión de <Wordmark>HoloMind</Wordmark>
          </h1>
          <p className="mt-2 text-[16px] font-normal italic text-white/90 md:text-[20px]">
            Define referencias visuales para el modelo espacial Holo
          </p>
        </header>

        {/* Selector de modo (nodos 58:1168 / 50:513). */}
        <div className="mt-8 flex justify-center">
          <div className="inline-flex items-center rounded-[50px] bg-black/20 p-1">
            {(
              [
                { key: 'visual', label: 'Entrenamiento visual' },
                { key: 'text', label: 'Vocabulario rápido' },
              ] as const
            ).map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setTeachingTab(tab.key)}
                className={`rounded-[50px] px-7 py-2.5 text-[12px] font-semibold uppercase transition-colors ${
                  teachingTab === tab.key
                    ? 'bg-orange text-white'
                    : 'text-white/80 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {teachingTab === 'visual' ? (
          <div className="mt-10 grid grid-cols-1 items-stretch gap-6 lg:grid-cols-12">
            <div className="flex flex-col gap-4 lg:col-span-8">
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={() => !uploadedImage && fileInputRef.current?.click()}
                className={`relative flex min-h-[350px] flex-1 cursor-pointer flex-col items-center justify-center rounded-[30px] border-2 border-dashed p-6 transition-colors ${
                  uploadedImage
                    ? 'border-orange/60 bg-white/5'
                    : dragOver
                      ? 'border-orange bg-orange/10'
                      : 'border-white/25 bg-white/5'
                }`}
              >
                {uploadedImage ? (
                  <div className="relative max-w-full select-none overflow-hidden">
                    <img
                      src={uploadedImage}
                      alt="Referencia"
                      className="pointer-events-none max-h-[350px] rounded-[20px] object-contain"
                    />
                    <div
                      ref={canvasRef}
                      onMouseDown={onCanvasDown}
                      onMouseMove={onCanvasMove}
                      onMouseUp={onCanvasUp}
                      className="absolute inset-0 z-20 h-full w-full cursor-crosshair"
                    >
                      {boundingBoxes.map((box, idx) => (
                        <div
                          key={idx}
                          className="absolute flex flex-col justify-between border-2 border-orange bg-orange/25 p-1 text-white"
                          style={{ left: box.x, top: box.y, width: box.w, height: box.h }}
                        >
                          <span className="rounded bg-orange px-1 text-[9px] font-bold">
                            {box.label}
                          </span>
                        </div>
                      ))}
                      {tempBox && (
                        <div
                          className="absolute border-2 border-dashed border-orange bg-orange/15"
                          style={{
                            left: tempBox.x,
                            top: tempBox.y,
                            width: tempBox.w,
                            height: tempBox.h,
                          }}
                        />
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4 p-8 text-center text-white">
                    <p className="text-[18px] font-semibold">
                      Arrastra una imagen o haz clic aquí
                    </p>
                    <p className="text-[14px] text-white/70">O elige una imagen de ejemplo</p>
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setUploadedImage(
                            'https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&q=80&w=800',
                          );
                        }}
                        className="rounded-[50px] bg-white/10 px-4 py-2 text-[12px] font-semibold text-white transition-colors hover:bg-orange"
                      >
                        Muestra: Carnet
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setUploadedImage(
                            'https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&q=80&w=800',
                          );
                        }}
                        className="rounded-[50px] bg-white/10 px-4 py-2 text-[12px] font-semibold text-white transition-colors hover:bg-orange"
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
                <div className={`${GLASS} space-y-4 p-6`}>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="space-y-1">
                      <label className="text-[12px] font-bold uppercase tracking-wide text-white/80">
                        Clase del objeto
                      </label>
                      <input
                        type="text"
                        value={currentLabel}
                        onChange={(e) => setCurrentLabel(e.target.value)}
                        className={INPUT_GLASS}
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[12px] font-bold uppercase tracking-wide text-white/80">
                        Descripción semántica
                      </label>
                      <input
                        type="text"
                        value={currentDesc}
                        onChange={(e) => setCurrentDesc(e.target.value)}
                        className={INPUT_GLASS}
                      />
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                    <button
                      onClick={() => setBoundingBoxes(boundingBoxes.slice(0, -1))}
                      className="rounded-[50px] bg-white/10 px-5 py-2 text-[12px] font-semibold text-white transition-colors hover:bg-white/20"
                    >
                      Deshacer caja
                    </button>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setUploadedImage(null)}
                        className="rounded-[50px] px-5 py-2 text-[12px] font-semibold text-white/80 transition-colors hover:text-white"
                      >
                        Cancelar
                      </button>
                      <button onClick={saveTeaching} className={BTN_PRIMARY}>
                        Guardar y entrenar
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className={`${GLASS} flex flex-col gap-4 p-6 lg:col-span-4`}>
              <h2 className={SECTION_TITLE}>Base de datos YOLO</h2>
              {config.savedTeachingObjects.length === 0 ? (
                <p className="text-[13px] text-white/70">
                  Sin objetos entrenados todavía. Dibuja un cuadro sobre una imagen y
                  guárdalo para verlo aquí.
                </p>
              ) : (
                <div className="max-h-[400px] flex-1 space-y-3 overflow-y-auto">
                  {config.savedTeachingObjects.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center gap-3 rounded-[20px] bg-white/5 p-2.5"
                    >
                      <TrainedThumbnail src={mediaUrl(item.thumbnail)} label={item.label} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[12px] font-bold text-white">
                          <span className="mr-1 text-[10px] uppercase text-orange">Clase:</span>
                          {item.label}
                        </p>
                        <p className="truncate text-[11px] text-white/70">
                          <span className="mr-1 font-semibold opacity-70">Desc:</span>
                          {item.desc}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => deleteTeachingObject(item.id)}
                        aria-label={`Eliminar ${item.label}`}
                        title="Eliminar objeto"
                        className="shrink-0 rounded-full p-1.5 text-white/60 transition-colors hover:bg-white/10 hover:text-orange"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* VOCABULARIO ABIERTO INSTANTÁNEO (nodos 58:997 / 50:576 / 50:575). */
          <div className={`${GLASS} mx-auto mt-10 max-w-4xl p-10 text-center`}>
            <h2 className="text-[20px] font-bold uppercase text-white md:text-[24px]">
              Vocabulario abierto instantáneo
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-[14px] text-white/85 md:text-[16px]">
              Define términos que el modelo de visión identificará. Separa los elementos por comas.
            </p>
            <textarea
              id="vocabList"
              rows={5}
              defaultValue="mochila, cuaderno, laptop, credencial de estudiante, telefono"
              placeholder="Ejemplo: Mochila, cuaderno, laptop, credencial de estudiante, teléfono"
              className={`${INPUT_GLASS} mt-8 resize-y rounded-[30px] py-5 text-start`}
            />
            <button
              onClick={() => {
                const el = document.getElementById('vocabList') as HTMLTextAreaElement | null;
                if (el) compileVocabulary(el.value);
              }}
              className={`${BTN_PRIMARY} mt-8`}
            >
              Compilar términos
            </button>
          </div>
        )}
      </div>
    </ScreenHero>
  );
}
