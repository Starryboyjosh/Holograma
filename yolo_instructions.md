# Instrucciones YOLO / YOLOE — Holograma UNEV

Documento de handoff para **modificar, depurar o rehacer** la visión del kiosco.
Úsalo en otra conversación o sesión de agente: resume arquitectura, decisiones,
trampas conocidas, variables de entorno, archivos y fuentes.

**Última actualización de este doc:** 2026-07-22 (sesiones de unificación YOLOE,
precisión de uniforme ITEE y corrección del bbox en cuello vs pecho).

---

## 1. Objetivo del subsistema

- Detectar **personas** delante del kiosco (presencia, saludo, contexto LLM).
- Detectar **objetos / etiquetas de Entrenar** (`data/training_metadata.json` +
  `data/open_vocabulary.txt`).
- Detectar **Uniforme ITEE** (logo bordado en pecho, no cualquier camisa azul).
- Publicar análisis al LLM vía `camera_context` y al frontend (MJPEG + eventos).

**No** hay modelo COCO separado ni YOLO-World en producción. Un solo checkpoint
open-vocab:

```text
models/yoloe-26n-seg.pt
```

Constante canónica: `DEFAULT_YOLOE_WEIGHTS` en `vision/person_detector.py`.

---

## 2. Mapa de archivos (qué tocar)

| Archivo | Rol |
|---------|-----|
| **`vision/person_detector.py`** | Núcleo: carga YOLOE, `set_classes`, predict, uniforme, logos ORB/template, bucle continuo, overlay JPEG |
| `vision/camera.py` | Captura OpenCV (índice, resolución, backend) |
| `vision/__init__.py` | Exporta `YoloPersonDetector`, `DEFAULT_YOLOE_WEIGHTS` |
| `call.py` | Hilo de cámara, `_last_camera_analysis`, `_camera_context_for_prompt`, callback de eventos |
| `main.py` | Arranque FastAPI: `start_camera_thread`, monkey-patch del callback → `CameraContextProvider` |
| `app/services/vision.py` | `CameraContextProvider` (último análisis para ConversationService) |
| `camera_context.py` | Texto de contexto para el LLM (personas + objetos solo si la pregunta es visual) |
| `config.json` / `.env` / `.env.example` | `YOLO_*`, `HOLOGRAM_CAMERA*` |
| `data/training_metadata.json` | Etiquetas Entrenar + rutas de thumbnails |
| `data/images/` | Fotos de Entrenar (plantillas logo) |
| `data/open_vocabulary.txt` | Vocabulario libre (coma/separado) |
| `tests/test_custom_object_interval.py` | Inferencia única, uniforme, pecho vs cuello |
| `tests/test_yolo_predict_opts.py` | imgsz, conf floor, prepare_frame |
| `tests/test_camera_stop.py`, `test_camera_feed_gate.py`, `test_person_presence.py` | Bucle / feed / presencia |
| `scripts/diagnose_hologram.py --yolo` | Smoke test de un frame |

**No reintroducir** sin decisión explícita:

- Segundo modelo `yolo26n.pt` / `YOLO_PERSON_MODEL` (dual COCO + open-vocab).
- Fallback a `yolov8s-world.pt`.
- Prompts open-vocab genéricos tipo `"blue shirt"`, `"polo azul"`.

---

## 3. Arquitectura en runtime

```text
[Cámara OpenCV]
      │
      ▼
YoloPersonDetector.run_continuous()
      │  analyze_frame() → _detect_all()
      │    1) set_classes(persona + custom + aliases)
      │    2) predict(conf = min(YOLO_CONFIDENCE, YOLO_CUSTOM_CONFIDENCE))
      │    3) split persons vs custom
      │    4) logos Entrenar (template + amarillo/azul en ROI pecho)
      │    5) filtro uniforme (cuello ban, estructura, snap bbox)
      │
      ├─► callback(event, count, analysis)
      │      call._last_camera_analysis
      │      camera_provider.update(analysis)   # vía patch en main.py
      │
      ├─► MJPEG anotado (solo si hay suscriptores del feed)
      │
      └─► LLM: build_camera_context(analysis, include_objects=pregunta_visual)
```

### API pública útil de `YoloPersonDetector`

- `load()`, `warmup()`, `model_info()`, `get_active_prompts()`, `set_prompts()`
- `reload_vocabulary()` — relee training + open_vocabulary
- `analyze_frame(frame)` / `analyze_once()` / `detect_labels(frame, labels)`
- `run_continuous(callback, …)`, `stop()`, feed subscribe/unsubscribe
- `is_available()`, `default_weights()`

### Flujo de datos al LLM

1. Pregunta con keywords visuales (`uniforme`, `qué ves`, etc.) → `include_objects=True`.
2. Si no hay personas ahora pero las hubo ≤60 s → se reutiliza caché en `camera_context.py`.
3. Log diagnóstico: `[Cámara→LLM] running=… custom=… persons=…`

Si ves `persons=0 custom=[]` con gente delante: el fallo está en detección, no en el LLM.

---

## 4. Decisiones de diseño (y por qué)

### 4.1 Un solo modelo: `yoloe-26n-seg.pt`

| Decisión | Razón |
|----------|--------|
| Solo YOLOE, no COCO + World | Menos VRAM/RAM, una inferencia por ciclo, API unificada `set_classes` |
| Forzar nombres legacy a canónico | `config.json` con `yolo26n.pt` como `YOLO_MODEL` rompía open-vocab (`set_classes` inexistente) |
| Backend Ultralytics `YOLOE` | Open-vocab + seg nativo; `get_text_pe` + `set_classes` |

**Síntoma histórico:**  
`[YOLO] El modelo no expone set_classes; usa un checkpoint YOLOE/YOLO-World…`  
→ `YOLO_MODEL` apuntaba a un YOLO COCO normal.

### 4.2 Piso de confianza de `predict`

Ultralytics filtra cajas **en el NMS** con el `conf` de `predict`. Si se usaba
solo `YOLO_CONFIDENCE=0.45`, las detecciones custom a 0.15–0.40 **nunca llegaban**
al post-proceso.

```text
predict_conf = max(0.05, min(YOLO_CONFIDENCE, YOLO_CUSTOM_CONFIDENCE))
# luego:
#   persona  si conf >= YOLO_CONFIDENCE
#   custom   si conf >= YOLO_CUSTOM_CONFIDENCE
```

Implementado en `_predict_floor_conf()` + `_split_detections()`.

### 4.3 Logos de Entrenar (ITEE y futuros colegios): imagen de referencia

**Fuente de verdad:** fotos en `data/training_metadata.json` + crop `x,y,w,h`
del bbox dibujado en la UI de Entrenar. Matching:

1. **Template multi-escala** (`TM_CCOEFF_NORMED`) sobre ROI pecho (gris + equalizeHist).
2. **ORB** como refuerzo de confianza.
3. **No** se usa color (amarillo/azul): eso era específico de ITEE y rompe
   otros colegios.

| Problema | Mitigación |
|----------|------------|
| Open-vocab «blue shirt» / camisa genérica = Uniforme ITEE | Sin match a la **foto Entrenar** no se acepta la etiqueta |
| Cuadro en el **placket del cuello** | Zona `y < YOLO_COLLAR_Y_MAX`; ROI pecho; snap bbox |
| Solo color azul+amarillo | Eliminado como criterio de aceptación |
| Varios colegios en Entrenar | Cada `label` tiene sus propias plantillas; misma pipeline |

**Señales de aceptación (prioridad):**

1. `source=logo_ref` — match template/ORB de Entrenar en ROI pecho (**preferido**).
2. Open-vocab de etiqueta **con** fotos Entrenar → solo si
   `_verify_logo_reference` confirma la plantilla (`logo_ref_verified`).
3. Open-vocab de etiqueta **sin** fotos (p. ej. «botella») → umbral custom normal.

**No reintroducir** gates de color ITEE (`_box_has_itee_structure`, seeds amarillas)
como condición principal.

### 4.4 Geometría del ROI pecho (fracciones de la caja persona)

```text
y ∈ [YOLO_LOGO_Y0, YOLO_LOGO_Y1]   default 0.36–0.58
x ∈ [YOLO_LOGO_X0, YOLO_LOGO_X1]   default 0.08–0.48  (izq. en imagen kiosco)
cuello ban: y < YOLO_COLLAR_Y_MAX  default 0.34
YOLO_LOGO_MIRROR=1                 si el logo sale al otro lado
```

`0` = arriba/izquierda de la bbox de persona; `1` = abajo/derecha.

### 4.5 Prompts `set_classes`

- Siempre incluir prompts de persona (`_BASE_PERSON_PROMPTS`).
- Custom = etiquetas Entrenar + `open_vocabulary` + aliases (`_OPEN_VOCAB_ALIASES`).
- Cap `_MAX_OPEN_VOCAB_PROMPTS` (40): CLIP/YOLOE degradan con listas enormes.
- Cargar embeddings con `get_text_pe` + `set_classes(names, pe)` cuando exista.

### 4.6 Cámara y feed

- Detección YOLO **no se apaga** si no hay personas ni viewers del MJPEG.
- Solo el **encode JPEG** es opcional (cero suscriptores del feed).
- Intervalo `YOLO_INTERVAL_SECONDS` (default config ~0.6).

---

## 5. Variables de entorno / config

### Esenciales

| Variable | Default típico | Notas |
|----------|----------------|--------|
| `HOLOGRAM_CAMERA` | `1` | Activa hilo de visión |
| `HOLOGRAM_CAMERA_INDEX` | `0` | Índice OpenCV/sounddevice |
| `YOLO_MODEL` | `yoloe-26n-seg.pt` | Solo YOLOE; legacy se reescribe |
| `YOLO_CONFIDENCE` | `0.28` | Personas (post-split) |
| `YOLO_CUSTOM_CONFIDENCE` | `0.12` | Custom genérico; también baja el piso de predict |
| `YOLO_UNIFORM_CONFIDENCE` | `0.45` | Solo open-vocab de uniforme |
| `YOLO_IMGSZ` | `416` | Tamaño de entrada Ultralytics |
| `YOLO_MAX_SIDE` | `960` | Resize software del frame antes de predict |
| `YOLO_INTERVAL_SECONDS` | `0.6` | Periodo del bucle continuo |
| `YOLO_IOU` / `YOLO_MAX_DET` | `0.5` / `50` | NMS / tope de cajas |
| `YOLO_DEVICE` | vacío (auto) | `cpu`, `0`, `cuda:0`… |
| `YOLO_HALF` | `0` | FP16 si GPU |

### Geometría / uniforme

| Variable | Default | Notas |
|----------|---------|--------|
| `YOLO_LOGO_Y0` / `Y1` | `0.36` / `0.58` | Banda vertical pecho |
| `YOLO_LOGO_X0` / `X1` | `0.08` / `0.48` | Banda horizontal logo |
| `YOLO_COLLAR_Y_MAX` | `0.34` | Por encima = cuello (descartar) |
| `YOLO_LOGO_MIRROR` | `0` | Invierte X del ROI |
| `YOLO_UNIFORM_YELLOW_MIN` | `0.015` | Fracción amarillo en parche |
| `YOLO_UNIFORM_BLUE_MIN` | `0.12` | Fracción azul |
| `YOLO_LOGO_TMPL_MIN` | `0.68` | Score template |
| `HOLOGRAM_YOLO_DEBUG` | `0` | Logs `[YOLO] Descartado…` / ciclo |

### Cámara

| Variable | Notas |
|----------|--------|
| `HOLOGRAM_CAMERA_WIDTH` / `HEIGHT` | Resolución pedida al driver |
| `HOLOGRAM_CAMERA_BACKEND` | Backend OpenCV si hace falta |
| `HOLOGRAM_CAMERA_RELEASE_ON_UI_OFF` | Si `1`, apagar UI libera cámara |

Pesos: `models/yoloe-26n-seg.pt` (o nombre de hub si no está en disco).

---

## 6. Cómo modificar (recetas)

### 6.1 Cambiar solo umbrales / ROI (sin código)

Editar `config.json` o `.env`, reiniciar backend.

```json
"YOLO_CONFIDENCE": "0.28",
"YOLO_CUSTOM_CONFIDENCE": "0.12",
"YOLO_UNIFORM_CONFIDENCE": "0.45",
"YOLO_IMGSZ": "416",
"YOLO_LOGO_Y0": "0.36",
"YOLO_LOGO_Y1": "0.58",
"YOLO_COLLAR_Y_MAX": "0.34"
```

Debug:

```bash
HOLOGRAM_YOLO_DEBUG=1
```

### 6.2 Añadir una clase Entrenar (UI o datos)

1. Pantalla Entrenar → fotos + etiqueta, o editar `data/training_metadata.json`.
2. Opcional: `data/open_vocabulary.txt`.
3. El detector recarga por mtime (~5 s) vía `_maybe_reload_training`, o
   `reload_vocabulary()`.

Para una etiqueta sensible a FP (como uniforme), **no** confíes solo en
open-vocab: añade post-filtro o aliases específicos (ver `_OPEN_VOCAB_ALIASES`
y `_filter_uniform_objects`).

### 6.3 Ajustar aliases open-vocab

En `vision/person_detector.py` → `_OPEN_VOCAB_ALIASES`:

- Clave = etiqueta operador en minúsculas.
- Valores = prompts en inglés/español **específicos**.
- Evitar: `blue shirt`, `polo`, `shirt`, colores sueltos.

### 6.4 Rehacer el detector desde cero (checklist)

1. Mantener un solo backend open-vocab con `set_classes` (YOLOE recomendado).
2. `predict` con conf = min(persona, custom); split después.
3. Separar caminos: persona / custom genérico / clases con post-filtro de dominio.
4. No dibujar la bbox cruda de open-vocab si se sabe que el modelo se ancla mal
   (ej. cuello): snap a ROI o usar solo template.
5. Inyectar análisis al mismo sitio que hoy (`call` + `CameraContextProvider`).
6. Tests: `test_custom_object_interval`, `test_yolo_predict_opts`, presencia, feed.
7. Documentar env en `.env.example` y este archivo.

### 6.5 Diagnóstico rápido

```bash
# Un frame de cámara
.venv/bin/python scripts/diagnose_hologram.py --camera --yolo

# Tests visión
.venv/bin/python -m pytest tests/test_custom_object_interval.py \
  tests/test_yolo_predict_opts.py tests/test_camera_stop.py \
  tests/test_camera_feed_gate.py tests/test_person_presence.py -q
```

Logs esperados al arrancar:

```text
[YOLO] Cargando YOLOE: yoloe-26n-seg.pt...
[YOLO] Listo (YOLOE): ... (personas + custom open-vocab)
[YOLO] Prompts YOLOE activos (...): ['person', 'persona', ..., 'Uniforme ITEE', ...]
[YOLO] Warmup OK
[YOLO] ciclo=N hits=… persons=… custom=[…] conf_floor=0.12
```

Si `set_classes` falla o el tipo no es YOLOE → revisar `YOLO_MODEL` y pesos en
`models/`.

### 6.6 Problemas frecuentes

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `set_classes` no existe | Checkpoint COCO / wrong file | `YOLO_MODEL=yoloe-26n-seg.pt` |
| `persons=0 custom=[]` con gente | conf alto, cámara mal, modelo no carga | bajar conf floor, debug, feed UI |
| Cualquier camisa = Uniforme ITEE | prompts genéricos / sin filtro estructura | no reabrir aliases genéricos; subir `YOLO_UNIFORM_CONFIDENCE` |
| Cuadro en el **cuello** | open-vocab en placket amarillo | `YOLO_COLLAR_Y_MAX`, snap pecho, preferir `logo_chest` |
| Logo al otro lado | espejo de cámara | `YOLO_LOGO_MIRROR=1` |
| LLM dice que no ve | análisis vacío o pregunta no “visual” | ver log `[Cámara→LLM]`; keywords en `camera_context.py` |
| Feed negro / sin frames | índice cámara, permisos, otro proceso | `HOLOGRAM_CAMERA_INDEX`, diagnose |

---

## 7. Tests que no deben romperse al tocar YOLO

| Test | Qué blinda |
|------|------------|
| `test_analyze_frame_single_predict_splits_person_and_custom` | Un solo predict por frame |
| `test_predict_floor_is_min_of_person_and_custom` | conf floor = min(persona, custom) |
| `test_uniform_open_vocab_outside_chest_is_dropped` | Fuera de pecho no cuenta |
| `test_uniform_on_collar_is_rejected_or_snapped_off_neck` | Cuello no es ITEE |
| `test_uniform_open_vocab_low_conf_dropped` | Umbral uniforme alto |
| `test_generic_blue_patch_fails_itee_structure` | Azul sin amarillo ≠ logo |
| `test_blue_yellow_patch_passes_itee_structure` | Estructura logo OK |
| `test_empty_room_still_runs_predict` | Sala vacía no apaga YOLO |

---

## 8. Fuentes consultadas (para esta y otras sesiones)

### Documentación y producto Ultralytics

1. **YOLOE — Real-Time Seeing Anything (docs oficiales)**  
   https://docs.ultralytics.com/models/yoloe/  
   - Open-vocab detection/segmentation.  
   - `set_classes([...])`, predicción con prompts de texto.  
   - Mismos pesos para text / visual prompts (visual vía API de predict).  
   - Usado para: un solo checkpoint, `set_classes` + predict, no inventar API.

2. **Comunidad Ultralytics — `set_classes` + `get_text_pe`**  
   https://community.ultralytics.com/t/how-to-run-object-detection-inference-with-a-yoloe-segmentation-model/1436  
   - Patrón: `model.set_classes(names, model.get_text_pe(names))`.  
   - Usado para: embeddings de texto correctos en YOLOE.

3. **YOLO-World (contexto open-vocab, no usado en prod actual)**  
   https://docs.ultralytics.com/models/yolo-world/  
   - Misma idea de `set_classes`; referencia histórica del dual-model eliminado.

4. **LearnOpenCV — YOLOE tutorial (text prompts, conf, multi-clase)**  
   https://learnopencv.com/yoloe-tutorial-real-time-open-vocabulary-detection/  
   - Prompts concretos + `conf` explícito; text prompts no bastan en dominios finos.  
   - Usado para: justificar post-filtros de dominio (uniforme) y umbrales.

5. **Discusión modelos YOLOE (Ultralytics org)**  
   https://github.com/orgs/ultralytics/discussions/19783  
   - Contexto de familia YOLOE / pesos.

6. **Paper / HTML YOLOE-26 (visión general open-vocab + visual prompts)**  
   https://arxiv.org/html/2602.00168v1  
   - Text vs visual prompts; visual cuando el texto no discrimina (logo).  
   - Usado para: priorizar plantillas Entrenar + color structure sobre texto solo.

### Código y comportamiento local del proyecto

7. **Código actual** `vision/person_detector.py`, `call.py`, `main.py`,
   `camera_context.py`, tests listados arriba.  
8. **Evidencia de producto:** logs de consola del kiosco (`persons=0`,
   `custom=[]`, cuadro en cuello) y captura de referencia del polo ITEE.  
9. **Experiencia previa en el repo:** dual `yolo26n` + World/`yoloe` causaba
   confusión de config y el mensaje `set_classes` ausente.

### Principios de ingeniería aplicados (no paper-specific)

- Open-vocabulary text encoders son **semánticamente amplios** → FP en categorías
  parecidas (camisa vs uniforme con logo). Mitigación: prompts estrechos +
  verificación geométrica y de color/template.
- El umbral de `predict` es un **filtro duro pre-NMS**; el post-split no recupera
  cajas ya eliminadas.
- Separar **señal de UI/LLM** (bbox en pecho) de la **caja cruda del detector**.

---

## 9. Prompt sugerido para otra conversación

Copia esto al abrir un chat nuevo:

```text
Lee y sigue docs/ o el archivo yolo_instructions.md en la raíz del repo Holograma
(vision YOLOE). Resumen:

- Un solo modelo: models/yoloe-26n-seg.pt vía vision/person_detector.py (YOLOE).
- No reintroducir yolo26n dual ni yolov8s-world sin acuerdo.
- predict conf = min(YOLO_CONFIDENCE, YOLO_CUSTOM_CONFIDENCE); split después.
- Uniforme ITEE: prohibido open-vocab genérico; ban cuello y<0.34; ROI pecho
  0.36–0.58 × 0.08–0.48; estructura azul+amarillo mate; preferir logo Entrenar;
  snap bbox al pecho.
- Contexto LLM: call._last_camera_analysis + CameraContextProvider + camera_context.py.
- Tests: test_custom_object_interval, test_yolo_predict_opts, camera_*.

Tarea: <describe el cambio>
```

---

## 10. Inventario de constantes clave (código)

Archivo: `vision/person_detector.py`

| Símbolo | Valor / idea |
|---------|----------------|
| `DEFAULT_YOLOE_WEIGHTS` | `yoloe-26n-seg.pt` |
| `_BASE_PERSON_PROMPTS` | person, persona, people, human, man, woman, estudiante |
| `_OPEN_VOCAB_ALIASES` | mapeo etiqueta → prompts (sin genéricos de camisa) |
| `_LOGO_Y0/_Y1/_X0/_X1` | ROI pecho |
| `_COLLAR_Y_MAX` | 0.34 |
| `_UNIFORM_OPEN_VOCAB_MIN_CONF` | 0.45 |
| `_MAX_OPEN_VOCAB_PROMPTS` | 40 |

---

## 11. Changelog breve (sesión de origen de este doc)

1. Unificación a **solo YOLOE-26n-seg**; eliminación de pesos duales y `YOLO_PERSON_MODEL`.
2. Fix **set_classes** / conf floor / defaults de umbral e imgsz.
3. Precisión **Uniforme ITEE**: aliases, estructura color, conf uniforme, veto de camisas genéricas.
4. Bbox: **cuello vs pecho** (collar ban, snap ROI, prefer logo_chest).
5. Este documento de handoff.

---

*Si cambias la arquitectura YOLO, actualiza este archivo en el mismo PR/commit.*
