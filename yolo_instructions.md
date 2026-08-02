# Instrucciones YOLO / YOLOE — Holograma UNEV

Documento de handoff para **modificar, depurar o rehacer** la visión del kiosco.
Úsalo en otra conversación o sesión de agente: resume arquitectura, decisiones,
trampas conocidas, variables de entorno, archivos y fuentes.

**Última actualización de este doc:** 2026-08-02 (sesión 5: corrección de
números obsoletos frente al código real, razonamiento parte por parte de
`vision/`, comparación con `remind-reid-tracker-main/` y hoja de ruta
WAVE-11+).

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
| **`vision/person_detector.py`** | Orquestación: carga YOLOE, `set_classes`, predict, filtro de uniforme, bucle continuo, overlay JPEG |
| **`vision/geometry.py`** | **Funciones puras** de cajas y ROI del pecho: `logo_roi_fractions`, `collar_y_max`, `snap_box_to_logo_zone`, `best_person_for_box`, `point_in_logo_zone`, `clamp_box_to_frame` |
| **`vision/image_signals.py`** | **Funciones puras** de imagen: `compute_hsv_hist`, `is_white_light_or_glare`, `compare_hsv_signature`, `match_template_multiscale`, `match_orb` |
| `vision/camera.py` | Captura OpenCV (índice, resolución, backend) |
| `vision/face_analyzer.py` | Estimación de rostro (usada opcionalmente por `analyze_frame`) |
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
| `tests/test_vision_geometry.py` | Geometría pura + **prioridad de fuente** en el dedupe |
| `tests/test_vision_signals.py` | HSV, glare/ventanas, template multiescala, ORB |
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
del bbox dibujado en la UI de Entrenar. Pipeline de matching (3 etapas):

1. **Firma de color HSV** (`_match_hsv_color_signature`): histograma 2D
   HSV (18 bins Hue × 16 bins Saturation) del recorte se compara con los
   histogramas de las fotos de Entrenar vía `cv2.HISTCMP_CORREL`.
   - Umbral: `YOLO_LOGO_HSV_MIN` (default **`0.18`**, código actual — muy
     permisivo a propósito). Correlación menor → descartado antes de gastar
     CPU en template/ORB.
   - **Razón:** detectar si el parche tiene los colores del logo (amarillo+azul para
     ITEE, rojo+blanco para otro colegio, etc.) sin hardcodear colores ITEE.
     Funciona genérico con cualquier colegio.
   - **⚠️ Bug en producción, verificado (sesión 5):** este gate está **inerte**
     hoy. `_rebuild_logo_templates` (`vision/person_detector.py:665`) resetea
     `_logo_templates`/`_logo_images` en el reset (`:674-675`) pero **no**
     `_logo_hsv_hists`; y el camino de caché (`data/logo_index.npz`) retorna en
     `:712` antes de asignar los hists — el npz en disco solo tiene las claves
     `meta_sig`, `by_img`, `by_des` (verificado con `np.load`, no hay `by_hsv`).
     Aguas abajo, `compare_hsv_signature` (`image_signals.py:115-116`) hace
     `if not ref_hists: return 1.0` (fail-open). Resultado: con `_logo_hsv_hists={}`,
     el color **nunca** rechaza un match. Ver §13 (I1) para el fix propuesto —
     no lo apliques sin leer esa sección primero, porque re-activar el gate a
     ciegas puede rechazar logos válidos bajo la iluminación real del kiosco.
2. **Template multi-escala** (`TM_CCOEFF_NORMED`, pirámide de 7 niveles)
   sobre ROI del cuerpo (gris + equalizeHist). Escalas relativas al ROI:
   `0.14, 0.20, 0.28, 0.38, 0.50, 0.65, 0.80`.
   - **Razón de 7 escalas:** el logo cambia mucho de tamaño dependiendo de la
     distancia persona-cámara. Con pocas escalas (3–4) el template matching fallaba
     cuando la persona estaba lejos o muy cerca. 7 niveles cubren desde logos
     pequeños (14% del ROI) hasta ocupar casi todo el ROI (80%).
3. **ORB** como refuerzo de confianza (700 keypoints, ratio Lowe 0.75).

La escalera de decisión real (`_match_logo_in_gray`, `person_detector.py:998-1040`)
no es un promedio simple de las tres señales: es un `if/elif/elif` con pesos y
umbrales fijados a mano (`conf = 0.75·tmpl + 0.25·orb` si `tmpl` pasa el umbral;
si no, `0.55·tmpl + 0.45·orb` si `orb≥0.85`; si no, una caja sintética si
`orb≥0.95`; si no, cero). §13 (I3) propone reemplazarla por una fusión ponderada
por calidad — no es una limpieza cosmética, cambia qué gana en casos límite.

**No** se usa color amarillo/azul hardcodeado como criterio: eso era específico
de ITEE y rompe otros colegios. El HSV histogram es genérico.

| Problema | Mitigación |
|----------|------------|
| Open-vocab «blue shirt» / camisa genérica = Uniforme ITEE | Sin match a la **foto Entrenar** no se acepta la etiqueta |
| Cuadro en el **placket del cuello** | Zona `y < YOLO_COLLAR_Y_MAX`; ROI pecho; snap bbox |
| Solo color azul+amarillo hardcodeado | Reemplazado por **histograma HSV genérico** (funciona con cualquier colegio) |
| Varios colegios en Entrenar | Cada `label` tiene sus propios histogramas y plantillas |
| Cuadro muy pequeño (20×20 px) sobre el video | `_snap_box_to_logo_zone` escala al tamaño proporcional del pecho (ver §4.7) |
| Ventana con luz blanca detectada como uniforme | `_is_white_light_or_glare` + check directo en la caja YOLOE (ver §4.8) |

**Señales de aceptación (prioridad):**

1. `source=logo_ref` — match HSV+template+ORB de Entrenar en ROI pecho (**preferido**).
2. Open-vocab de etiqueta **con** fotos Entrenar → solo si
   `_verify_logo_reference` confirma la plantilla (`logo_ref_verified`).
3. Open-vocab de etiqueta **sin** fotos (p. ej. «botella») → umbral custom normal.

Esta prioridad se aplica en `_dedupe_custom` mediante `_SOURCE_PRIORITY`
(verificado = 3, `open_vocab_snapped` = 1). La confianza **solo** desempata
entre detecciones de la misma fuente.

> **Límite conocido, no un bug:** `_dedupe_custom` (`person_detector.py:1402`)
> indexa **solo por `label`**, así que colapsa a **una** entrada aunque haya
> varias personas con el mismo uniforme puesto — dos estudiantes de ITEE
> producen un único objeto `"Uniforme ITEE"` en `analysis`. Es multi-instancia,
> no multi-etiqueta, lo que falta. Ver §13 (I2) — es la mejora más barata de
> toda la hoja de ruta.

> **Regresión histórica (sesión 4).** Durante mucho tiempo esta prioridad estuvo
> escrita en el documento pero **no** en el código: `_dedupe_custom` ordenaba
> solo por confianza y la preferencia por fuente se aplicaba después, en
> `_detect_all`, sobre una lista que ya tenía una sola entrada por label — así
> que era código muerto. En la práctica ganaba el open-vocab (0.92) sobre el
> match verificado contra la foto de Entrenar (0.70): exactamente al revés de lo
> diseñado. Si vuelves a tocar el dedupe, **no reordenes por confianza antes de
> resolver la fuente**. Lo blinda `test_verified_logo_beats_higher_confidence_open_vocab`.

**No reintroducir** gates de color ITEE (`_box_has_itee_structure`, seeds amarillas)
como condición principal.

### 4.4 Geometría del ROI (fracciones de la caja persona)

```text
y ∈ [YOLO_LOGO_Y0, YOLO_LOGO_Y1]   default 0.20–1.00  (cuerpo completo, NO solo pecho)
x ∈ [YOLO_LOGO_X0, YOLO_LOGO_X1]   default 0.00–1.00
cuello ban: y < YOLO_COLLAR_Y_MAX  default 0.25
YOLO_LOGO_MIRROR=1                 si el logo sale al otro lado
```

`0` = arriba/izquierda de la bbox de persona; `1` = abajo/derecha.

> **Corrección frente al doc anterior (sesión 5):** la banda dejó de ser
> "pecho" (`0.36–0.58 × 0.08–0.48`). `logo_roi_fractions()` y `chest_zone()`
> en `vision/geometry.py:39-43,88-89` documentan explícitamente que cubren el
> **cuerpo** de la persona, y `snap_box_to_logo_zone` ya no fuerza la caja a
> una zona fija: **preserva la ubicación detectada en cualquier parte del
> cuerpo**, solo la empuja por debajo del cuello si quedó por encima
> (`geometry.py:155-157`). El nombre "pecho"/"logo" en variables y funciones
> es ahora un nombre heredado, no una descripción exacta — no lo tomes
> literalmente al leer el código.

### 4.5 Prompts `set_classes`

- Siempre incluir prompts de persona (`_BASE_PERSON_PROMPTS`).
- Custom = etiquetas Entrenar + `open_vocabulary` + aliases (`_OPEN_VOCAB_ALIASES`).
- Cap `_MAX_OPEN_VOCAB_PROMPTS` (40): CLIP/YOLOE degradan con listas enormes.
- Cargar embeddings con `get_text_pe` + `set_classes(names, pe)` cuando exista.

### 4.6 Cámara y feed

- Detección YOLO **no se apaga** si no hay personas ni viewers del MJPEG.
- Solo el **encode JPEG** es opcional (cero suscriptores del feed).
- Intervalo `YOLO_INTERVAL_SECONDS` (default en código **`1.0`**,
  `person_detector.py:1772`; `config.json` trae `"1"` — el `~0.6` de versiones
  previas de este doc no corresponde a ningún default real).
- `run_continuous` también corre un debounce de presencia con
  `PRESENCE_ENTER_SECONDS` (default `0.8`) y `PRESENCE_ABSENCE_SECONDS`
  (default `5.0`) que no estaba documentado aquí — ver §12.6 y §13 (la brecha
  de identidad de persona nace exactamente de este debounce).

### 4.7 Tamaño proporcional de la caja del logo (`_snap_box_to_logo_zone`)

**Problema original:** El template matching encontraba el logo correctamente pero
devolvía un rectángulo del tamaño exacto del template redimensionado (ej. 20×18 px).
En el video en vivo se dibujaba un cuadrado minúsculo invisible. También, en
`_filter_uniform_objects`, la caja `refined` de `_verify_logo_reference` era la
coordenada del match crudo y **nunca pasaba por `_snap_box_to_logo_zone`**.

**Solución:** `_snap_box_to_logo_zone(box, person_box)` ahora:

1. Calcula la zona del cuerpo (`zw`, `zh`) según las fracciones `_logo_roi_fractions()`.
2. Define dimensiones mínimas proporcionales:
   - `target_w = max(45px, 25% del ancho de la zona)`
   - `target_h = max(45px, 25% del alto de la zona)`
3. Si la caja original es más pequeña que estos mínimos, la agranda —
   **nunca la achica** (`use_w = max(orig_w, target_w)`).
4. Clampea el centro dentro de la zona del cuerpo (margen 4%).
5. Clampea los bordes dentro de la caja de la persona.

**Valores actuales** (`vision/geometry.py:31-33` —
`SNAP_MIN_W_FRACTION=0.25`, `SNAP_MIN_H_FRACTION=0.25`, `SNAP_MIN_SIDE_PX=45.0`,
`SNAP_CENTER_MARGIN=0.04`): distintos de los `55%/65%/50px` documentados en
versiones previas de este archivo. La justificación original (envolver
cómodamente el logo) sigue siendo válida en espíritu, pero **preservando la
ubicación detectada** en vez de forzar centrado — ver §4.4.

**Aplicación en ambos caminos de código:**

- `_detect_logo_templates` (`person_detector.py:1089`, snap en `:1138`):
  `best_box_frame = self._snap_box_to_logo_zone(...)` ✓
- `_filter_uniform_objects` (`logo_ref_verified`, `person_detector.py:1240`,
  snap en `:1379`): aplica `final_box = self._snap_box_to_logo_zone(refined, person_box)`
  **siempre** antes de emitir el resultado. ✓

### 4.8 Rechazo de ventanas / luz blanca / destellos (`_is_white_light_or_glare`)

**Problema original:** El YOLOE detectaba ventanas con luz solar blanca como
"school uniform" o "ITEE uniform". La verificación con `_verify_logo_reference`
no ayudaba porque:

1. El primer intento (sobre `search_box`) fallaba correctamente.
2. Pero el **segundo intento** usaba `person_box` (la persona entera), que SÍ
   contiene el logo real del uniforme → match exitoso.
3. Resultado: la ventana era aceptada como "Uniforme ITEE" porque la verificación
   se hizo sobre el pecho de la persona, no sobre la ventana.

**Solución (3 capas):**

1. **`_is_white_light_or_glare(bgr_crop)`**: Analiza el espacio HSV del recorte.
   - Píxeles blancos: Saturation < 40 AND Value > 180.
   - Rechaza si: ratio de píxeles blancos > 40% **O** (Sat media < 32 AND Val media > 175).
   - **Razón de umbrales más agresivos:** la versión anterior (Sat < 35, Val > 195,
     ratio > 55%) era demasiado permisiva — ventanas con luz difusa tenían Sat ~38
     y Val ~185, pasando los filtros.

2. **Filtro ANTES de `_verify_logo_reference`** en `_filter_uniform_objects`:
   Se recorta la caja YOLOE original del frame y se ejecuta
   `_is_white_light_or_glare(det_crop)` **antes** de intentar verificar con
   la plantilla. Si la caja YOLOE es luz blanca → descartada inmediatamente,
   sin importar que `_verify_logo_reference` con `person_box` encontraría el logo.
   - **Razón crítica:** la verificación con `person_box` busca el logo en el
     pecho de la persona. Si la persona lleva uniforme, siempre encontrará el logo.
     Pero eso no significa que la detección YOLOE original (la ventana) sea el logo.
     El filtro de glare en la caja YOLOE original resuelve esta ambigüedad.

3. **Filtro en `_match_hsv_color_signature`**: Si el crop del ROI pecho tiene
   glare, `_match_hsv_color_signature` devuelve `0.0` → `_match_logo_in_gray`
   devuelve `(0.0, None, "hsv_mismatch")`.

4. **`_detect_logo_templates` sin personas = vacío**: Si no hay personas detectadas
   por YOLO, `_detect_logo_templates` retorna `[]` inmediatamente. Antes, creaba
   una "persona falsa" que cubría casi todo el frame (incluyendo ventanas), lo que
   causaba falsos positivos en ventanas sin persona. Los logos de uniforme solo
   existen sobre personas.

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
| `YOLO_INTERVAL_SECONDS` | `1.0` | Periodo del bucle continuo |
| `YOLO_IOU` / `YOLO_MAX_DET` | `0.5` / `50` | NMS / tope de cajas |
| `YOLO_DEVICE` | vacío (auto) | `cpu`, `0`, `cuda:0`… |
| `YOLO_HALF` | `0` | FP16 si GPU |

### Geometría / uniforme

| Variable | Default | Notas |
|----------|---------|--------|
| `YOLO_LOGO_Y0` / `Y1` | `0.20` / `1.00` | Banda vertical — **cuerpo completo**, no solo pecho (ver §4.4) |
| `YOLO_LOGO_X0` / `X1` | `0.00` / `1.00` | Banda horizontal — cuerpo completo |
| `YOLO_COLLAR_Y_MAX` | `0.25` | Por encima = cuello (descartar), clamp 0.10–0.45 |
| `YOLO_LOGO_MIRROR` | `0` | Invierte X del ROI |
| `YOLO_LOGO_TMPL_MIN` | `0.42` | Score template mínimo (`_TMPL_MATCH_MIN`) |
| `YOLO_LOGO_HSV_MIN` | `0.18` | Correlación HSV mínima — **hoy inerte en producción**, ver §4.3 y §13 (I1) |
| `YOLO_LOGO_TMPL_MAX_SIDE` | `128` | Lado máx. de la plantilla gris cacheada, clamp 64–192 |
| `YOLO_LOGO_ORB_MAX_SIDE` | `160` | Lado máx. de la miniatura para ORB, clamp `tmpl_max`–256 |
| `HOLOGRAM_YOLO_DEBUG` | `0` | Logs `[YOLO] Descartado…` / ciclo |

### Presencia

| Variable | Default | Notas |
|----------|---------|--------|
| `PRESENCE_ENTER_SECONDS` | `0.8` | Debounce de entrada antes de emitir `person_entered`/`group_detected` |
| `PRESENCE_ABSENCE_SECONDS` | `5.0` | Debounce de salida antes de emitir `person_left` — ver §13, es la causa raíz de la brecha de identidad |

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
| **Cuadro muy pequeño** (20×20 px) | `refined` de `_verify_logo_reference` sin snap | El bug: `_filter_uniform_objects` no aplicaba `_snap_box_to_logo_zone` al `refined`. Ahora siempre se aplica. |
| **Ventana = Uniforme ITEE** | YOLOE detecta ventana blanca como "school uniform"; segundo intento busca en `person_box` y encuentra logo real | Filtro de glare en la caja YOLOE original **antes** de `_verify_logo_reference`. Ver §4.8. |
| Logo al otro lado | espejo de cámara | `YOLO_LOGO_MIRROR=1` |
| LLM dice que no ve | análisis vacío o pregunta no “visual” | ver log `[Cámara→LLM]`; keywords en `camera_context.py` |
| Feed negro / sin frames | índice cámara, permisos, otro proceso | `HOLOGRAM_CAMERA_INDEX`, diagnose |

---

## 7. Tests que no deben romperse al tocar YOLO

**Corregido en sesión 5:** la tabla anterior nombraba tres tests que no existen
(`test_uniform_open_vocab_outside_chest_is_dropped`,
`test_generic_blue_patch_fails_itee_structure`,
`test_blue_yellow_patch_passes_itee_structure`) — el gate de estructura
azul+amarillo (`_box_has_itee_structure`) fue eliminado del código. Los que
existen hoy, verificados con `grep -n "^def test_" tests/test_custom_object_interval.py`:

| Test | Qué blinda |
|------|------------|
| `test_analyze_frame_single_predict_splits_person_and_custom` | Un solo predict por frame |
| `test_detect_all_applies_person_and_custom_prompts` | Prompts persona + custom aplicados juntos |
| `test_no_custom_still_detects_person` | Sin custom, persona se sigue detectando |
| `test_uniform_alias_maps_to_operator_label` | Alias mapea a etiqueta de operador |
| `test_uniform_on_collar_is_rejected_or_snapped_off_neck` | Cuello no es ITEE |
| `test_uniform_open_vocab_on_face_or_head_is_dropped` | Sobre cara/cabeza se descarta |
| `test_uniform_open_vocab_on_other_body_parts_accepted` | **Semántica invertida** frente al doc viejo: fuera del pecho estricto ahora **se acepta** (la zona es el cuerpo completo, §4.4) |
| `test_uniform_open_vocab_low_conf_dropped` | Umbral uniforme alto |
| `test_logo_trained_open_vocab_requires_reference_match` | Etiqueta con fotos Entrenar exige match contra la plantilla |
| `test_logo_ref_from_template_match` | `source=logo_ref` desde template |
| `test_open_vocab_uniform_checked_against_db_logo_images` | Open-vocab uniforme se valida contra fotos en BD |
| `test_predict_floor_is_min_of_person_and_custom` (`test_yolo_predict_opts.py`) | conf floor = min(persona, custom) |
| `test_empty_room_still_runs_predict` (`test_yolo_predict_opts.py`) | Sala vacía no apaga YOLO |

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
- Uniforme ITEE: prohibido open-vocab genérico; ban cuello y<YOLO_COLLAR_Y_MAX
  (0.25); ROI = cuerpo completo (y 0.20–1.00, x 0.00–1.00, NO solo pecho);
  sin gate de estructura de color (fue eliminado); preferir logo Entrenar
  (source=logo_ref/logo_ref_verified sobre open_vocab_snapped); snap bbox
  preserva la ubicación detectada, no la centra en una zona fija.
- El gate HSV (YOLO_LOGO_HSV_MIN) está inerte en producción por un bug de
  caché conocido — no asumas que el color está filtrando nada hasta leer §13 (I1).
- No hay identidad de persona (no hay model.track()); solo presencia
  booleana con debounce PRESENCE_ENTER_SECONDS/PRESENCE_ABSENCE_SECONDS.
  _dedupe_custom colapsa a una entrada por etiqueta (sin multi-instancia).
- Contexto LLM: call._last_camera_analysis + CameraContextProvider + camera_context.py.
- Tests: test_custom_object_interval.py, test_yolo_predict_opts.py, camera_*,
  test_vision_geometry.py, test_vision_signals.py, test_person_presence.py.
- Antes de tocar detección: leer §13 (comparación con remind-reid-tracker-main/
  y hoja de ruta WAVE-11+) — puede que la mejora que buscas ya esté diseñada ahí.

Tarea: <describe el cambio>
```

---

## 10. Inventario de constantes clave (código)

Archivo: `vision/person_detector.py` (1916 líneas — verificado `wc -l`, sesión 5)

| Símbolo | Valor / idea |
|---------|----------------|
| `DEFAULT_YOLOE_WEIGHTS` | `yoloe-26n-seg.pt` |
| `_BASE_PERSON_PROMPTS` | person, persona, people, human, man, woman, estudiante |
| `_PERSON_LABELS` | person, persona, people, human, hombre, mujer, estudiante, student (conjunto distinto de `_BASE_PERSON_PROMPTS`, usado para clasificar salidas del modelo) |
| `_OPEN_VOCAB_ALIASES` | mapeo etiqueta → prompts (sin genéricos de camisa) |
| `_SOURCE_PRIORITY` | `logo_ref`/`logo_ref_verified`/`logo_chest` (3) > `open_vocab_snapped` (1) > desconocido (0). Nota: `yoloe_adhoc` (de `detect_labels`) no está en el mapa → rango 0 |
| `_LOGO_OPEN_VOCAB_MIN_CONF` | 0.45 (renombrada; antes `_UNIFORM_OPEN_VOCAB_MIN_CONF`. Atributo de instancia sigue expuesto como `self.uniform_ov_confidence` por compat) |
| `_MAX_OPEN_VOCAB_PROMPTS` | 40 |
| `_TMPL_MATCH_MIN` | **0.42** (override: `YOLO_LOGO_TMPL_MIN`) — antes documentado como 0.62 |

Archivo: `vision/geometry.py`

| Símbolo | Valor / idea |
|---------|----------------|
| `LOGO_Y0/Y1/X0/X1` | ROI **cuerpo completo**: `0.20 / 1.00 / 0.00 / 1.00` — antes documentado como banda de pecho `0.36/0.58/0.08/0.48` |
| `COLLAR_Y_MAX` | **0.25** (clamp 0.10–0.45) — antes documentado como 0.34 |
| `SNAP_MIN_W_FRACTION` / `SNAP_MIN_H_FRACTION` | **0.25 / 0.25** de la zona — antes documentado como 0.55/0.65 |
| `SNAP_MIN_SIDE_PX` | **45 px** — antes documentado como 50 px |
| `SNAP_CENTER_MARGIN` | 0.04 (no estaba en el inventario anterior) |

Archivo: `vision/image_signals.py`

| Símbolo | Valor / idea |
|---------|----------------|
| `HSV_HUE_BINS` / `HSV_SAT_BINS` | 18 / 16 |
| `GLARE_SAT_MAX` / `GLARE_VAL_MIN` | 40 / 180 (píxel «blanco») |
| `GLARE_RATIO_MAX` | 0.40 del parche |
| `GLARE_MEAN_SAT_MAX` / `GLARE_MEAN_VAL_MIN` | 32.0 / 175.0 |
| `TEMPLATE_SCALES` | 7 niveles: 0.14 → 0.80 |
| `ROI_MIN_STDDEV` / `TEMPLATE_MIN_STDDEV` | 4.0 / 8.0 (sin textura, no se matchea) |
| `ORB_FEATURES` / `ORB_RATIO` / `ORB_MIN_GOOD_MATCHES` | 700 / 0.75 / 14 |

---

## 11. Changelog breve (sesión de origen de este doc)

1. Unificación a **solo YOLOE-26n-seg**; eliminación de pesos duales y `YOLO_PERSON_MODEL`.
2. Fix **set_classes** / conf floor / defaults de umbral e imgsz.
3. Precisión **Uniforme ITEE**: aliases, estructura color, conf uniforme, veto de camisas genéricas.
4. Bbox: **cuello vs pecho** (collar ban, snap ROI, prefer logo_chest).
5. Este documento de handoff.

### Sesión 2: HSV + Multi-escala + Limpieza aliases

6. **Firma de color HSV** (`_compute_hsv_hist`, `_match_hsv_color_signature`): histograma 2D
   HSV compara candidatos contra fotos de Entrenar. Reemplaza el color hardcodeado ITEE.
7. **Pirámide multi-escala de 7 niveles** (`_match_template_multiscale`): escalas
   `0.14, 0.20, 0.28, 0.38, 0.50, 0.65, 0.80` relativas al ROI pecho.
8. **Limpieza `_OPEN_VOCAB_ALIASES`**: eliminados prompts genéricos (`blue shirt`,
   `polo shirt`, `school uniform` como prompts directos — solo se mantienen como
   mapeos de salida).

### Sesión 3: Tamaño proporcional + Rechazo de ventanas

9. **`_snap_box_to_logo_zone` proporcional** (§4.7):
   - `target_w = max(50px, 55% ancho pecho)`, `target_h = max(50px, 65% alto pecho)`.
   - **Bug corregido:** `_filter_uniform_objects` NO aplicaba snap al `refined` de
     `_verify_logo_reference` → cuadro de 20×20 px en el overlay.
10. **Rechazo de luz blanca / ventana** (§4.8):
    - `_is_white_light_or_glare`: Sat < 40 + Val > 180, ratio > 40% o Sat media < 32.
    - **Bug corregido:** el filtro de glare solo estaba en `_match_hsv_color_signature`
      (ROI pecho), pero NO en la caja YOLOE original. El YOLOE detectaba la ventana,
      la verificación fallaba en la ventana pero triunfaba en `person_box` (donde
      el logo sí existe) → falso positivo. Ahora se verifica glare en la caja
      YOLOE original ANTES de `_verify_logo_reference`.
11. **`_detect_logo_templates` sin personas → vacío**: eliminada la "persona falsa"
    que cubría todo el frame y causaba FP en ventanas.
12. Umbrales de glare ajustados (más agresivos): la versión anterior
    (Sat < 35, Val > 195, ratio > 55%) dejaba pasar ventanas con luz difusa.

### Sesión 4: Separación de módulos + bug de prioridad de fuente

13. **`vision/geometry.py` y `vision/image_signals.py`**: ~440 líneas de lógica
    pura salen de `person_detector.py` (2110 → 1880). Antes, probar aritmética de
    rectángulos obligaba a instanciar el detector y cargar Ultralytics; ahora son
    funciones puras con tests propios (`test_vision_geometry`, `test_vision_signals`).
    Los métodos del detector siguen existiendo como delegaciones finas, así que la
    API interna y los tests históricos no cambian.
14. **Bug corregido — la prioridad `logo_ref` no se aplicaba** (§4.3): el bloque
    de preferencia por fuente de `_detect_all` era código muerto porque
    `_dedupe_custom` ya había colapsado a una entrada por label ordenando por
    confianza. Ahora la prioridad vive en `_dedupe_custom` vía `_SOURCE_PRIORITY`
    y la confianza solo desempata dentro de la misma fuente.
15. **Números mágicos a constantes con nombre**: umbrales de glare, bins HSV,
    escalas del template, parámetros ORB y proporciones del snap estaban
    incrustados en el cuerpo de los métodos.
16. **`import cv2` / `import numpy` sacados de los bucles**: `_match_template_multiscale`
    los importaba **dentro** del bucle de plantillas, que corre en cada frame.
17. **Deduplicación de código**: el recorte+clampeo+chequeo de glare estaba
    copiado literal en las dos ramas de `_filter_uniform_objects` → `_box_is_glare`.
    El chequeo de `HOLOGRAM_YOLO_DEBUG` estaba repetido en 4 sitios → `_yolo_debug()`.
18. **`except Exception` genéricos acotados** a las excepciones reales
    (`cv2.error`, `TypeError`, `ValueError`…) en el código extraído: antes un
    error de programación quedaba enmascarado como «no hubo match».
19. **Docstring de `run_continuous` corregido**: documentaba
    `callback(event, count)` cuando siempre se invoca con
    `(event, count, analysis)`, y omitía `analysis_update` y
    `custom_object_detected`.

### Sesión 5: Corrección de números obsoletos + comparación con REMIND + hoja de ruta

20. **Auditoría completa de §4/§5/§7/§9/§10 contra el código real.** El doc
    llevaba desde sesión ~3 describiendo una geometría de "banda de pecho"
    (`y∈[0.36,0.58], x∈[0.08,0.48], collar 0.34`) que ya no existe — el código
    actual usa el cuerpo completo (`y∈[0.20,1.00], x∈[0.00,1.00], collar 0.25`,
    `vision/geometry.py:22-26`). También estaban desactualizados
    `_TMPL_MATCH_MIN` (0.62 documentado vs 0.42 real), `YOLO_LOGO_HSV_MIN`
    (0.35 vs 0.18), `YOLO_INTERVAL_SECONDS` (~0.6 vs 1.0), las proporciones de
    `_snap_box_to_logo_zone` (55%/65%/50px vs 25%/25%/45px), y el conteo de
    líneas de `person_detector.py` (1880 vs 1916 real). §7 protegía tres
    tests que ya no existen (el gate de estructura azul+amarillo fue
    eliminado). §9 (el prompt de handoff) repetía todos estos números viejos.
21. **Hallazgo: el gate `YOLO_LOGO_HSV_MIN` está inerte en producción.**
    Verificado leyendo `data/logo_index.npz` (solo tiene `meta_sig`, `by_img`,
    `by_des` — sin `by_hsv`) y el código de `_rebuild_logo_templates`: el
    camino de caché retorna antes de poblar `_logo_hsv_hists`, que además no
    se resetea en el bloque de reset. `compare_hsv_signature` hace fail-open
    (`return 1.0`) sin referencias. El color no ha estado filtrando nada. Ver
    §4.3 y §13 (I1).
22. **Hallazgo: las máscaras de segmentación se calculan y se descartan.**
    El modelo es `yoloe-26n-**seg**.pt` pero `_predict_boxes` solo lee
    `result.boxes`. Es el activo gratuito que habilita un descriptor de
    persona (§13, I5) sin coste de inferencia adicional.
23. **Comparación con `remind-reid-tracker-main/`** (§13, nueva): sistema de
    re-identificación vendorizado que nadie importa. Backbone DINOv3
    (torch+transformers) descartado por restricción de hardware del kiosco
    CPU, pero sus ideas algorítmicas (fusión ponderada por calidad, Hungarian
    con dummy adaptativo, locks antes de asignar, veto de empate, EMA
    margin-gated) son portables sin esa dependencia. Documentadas 7 mejoras
    concretas (I1–I7) secuenciadas en WAVE-11 a WAVE-17, con evaluación
    honesta de qué es y qué no es alcanzable para identidad de persona sin
    DINOv3 en un kiosko donde todos los estudiantes visten el mismo uniforme
    (el problema de "las cuatro sillas idénticas" de REMIND).
24. **Nueva §12**: razonamiento módulo por módulo de `vision/`, nombrando
    explícitamente las cuatro brechas (sin identidad de persona, colapso
    multi-instancia, escalera de logo frágil, sin estabilidad temporal) como
    diseño actual, no como bugs a corregir en el momento.

### Sesión 6: WAVE-11 — caché de logos corregida y referencias aisladas (I1)

25. **`_rebuild_logo_templates` arreglado** (`person_detector.py`): el bloque
    de reset ahora también vacía `_logo_hsv_hists` (antes solo
    `_logo_templates`/`_logo_images`), la caché `data/logo_index.npz` guarda y
    lee `by_hsv` junto con `by_img`/`by_des`, y se añadió `cache_version` al
    esquema: un npz viejo (sin `by_hsv` ni `cache_version`) se rechaza y se
    reconstruye en vez de cargarse a medias. El `logo_index.npz` de disco se
    regeneró en formato v2. El gate HSV (I1) **sigue inerte por diseño**: el
    default de `YOLO_LOGO_HSV_MIN` bajó de `0.18` a `0.0`, y cada match
    aceptado registra `color_score` bajo `HOLOGRAM_YOLO_DEBUG=1` — los datos
    para que I3 (WAVE-13) promueva HSV de veto a canal ponderado.
26. **Fallback cruzado aislado por etiqueta**: `_logo_templates_for` /
    `_logo_orb_for` / `_logo_hsv_hists_for` solo aplican el fallback entre
    etiquetas cuando existe **exactamente una** etiqueta entrenada (el caso de
    bootstrap de una sola escuela). Con dos o más colegios, la etiqueta X ya
    no casa contra las plantillas de la escuela Y.
27. `_rebuild_logo_templates` acepta ahora `base_dir` opcional (tests) para no
    leer el `data/` real. Tests nuevos: `tests/test_logo_index_cache.py`
    (reset, esquema v2, carga desde caché, rechazo de npz viejo, aislamiento
    del fallback). El fixture `_make_detector` de `test_custom_object_interval.py`
    ahora también limpia `_logo_hsv_hists`, que la caché corregida empezaba a
    poblar y rompía dos tests de open-vocab.

### Sesión 7: WAVE-12 — logos multi-instancia, un logo por persona (I2)

28. **Bucles invertidos en `_detect_logo_templates`** (`person_detector.py`):
    ahora es `for roi: for label:` en vez de `for label: for roi:`. Antes el
    "mejor global" por etiqueta colapsaba a **una** caja aunque hubiera varios
    estudiantes con el mismo uniforme entrenado; ahora cada ROI de pecho emite
    **su** mejor etiqueta y dos personas idénticas generan dos objetos. Cada
    detección lleva `person_index` (índice 0-based en `persons`, vía
    `best_person_for_box`).
29. **`_dedupe_custom` cambia su clave**: antes `label`, ahora `(label,
    person_index)`. Dos personas con el mismo uniforme ya no se colapsan. Sin
    `person_index` (open-vocab, tests) la clave degenera a `(label, None)` y el
    comportamiento es idéntico al previo. `_detect_all` propaga el
    `person_index` de cada hit de `logo_ref` al objeto final.
30. Tests nuevos en `test_custom_object_interval.py`: dos estudiantes con el
    mismo logo producen dos hits con `person_index` `{0, 1}`, y
    `_dedupe_custom` mantiene dos entradas para `(L, 0)` / `(L, 1)` pero
    colapsa `(L, None)`. Verificada la puerta de regresión: ambos fallan si se
    revierte solo `person_detector.py`.

### Sesión 8: WAVE-13 — fusión ponderada por calidad de logos (I3)

31. **Módulo nuevo puro `vision/scoring.py`** (solo numpy, sin cv2): implementa
    `score = Σ(w_c·q_c_eff·s_c) / Σ(w_c·q_c_eff)` sobre los canales
    template / ORB / HSV. Cada canal tiene peso (`CHANNEL_WEIGHTS` = 0.5 / 0.3
    / 0.2) y piso de calidad (`CHANNEL_FLOORS` = 0.40 / 0.50 / 0.30). Un canal
    **sin evidencia** (`s_c is None`) se elimina del numerador Y del
    denominador — el arreglo estructural de la clase de bug que I1 corrige
    puntualmente (un 1.0 silencioso por "no sé" inflaba la fusión como un
    match real). `channel_quality_eff` expone la calidad efectiva por canal.
32. **`_match_logo_in_gray` usa la fusión detrás de `YOLO_LOGO_FUSION=1`**: la
    escalera `if/elif` (template → orb+template → orb) sigue siendo el default
    hasta recalibrar el umbral contra una sesión grabada, como pide el §13 I3.
    En la rama de fusión, el canal ORB se marca sin evidencia si no hay
    descriptores, el HSV siempre aporta (`color_score` ya inerte en I1) y la
    localización la sigue dando el template (o el centro del ROI sin él).
33. Tests nuevos: `tests/test_vision_scoring.py` (media ponderada, canal sin
    evidencia excluido del denominador, evidencia bajo el piso pesa menos,
    pesos suman 1.0) y `test_logo_ref_fusion_path_via_env_flag` en
    `test_custom_object_interval.py` (match de template aceptado con
    `YOLO_LOGO_FUSION=1`). Puerta de regresión verificada: ambos fallan sin
    `vision/scoring.py` ni el cambio en `person_detector.py`.

### Sesión 9: WAVE-14 — histéresis M-of-N de custom objects (I4)

34. **Módulo nuevo puro `vision/tracking.py`**: máquina `NEW→TENTATIVE→
    CONFIRMED→INACTIVE` sobre el conjunto de etiquetas (`LabelHysteresis`).
    Un label arranca en `TENTATIVE` con 1 avistamiento y solo pasa a
    `CONFIRMED` tras `confirm_cycles` avistamientos **consecutivos** (default
    2), emitiendo `"detected"` exactamente una vez. Un `CONFIRMED` que deja de
    verse durante `forget_seconds` (default 10 s) pasa a `INACTIVE` y emite
    `"forgotten"`. Un `TENTATIVE` que se pierde un ciclo vuelve a `NEW` (el
    parpadeo no cuenta como evidencia) y al reaparecer debe volver a acumular
    ciclos. Los `INACTIVE` se purgan tras `retain_seconds` (default 60 s).
    Recibe `now` por parámetro: puro, determinista, sin time real.
35. **`run_continuous` usa el tracker** (`person_detector.py`): el diff de sets
    `current - last` (prone a re-disparar por un parpadeo) se reemplaza por
    `self._label_tracker.update(...)`; `custom_object_detected` solo se emite
    con labels que **concluyen** su confirmación. Parámetros por env:
    `YOLO_CUSTOM_CONFIRM_CYCLES` (2), `YOLO_CUSTOM_FORGET_SECONDS` (10),
    `YOLO_CUSTOM_RETAIN_SECONDS` (60).
36. Tests nuevos: `tests/test_tracking.py` (unidad: parpadeo de un ciclo no
    confirma, confirmación exacta una vez, olvido por ausencia, reinicio de
    progreso, purga de INACTIVE, independencia multi-label, `confirm_cycles=1`)
    y `tests/test_custom_hysteresis.py` (integración en `run_continuous`:
    parpadeo sin re-disparo, label único nunca detectado, sostenido se detecta
    una vez, vuelta tras olvido re-confirma). Puerta de regresión verificada:
    los archivos de test fallan sin `vision/tracking.py` ni el cambio del
    detector.

---

## 12. Razonamiento parte por parte de `vision/`

Seis archivos, dos capas: `geometry.py` e `image_signals.py` son **puros**
(sin importar `cv2`/`numpy` a nivel obligatorio — `image_signals.py` los
envuelve en `try/except` y degrada a valor neutro si faltan; `geometry.py` no
los necesita en absoluto). Por eso `tests/test_vision_geometry.py` y
`tests/test_vision_signals.py` corren sin instalar Ultralytics. Todo lo demás
depende de OpenCV y, para inferencia real, de `ultralytics.YOLOE`.

Dependencia: `person_detector.py` → `{geometry, image_signals, camera, face_analyzer}` + `utils._env*`.

### 12.1 `camera.py` (166 líneas)

Wrapper de `cv2.VideoCapture` con semántica de gestor de contexto. Decisiones:
selección de backend (`CAP_DSHOW`/`CAP_MSMF`/`CAP_V4L2`) **solo** cuando
`source` es un índice entero, nunca para un archivo; el backend se elige por
`HOLOGRAM_CAMERA_BACKEND` o, si no está seteado, por `platform.system()`. No
hay locks ni protección de hilos — el diseño asume un único dueño (el hilo
`yolo-camera`), y eso es correcto porque `run_continuous` es el único llamador
en producción. `read_frame()` devuelve `None` en vez de lanzar excepción
cuando la captura falla, delegando la decisión de "reintentar o abortar" al
llamador. `__exit__` no traga excepciones (devuelve `False`) — es el mecanismo
real por el que `stop()` apaga la cámara: sale del `with`, se llama `release()`.

### 12.2 `geometry.py` (233 líneas, sin `cv2` ni `numpy`)

Aritmética pura de rectángulos. La función más importante para entender el
sistema es `snap_box_to_logo_zone` (§4.7): **no centra la caja en una zona
fija**, preserva la ubicación detectada y solo (a) la empuja por debajo del
cuello si quedó por encima, (b) la agranda si es más pequeña que el mínimo
proporcional, nunca la achica. `best_person_for_box` resuelve qué persona es
dueña de una caja con una heurística de dos pasos: primero contención
(la persona más grande que contiene el centro de la caja), luego distancia
mínima al centro. Esta función existe hoy solo para el snap — §13 (I2) la
reutiliza para atribuir logos a personas.

**Limitación honesta:** el nombre "logo"/"chest" en variables y funciones
(`LOGO_Y0`, `chest_zone`, `_logo_roi_fractions`) es vocabulario heredado de
cuando la zona era literalmente el pecho. Hoy es el cuerpo completo. No
renombrar sin medir el impacto — muchos tests y tres archivos consumidores
usan estos nombres.

### 12.3 `image_signals.py` (228 líneas)

Primitivas de similitud de imagen: histograma HSV 2D (18×16), rechazo de
brillo/ventana (`is_white_light_or_glare`), template matching multi-escala
(7 niveles), y ORB. **Limitación honesta y deliberada:** `compare_hsv_signature`
es *fail-open* — devuelve `1.0` (no rechazar) sin referencias, en escala de
grises, o si OpenCV falla; el color nunca es, por diseño, la razón de un
rechazo ambiguo. Eso es correcto como principio, pero combinado con el bug de
§4.3 (referencias vacías por la caché) significa que hoy el color **nunca**
rechaza nada, ni siquiera cuando sí hay evidencia de mismatch — el fail-open
que debía ser la excepción se volvió la regla.

### 12.4 `face_analyzer.py` (81 líneas)

Haar cascade de OpenCV, cuenta rostros frontales. Explícitamente **no** hace
identidad, edad, género ni emoción — está en el docstring del módulo. Gateado
por `HOLOGRAM_FACE_ANALYSIS == "1"` (debe ser exactamente ese string) en
`analyze_frame`.

### 12.5 `person_detector.py` (1916 líneas) — el núcleo

Orden de lectura recomendado para un agente nuevo:

1. **Carga de pesos** (`_normalize_weights_name`, `_load_yoloe`, `load()`):
   un solo checkpoint YOLOE; cualquier nombre legacy o de la familia World se
   reescribe al canónico con una advertencia impresa. Un fallo de carga deja
   `model=None` pero **igual** reconstruye el índice de logos (`_rebuild_logo_templates`
   se llama siempre en `load()`) — el matching de logo sobrevive a un modelo caído.
2. **Prompts** (`_apply_classes`, `set_prompts`): `_prompt_key` cachea la
   última lista pasada a `set_classes` para no re-encodear CLIP cada ciclo —
   es un no-op si la clave no cambió.
3. **Datos de Entrenar** (`_load_training_data`, polling cada 5 s vía
   `_maybe_reload_training`): así es como la UI de Entrenar llega a un kiosko
   corriendo sin reiniciar.
4. **El indexador** `_rebuild_logo_templates`: construye plantillas grises +
   descriptores ORB + histogramas HSV desde las fotos de referencia, con
   caché en `data/logo_index.npz` keyed por `mtime+size` del metadata. Ver
   §4.3 para el bug de caché conocido.
5. **El matcher** `_match_logo_in_gray`: la escalera de decisión de tres
   señales (HSV → template → ORB), ver §4.3.
6. **Dos rutas convergentes hacia el mismo resultado:**
   - *Bottom-up* (`_detect_logo_templates`, source=`logo_ref`): escanea el
     ROI de cada persona contra cada etiqueta entrenada.
   - *Top-down* (`_filter_uniform_objects`, source=`logo_ref_verified`): un
     hit open-vocab de YOLOE (≥0.45) es **solo una sugerencia** que debe
     confirmarse contra la foto de Entrenar, o se descarta.
7. **`_dedupe_custom`**: colapsa por `label`, prioriza por fuente
   (`_SOURCE_PRIORITY`) y solo desempata por confianza dentro de la misma
   fuente. Ver la nota de límite conocido en §4.3.
8. **El buffer MJPEG** (`_store_annotated_frame`, `feed_subscribe`/`unsubscribe`):
   el encode a JPEG solo ocurre si hay suscriptores; la detección YOLO nunca
   se apaga por falta de viewers.
9. **`run_continuous`**: la máquina de presencia. Estado local (no de
   instancia, se reinicia en cada arranque del bucle): `was_present`,
   `present_since`, `absent_since`, `last_custom_labels`. Debounce de entrada
   (`PRESENCE_ENTER_SECONDS`) y de salida (`PRESENCE_ABSENCE_SECONDS`).

### 12.6 Las cuatro brechas — diseño actual, no bugs puntuales

Estas cuatro son **límites de diseño**, no descuidos a corregir con un parche
rápido — cada una tiene una mejora dedicada en §13:

1. **Sin identidad de persona.** `model.track()` nunca se llama;
   `_split_detections` produce una lista anónima nueva cada ciclo. "La misma
   persona" ≡ "`person_count>0` no llegó a 0 durante `PRESENCE_ABSENCE_SECONDS`
   (5 s)". Consecuencia observable: si el estudiante A se va y el estudiante B
   llega en menos de 5 s, el sistema cree que es la misma presencia continua y
   **B nunca recibe el saludo de entrada**.
2. **Colapso multi-instancia.** `_dedupe_custom` indexa solo por `label` — dos
   personas con el mismo uniforme entrenado producen un único objeto en
   `analysis["custom_objects"]`.
3. **Escalera de decisión frágil para logos.** Pesos y umbrales fijados a
   mano (`0.75·tmpl + 0.25·orb`, etc.) en vez de una fusión que pondere por
   la calidad de cada señal.
4. **Sin estabilidad temporal de etiquetas.** `run_continuous` compara el
   conjunto de etiquetas custom del ciclo actual contra **solo** el ciclo
   anterior (`:1859-1864`) — un parpadeo de detección de un ciclo re-dispara
   `custom_object_detected`. El único freno es un cooldown de 60 s por
   etiqueta en `call.py:1322`, que amortigua el síntoma sin corregir la causa.

Y dos bugs latentes, distintos del de HSV, que conviene tener presentes:

- El fallback cruzado en `_logo_templates_for`/`_logo_orb_for`
  (`person_detector.py:899-907,921-925`): si una etiqueta "parece uniforme" y
  no tiene sus propias referencias, el código devuelve la concatenación de
  las referencias de **todas** las etiquetas entrenadas. Con una sola escuela
  entrenada esto es inofensivo (es el caso de bootstrap para el que se
  escribió); con dos o más escuelas, la etiqueta X puede casar legítimamente
  contra las plantillas de la escuela Y.

---

## 13. Comparación con `remind-reid-tracker-main/` y hoja de ruta de mejoras

`remind-reid-tracker-main/` es un sistema de re-identificación multi-objeto
vendorizado en la raíz del repo. **Nada en `vision/` lo importa** — es
material de referencia, no código en producción. Su método (REMIND, ver
`REMIND_METHOD.md` en ese directorio) resuelve re-identificación online con
cámara en movimiento: un forward de DINOv3 (ViT congelado, HuggingFace
`transformers`+`torch`) produce descriptores por parche, agrupados por máscara
de segmentación en varios canales (global, partes por k-means, anillos de
fondo), fusionados con pesos ajustados por calidad, asociados con Hungarian
(`scipy.optimize.linear_sum_assignment`), y almacenados en un banco de
prototipos dual (work/stable) con promoción y expulsión.

**El backbone (DINOv3, torch+transformers, ~2.5 GB) queda descartado para
este proyecto** — no por calidad, sino porque el kiosko es CPU y corre
`yoloe-26n-seg` a `imgsz=416` y ~1 detección/segundo; un forward de ViT por
frame no cabe en ese presupuesto. Lo que sí se porta son las **ideas
algorítmicas de asociación y fusión**, que son independientes del backbone —
y `scipy` (para `linear_sum_assignment`) **ya está instalado**, llega como
dependencia de `ultralytics` (verificado: `scipy 1.17.1` en `.venv`), así que
usarlo no añade una dependencia nueva.

### 13.1 Siete mejoras propuestas

| # | Mejora | Brecha (§12.6) | Coste CPU |
|---|---|---|---|
| I1 | Corregir caché `logo_index.npz` + aislar referencias por etiqueta | robustez de logo | arranque, ≈0 |
| I2 | Atribución por persona (`person_index`) y dedupe multi-instancia | multi-instancia | **cero** |
| I3 | Fusión ponderada por calidad reemplaza la escalera de `_match_logo_in_gray` | robustez de logo | ≈300 flops/s |
| I4 | Histéresis M-of-N para `custom_object_detected` | estabilidad temporal | gratis |
| I5 | Descriptor de persona: HSV en 3 bandas agrupado por máscara de segmentación | identidad (habilitador) | 3–8 ms @ 1 Hz |
| I6 | Asociación: locks → Hungarian → dummy adaptativo → veto de empate | identidad | <1 ms/ciclo |
| I7 | Presencia derivada de tracks en vez de `was_present` booleano | identidad + temporal | gratis |

**I1 — Corregir caché npz + aislar referencias por etiqueta.**
Tres cambios en `_rebuild_logo_templates` (`person_detector.py:665`): (a)
añadir `self._logo_hsv_hists = {}` al bloque de reset en `:674-675`, que hoy
solo resetea `_logo_templates`/`_logo_images`; (b) guardar y leer `by_hsv` en
el `np.savez_compressed`/`np.load` del camino de caché (`:693-712,796-803`);
(c) versionar la caché (`cache_version`) para que el `logo_index.npz` que ya
existe en disco — sin `by_hsv` — se rechace y se reconstruya en vez de
cargarse a medias. Además, limitar el fallback cruzado de
`_logo_templates_for`/`_logo_orb_for`/`_logo_hsv_hists_for` a que solo aplique
cuando existe **exactamente una** etiqueta entrenada (el caso de bootstrap
para el que se escribió), no para cualquier etiqueta que "parezca uniforme".
**No reactivar el veto HSV en el mismo cambio**: desplegar con
`YOLO_LOGO_HSV_MIN=0.0`, registrar `color_score` bajo `HOLOGRAM_YOLO_DEBUG=1`
en cada match aceptado, y dejar que I3 promueva HSV de veto a canal ponderado
con datos reales de iluminación del kiosko.

**I2 — Atribución por persona y dedupe multi-instancia.** Invertir los bucles
de `_detect_logo_templates` (hoy `for label: for roi: quedarse con el mejor
global` — estructuralmente no puede emitir dos instancias; pasar a `for roi:
for label: emitir el mejor para este roi`), etiquetar cada objeto con el
`person_index` de la persona dueña (usando `best_person_for_box`, ya en
`geometry.py`), y cambiar la clave de `_dedupe_custom` de `label` a
`(label, person_index)`. **Coste CPU cero**: `_detect_logo_templates` ya
ejecuta `len(labels)×len(rois)` llamadas al matcher; invertir los bucles
cambia cuál resultado se conserva, no cuántos se calculan. Compatible hacia
atrás por construcción: los seis tests de `tests/test_vision_geometry.py:186-227`
llaman `_dedupe_custom` sin `person_index` en sus fixtures, así que la clave
degenera a `(label, None)` y el colapso es idéntico al actual.

**I3 — Fusión ponderada por calidad.** Reemplazar la escalera `if/elif` de
`_match_logo_in_gray` por `score = Σ(w_c·q_c_eff·s_c) / Σ(w_c·q_c_eff)` sobre
tres canales (template, ORB, HSV), donde cada canal tiene un peso, un piso de
calidad, y **se elimina del denominador si no hay evidencia** (`q_c=None`) en
vez de aportar un `1.0` silencioso — el arreglo estructural para la clase de
bug que I1 corrige puntualmente. Vive en un módulo nuevo, puro,
`vision/scoring.py` (numpy únicamente). Desplegar detrás de
`YOLO_LOGO_FUSION=1` y recalibrar el umbral contra una sesión grabada antes
de cambiar el default.

**I4 — Histéresis M-of-N.** Máquina `NEW→TENTATIVE→CONFIRMED→INACTIVE` sobre
el conjunto de etiquetas, en un módulo nuevo puro `vision/tracking.py`. A
`YOLO_INTERVAL_SECONDS=1.0`: "visto en 2 ciclos consecutivos, olvidado tras
10 s de ausencia". Un parpadeo de un ciclo ya no re-dispara el evento.

**I5 — Descriptor de persona desde las máscaras.** `yoloe-26n-**seg**` ya
calcula máscaras que hoy se descartan (`_predict_boxes` solo lee
`result.boxes`). Leer `result.masks.data`, agrupar en 3 bandas horizontales
(cabeza/torso/piernas) un histograma HSV por banda, L2-normalizar. **No usar
ORB para esto** — los keypoints de una persona son inestables entre ciclos y
ante cambio de pose; ORB es correcto para logos rígidos e impresos, no para
personas. **No activar `retina_masks=True`** (revienta el presupuesto de
CPU); usar `masks.data` a resolución de protos. Correr **solo** dentro de la
rama de detección de `run_continuous` (1 vez/s), nunca en el camino del feed
MJPEG a ~30 fps. El descriptor **no debe entrar en `analysis`** — `main.py`
difunde ese dict por WebSocket y un array de cientos de floats por persona no
debe llegar al navegador.

**I6 — Asociación: locks → Hungarian → dummy adaptativo → veto de empate.**
Cuatro piezas de REMIND, las cuatro independientes de DINOv3, en un módulo
nuevo puro `vision/tracking.py` (scipy importado de forma perezosa, con
fallback greedy si falla): (a) *locks* antes de Hungarian — comprometer de
una vez un par cuando `s1≥0.90` y el margen sobre el segundo mejor es amplio;
(b) Hungarian con columnas dummy para "crear identidad nueva"; (c) **dummy
adaptativo a la confianza** — `dummy = clamp(0.05 + 0.20·(1−confianza), 0, 0.72)`:
cuanto menos confiado el mejor match, más atractivo se vuelve crear una
identidad nueva en vez de asignar mal; (d) **veto de empate** — si el mejor y
el segundo mejor puntaje quedan a menos de 0.05, no comprometer nada, arrastrar
la detección sin asignar al siguiente ciclo. Este último punto es la pieza
clave frente a uniformes idénticos: prefiere decir "no sé" a adivinar mal con
aparente confianza.

**I7 — Presencia derivada de tracks.** La máquina `was_present`/`present_since`/
`absent_since` de `run_continuous` se mantiene intacta; se le superpone el
estado de tracks de I6, y solo cuando el conjunto de tracks confirmados
cambia por completo sin que `person_count` llegue a 0 se emite `person_left`
seguido de `person_entered` en vez de continuar la misma presencia en
silencio. **Restricción de compatibilidad, la más importante de esta pieza:**
sin descriptor (`descriptor=None`, que es el caso de todos los tests
actuales, cuyos fixtures no traen máscara), el canal de apariencia se
descarta y la asociación queda solo con geometría — con cajas idénticas eso
converge al mismo comportamiento de hoy. Los siete tests de
`tests/test_person_presence.py` deben pasar **sin modificarse**; si necesitan
cambiar, el diseño está mal. Desplegar detrás de `YOLO_REID=0` (apagado por
defecto) y no activar el default hasta medir, en producción, con qué
frecuencia dispara el veto de empate de I6.

### 13.2 Qué NO portar, y por qué

- **Grafo de co-ocurrencia + beam search de vecinos.** REMIND lo necesita
  porque en una escena de veinte objetos, "la silla junto al escritorio con
  el portátil" desambigua cuatro sillas idénticas. Un kiosko ve 1–5 personas
  transitorias sin relación mutua estable — no hay escena con la cual
  co-ocurrir, y las estadísticas por episodio nunca saldrían del prior.
  Máxima superficie de código de la asociación de REMIND, ganancia esperada
  nula aquí.
- **Backtracking de estabilidad de identidad** (enumerar asignaciones
  alternativas de un componente de conflicto). Con N≤5 y un paso de locks
  previo, la ganancia marginal es ≈0. Portar solo la mitad barata: el test de
  "si el mejor y el segundo mejor quedan a menos de 0.05, negarse a
  comprometer" — eso ya está en I6 como el veto de empate.
- **Memoria dual de prototipos work/stable con promoción y expulsión.**
  Existe para sostener múltiples puntos de vista de un objeto rígido a lo
  largo de cientos de frames. Nuestros tracks viven ~10 s y un histograma HSV
  de torso ya es casi invariante al punto de vista — un solo descriptor
  actualizado por EMA con compuerta de margen (la pieza que sí vale la pena
  portar, dentro de I6/I7) alcanza lo mismo con una fracción del código.
- **Política de consistencia de fuente** (forzar que todos los candidatos de
  una detección puntúen contra el mismo banco). Existe solo porque hay dos
  bancos. Con un banco no hay nada que sea inconsistente.
- **Clases `AmbiguousTrack`/`ProvisionalNewTrack` con TTL y un segundo pase
  de Hungarian.** La idea — negarse a forzar accept/reject — es esencial y ya
  la da el veto de empate de I6. La maquinaria completa (tres clases, un
  segundo scoring, un segundo problema de asignación) es sobre-ingeniería
  para diferir una decisión seis frames a 1 Hz con ≤5 personas.
- **Canales de fondo y de partes basados en parches.** El análogo sin
  DINOv3 de "fondo" sería el histograma fuera de la máscara — que en un
  kiosko de posición fija es literalmente la misma pared para todas las
  personas. Cero información de identidad, y diluiría el denominador de la
  fusión de I3/I6.

### 13.3 La victoria más barata de alto valor: I2

Costo CPU cero, ~15 líneas de cambio real, compatible hacia atrás sin tocar
ningún test existente, y es la única mejora de esta lista que cambia de
inmediato lo que percibe el visitante: hoy dos estudiantes con uniforme ITEE
delante del kiosko producen `person_count: 2` y **un solo** objeto
`"Uniforme ITEE"` en el análisis — el LLM no puede decir "los dos llevan
uniforme del ITEE" porque ese dato no existe en `analysis`. Las demás mejoras
hacen más confiable lo que ya existe; ésta añade información que hoy no
existe. Es además prerrequisito de I6/I7: un track necesita poder poseer su
logo, lo que exige que el logo esté atribuido a una persona primero.

### 13.4 Identidad de persona sin DINOv3 — evaluación honesta

El descriptor de I5 es, en términos llanos, *color de piel/cabello, color de
camisa, color de pantalón* con el fondo quitado por la máscara — 3 a 6 bits
útiles de información, sensibles a la iluminación. El techo realista, por
escenario:

| Escenario | Resultado realista |
|---|---|
| 1 persona, presencia continua, luz estable | Prácticamente perfecto |
| 2–3 personas **con ropa distinta**, pocos minutos | Bien (>90 %) — conjunto cerrado diminuto con escape "crear nueva" |
| 2–3 personas **con el mismo uniforme ITEE**, cruzándose | **Falla.** La banda del torso es idéntica por construcción; esperar cambio de identidad en casi cada cruce |
| Misma persona que vuelve tras 10 minutos | **No intentar** |
| Identidad persistente entre sesiones o días | **Imposible, y peligroso fingir que funciona** |

Este es exactamente el problema de "las cuatro sillas idénticas" que motiva
el contexto relacional de REMIND — y REMIND **tampoco** lo resuelve con
apariencia sola, lo resuelve con "qué objetos co-ocurren", que en un kiosko
con 1–5 personas transitorias no existe (§13.2). No hay que esperar superar a
REMIND en su caso más difícil con un descriptor más débil y sin relaciones.
La respuesta correcta no es un descriptor mejor: es **detectar que el caso es
irresoluble y negarse a adivinar** — exactamente lo que hacen el veto de
empate y el dummy adaptativo de I6.

Declaración de alcance, para dejar por escrito y no reinterpretar después:

> El tracker responde *"¿la persona frente al kiosko ahora es la misma que
> estaba hace tres segundos?"*. No responde *"¿quién es?"*.

Con estas consecuencias obligatorias si se implementa I7: el track muere tras
~10 s de ausencia con **borrado duro** (no el `remove_enabled: false` de
REMIND — una galería sin límite de histogramas de menores de edad es un
pasivo, no una funcionalidad); nada persiste a disco; `track_id` nunca se
expone al LLM como una identidad. El pago medible es un bug concreto y
reproducible: hoy, si el estudiante A se va y el B llega en menos de 5 s,
`person_count` nunca toca 0 y B nunca recibe el saludo de entrada — corregir
eso solo exige distinguir "alguien distinto" de "el mismo alguien", un
requisito mucho más débil que distinguir A de B por identidad.

**Criterio de cancelación:** si después de desplegar I6 los registros muestran
el veto de empate disparando en la mayoría de los ciclos con más de una
persona, esa es la señal honesta de **cancelar I7** y quedarse con la máquina
de presencia por conteo que existe hoy. Medir eso es precisamente el motivo
de separar I6 (bajo riesgo, sin cambiar la experiencia del visitante) de I7
(alto riesgo, cambia los saludos).

### 13.5 Secuenciación en WAVEs

`docs/plans/execution/WAVE-08-politica-camara.md` declara los internos de
detección explícitamente **fuera de alcance** para esa wave, con un check de
pre-commit `git diff --stat sin vision/person_detector.py`. Por eso estas
mejoras se numeran **WAVE-11 en adelante**, después de WAVE-10, cada una en
su propia sesión y su propio commit — nunca dentro de WAVE-08.

| WAVE | Título | Mejora | Depende de | Riesgo |
|---|---|---|---|---|
| 11 | Índice de logos: caché correcta y referencias por etiqueta | I1 | — | Bajo |
| 12 | Multi-instancia: un logo por persona | I2 | — | Bajo |
| 13 | Fusión ponderada por calidad | I3 | 11 | Medio |
| 14 | Histéresis temporal de etiquetas | I4 | 12 (suave) | Bajo |
| 15 | Descriptor de persona desde máscaras de segmentación | I5 | — | Medio |
| 16 | Asociación: locks + Hungarian + veto de empate | I6 | 15, 13 | Medio |
| 17 | Presencia derivada de tracks | I7 | 16 + métricas de producción de 16 | **Alto** |

Prerrequisitos duros: 11→13 (la fusión necesita que el canal HSV exista de
verdad, no que esté fail-open); 15→16→17; 13→16 (16 reusa `vision/scoring.py`
creado en 13). Las waves 11, 12, 14 y 15 son mutuamente independientes y se
pueden reordenar o hacer en paralelo entre sesiones distintas.

---

*Si cambias la arquitectura YOLO, actualiza este archivo en el mismo PR/commit.*
