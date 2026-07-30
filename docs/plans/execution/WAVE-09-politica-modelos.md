# WAVE-09 — Política de modelos, presupuesto y fallback

| | |
|---|---|
| **Fase** | 3 · Endurecer |
| **Riesgo** | Bajo — cambia parámetros, no estructura. Pero es la WAVE con **decisión humana obligatoria** |
| **Esfuerzo** | 1 sesión |
| **Modelo sugerido** | `scout` (brief obligatorio) → Opus (código) → `worker` (tests) |
| **Cierra hallazgos** | F, G, M |
| **Decisiones que resuelve** | **D1** (`LLM_MAX_TOKENS`) · **D2** (modelo de razonamiento en `:free`) |

> Antes de empezar: leé `README.md` y `PROGRESS.md`. Re-localizá los símbolos con
> `graphify query`. Las líneas de este documento son orientativas.

> **Esta WAVE no se commitea sin una respuesta humana a D1 y D2.** No las asumas, no las
> "elijas por sentido común". Preguntá en la puerta y anotá la respuesta. Ver *Puerta de decisión*.

---

## Por qué

WAVE-01 desbloqueó el turno: arregló el `return` incondicional, el sangrado de `LLM_MODEL` y
subió el presupuesto de forma provisional. WAVE-03 nos dio los números reales. Lo que queda es
todo lo que sigue **fijado a mano dentro del código**: la temperatura, el presupuesto, el
timeout, y qué modelo le corresponde a cada proveedor. Hoy son constantes desperdigadas; al
terminar esta WAVE son una política declarada en un solo sitio, con tests.

### Hallazgo F · `temperature=0.6` fijada a mano en seis sitios

Medido en runtime sobre `llm_backend.py`:

```
L473    L734    L796    L875    L1008    L1042
```

Seis literales idénticos, en las rutas de chat y de streaming de los backends compatibles con
OpenAI (`_chat_with_openai_compatible` ≈L444, `_iter_openai_compatible_tokens` ≈L846,
`_stream_backend_response` ≈L972 y sus vecinos).

> Los `0.0` de `stt/listener.py` L1055 y L1112 son de **Whisper**, no del LLM. **No son parte de
> esta WAVE.** Si los tocás, te saliste del alcance.

Dos consecuencias, y la segunda es la que importa:

1. **Cambiar la temperatura hoy es tocar seis líneas.** El día que alguien toque cinco, el
   comportamiento del kiosco pasa a depender de por qué rama del fallback entró la pregunta.
   Es exactamente el bug que `_max_tokens()` ya resolvió para los tokens — y que sigue vivo para
   la temperatura.
2. **No hay política por tipo de consulta.** «¿Cuánto dura Programación Web?» y «Contame un
   chiste» se muestrean con el mismo 0.6. La primera es un dato institucional donde la variación
   es un riesgo de alucinación; la segunda es la única de las 11 donde la variación es deseable.

### Hallazgo G · Un solo presupuesto de tokens, compartido entre razonamiento y respuesta

```
_max_tokens()  (llm_backend.py ≈L44)   default en código: 450
.env del equipo: LLM_MAX_TOKENS=180  →  valor real en runtime: 180
```

El docstring de `_max_tokens` cuenta la historia útil: **antes cada backend traía su propio
número mágico** (350 / 450 / 1024 / sin límite), y la longitud de la respuesta cambiaba según el
proveedor y entre voz y web. Eso ya está unificado — el trabajo previo fue correcto y no hay que
deshacerlo. Lo que falta es lo que quedó pendiente:

- **Presupuesto por tipo de consulta.** 180 tokens es razonable para «¿Qué significa UNEV?» y
  demasiado poco para «¿Qué carreras ofrecen?».
- **Separar el presupuesto de razonamiento del de respuesta.** Hoy los 180 los comparten. Con un
  modelo de razonamiento, el *thinking* se come el presupuesto y al visitante no le llega nada.

Ese segundo punto es el hallazgo B de WAVE-01 visto desde el otro lado: WAVE-01 arregló que un
turno vacío **no se propague en silencio**; WAVE-09 arregla la causa de que el turno salga vacío.

### Hallazgo M · El fallo tarda 90 s en aparecer y el aviso que lo explica está apagado

**Timeout:** default **90,0 s** (`llm_backend.py` ≈L71–L76), único, y aplicado por proveedor. Con
la cadena `['openrouter', 'groq']` eso da el **~180 s antes de la primera palabra** medido en la
línea base. Un visitante frente a un holograma espera unos segundos; a los diez, se va.

Y el diagnóstico que explicaría el problema **está silenciado por configuración**. En
`_CotStreamMirror.finish` (≈L678) la primera línea es:

```python
    def finish(self, *, error: str | None = None) -> None:
        if not _cot_log_enabled():
            return
```

y más abajo (≈L709–714) vive exactamente el aviso que haría obvio el presupuesto compartido:

```python
        elif self.answer_chars == 0 and (self.think_chars + self.reasoning_chars) > 0:
            print(
                "[LLM/CoT] AVISO: solo hubo razonamiento (CoT), sin respuesta "
                "útil. Suele pasar si LLM_MAX_TOKENS se agota en el thinking.",
```

Con `LLM_LOG_COT=0` en el `.env` del equipo, **ese aviso nunca se imprime**. El repositorio ya
sabía cuál era el problema y la configuración apagó al mensajero.

Es el mismo acoplamiento **logging ↔ lógica** que WAVE-02 desarma en `feed`. Acá la regla es:
un **log de depuración** puede estar detrás de un flag; un **aviso de que el turno salió vacío**,
no. Son cosas distintas y hoy comparten interruptor.

---

## Precondiciones

```bash
git status --short                      # limpio
git log --oneline -1                    # WAVE-08 commiteada
.venv/bin/python -m pytest tests/ -q    # verde
```

**Dependencia dura con WAVE-01 y WAVE-03.**

- De **WAVE-01** viene el sangrado de `LLM_MODEL` ya cerrado en `resolve_model` (≈L230). Esta
  WAVE **no lo vuelve a arreglar**: lo convierte en política declarada y le pone tests. Verificá
  que ya esté hecho:

```bash
.venv/bin/python -c "
from provider_config import resolve_model
print('openrouter ->', resolve_model('openrouter'))
print('groq       ->', resolve_model('groq'))
print('PARAR: falta WAVE-01' if resolve_model('groq') == resolve_model('openrouter') else 'OK, WAVE-01 aplicada')
"
```

- De **WAVE-03** vienen los números con los que se decide D1. **Sin las métricas de las 11
  preguntas ya tomadas, no elijas un presupuesto**: sería el mismo número mágico de antes, con
  otro valor. Buscalos en `PROGRESS.md`.

---

## Puerta de decisión (antes de escribir código)

Esta WAVE arranca preguntando, no implementando.

### D1 · `LLM_MAX_TOKENS`

La propuesta del plan es **800** (frente a los 180 de hoy y los 450 del default en código).
Llevá a la puerta, sacados de WAVE-03:

- tokens de salida realmente usados por cada una de las 11 preguntas,
- cuántas respuestas se cortaron a mitad de frase,
- cuántos turnos terminaron con `answer_chars == 0`.

Con eso, proponé un número **y su reparto** entre razonamiento y respuesta. La respuesta humana
va a `PROGRESS.md` como definitiva (D1 pasa de "abierta" a "cerrada").

### D2 · Modelo de razonamiento en tier `:free` vs. no-razonador de pago

El modelo vivo es `nvidia/nemotron-3-nano-30b-a3b:free`. Dos propiedades, ambas malas para un
kiosco en vivo:

| Propiedad | Consecuencia |
|---|---|
| Es un modelo de **razonamiento** | Gasta presupuesto en *thinking* antes de la primera palabra útil, y ese *thinking* hay que filtrarlo (WAVE-02) |
| Es de tier **`:free`** | Cola compartida y *rate limits*: la latencia depende de cuánta gente use el tier, no de tu red |

Es la peor combinación de latencia posible para el único caso de uso que tenemos: una persona
parada frente a un holograma esperando que hable.

**El runbook registra la decisión, no la asume.** Las opciones a presentar:

- **(a)** Seguir con el `:free` y compensar con el corte local de WAVE-07 (las respuestas
  institucionales no llegan al LLM) más el presupuesto separado de esta WAVE.
- **(b)** Pasar a un no-razonador de pago: menos latencia a primera palabra, sin *thinking* que
  filtrar, con coste por token.
- **(c)** Un híbrido: no-razonador por defecto, razonador sólo para lo que lo necesite.

> **Sin llamadas de pago para "probar" modelos sin autorización explícita del usuario.** Si la
> respuesta es (b) o (c), lo que se cambia acá es la **política y el nombre del modelo**; la
> validación en vivo la habilita quien paga.

**ElevenLabs sigue fuera de alcance; Piper sigue siendo el TTS.** Si la conversación de D2 deriva
hacia la voz, cortala: no es de este plan.

Si D1 o D2 no tienen respuesta, **PARAR** y anotarlo en `PROGRESS.md`. Es una Puerta 0 legítima.

---

## Alcance

### 1. Una sola fuente para la temperatura

Un punto único que devuelve la temperatura a usar, y **las seis llamadas pasan a consultarlo**.
Nada de seis literales.

- El **default sigue siendo 0.6**. Esto es deliberado: si no declarás un tipo de consulta, el
  comportamiento es idéntico al de hoy. Una WAVE de endurecimiento que cambia el tono del
  holograma de refilón es una WAVE mal hecha.
- Por tipo de consulta, con la clasificación que ya produce el ensamblador de WAVE-05 (no
  inventes una taxonomía nueva): **dato institucional → baja**; **conversacional/creativo →
  la actual**.
- Configurable por entorno, con el nombre de variable documentado en `PROGRESS.md`.

### 2. Presupuesto por tipo de consulta, con razonamiento y respuesta separados

- Un presupuesto **de respuesta** por tipo de consulta, con el valor de D1 como base.
- Un presupuesto **de razonamiento** propio, para que el *thinking* no se coma la respuesta.
  Cómo se expresa depende del proveedor: si la API acepta un tope de razonamiento, usalo; si no,
  el tope total tiene que estar dimensionado **asumiendo** que el CoT consume su parte.
- El caso «se gastó todo en pensar» tiene que ser **detectable y detectado** (ver punto 4), no
  una respuesta vacía silenciosa.
- Reusá `_max_tokens()` (≈L44) como el punto donde vive esto. Ya es el sitio correcto y ya
  unificó los cuatro números mágicos anteriores: **extendelo, no lo reemplaces**.

### 3. Timeout escalonado y fast-fail de conectividad

El objetivo numérico está en `PROGRESS.md`: **peor caso de la cadena < 20 s**. Con dos
proveedores y 90 s cada uno, hoy es ~180 s.

- Separar **conexión** de **lectura**. Un proveedor que no resuelve o no acepta la conexión tiene
  que fallar en segundos, no en noventa.
- El timeout deja de ser un número por proveedor y pasa a ser un **presupuesto de la cadena
  completa**: lo que gasta el primer intento se le descuenta al siguiente. Si el presupuesto se
  agotó, no se intenta el tercero: se responde con lo que haya (skill local o mensaje de
  degradación) en vez de hacer esperar al visitante.
- **Fast-fail sin red**: si no hay conectividad, la cadena cloud no debe intentarse en absoluto.
  Es el caso más frecuente en una feria con wifi de campus.
- El streaming ya en curso **no** se corta por el presupuesto de la cadena: una vez que llegó el
  primer token, el turno es válido. El presupuesto gobierna los **intentos**, no la generación.

### 4. Avisos de diagnóstico independientes del log de CoT

- El aviso de ≈L709–714 (**respuesta vacía con razonamiento presente**) deja de depender de
  `_cot_log_enabled()`. Se emite siempre, porque no es depuración: es un fallo de producto.
- Lo mismo para los avisos de WAVE-01 (proveedor caído, modelo no válido para el proveedor) si
  siguieran atados al mismo flag.
- El **log verboso** de CoT (chars pensados, tail, volcado) **sigue** detrás de `LLM_LOG_COT`.
  La distinción es: *log* = flag; *aviso de fallo* = siempre.
- Los avisos pasan por `redact_secrets()` (`security.py` ≈L61) antes de imprimirse. Ya existe;
  no escribas otro.
- Se registran en las métricas de WAVE-03, no sólo en `stdout`.

### 5. Política de proveedor y modelo, declarada

`provider_config.py` — `select_backend` ≈L192, `resolve_model` ≈L230,
`configured_cloud_providers` ≈L277.

- **Cada proveedor tiene su modelo**; ningún identificador namespaceado de un proveedor puede
  llegar a otro. WAVE-01 lo cerró en `resolve_model`; acá se documenta como política y se
  blinda con test.
- Un proveedor **sin modelo válido configurado no entra en la cadena**. Hoy entra y falla con
  404 tras el timeout: es peor que no estar.
- El orden de la cadena y el criterio para estar en ella quedan escritos en `PROGRESS.md`.

### Archivos
`llm_backend.py`, `provider_config.py`, el emisor de métricas de WAVE-03, `.env.example` (si
existe) y la documentación de configuración, más tests.

**`.env` y `config.json` NO se tocan.** Los valores elegidos se documentan; cambiarlos en la
máquina del equipo es acción del operador.

---

## Fuera de alcance

- **Rotar la clave de Groq (SEC-1).** Está reportada en `PROGRESS.md` y es acción humana, no
  código. Acá no se toca `config.json` ni se mueven secretos.
- **Añadir proveedores nuevos.** La cadena es la que hay.
- **Llamadas de pago para comparar modelos** sin autorización explícita del usuario.
- **ElevenLabs.** Piper sigue siendo el TTS. Fuera de discusión en este plan.
- El filtro de razonamiento en el stream → **WAVE-02** (ya hecho). Acá se ajusta el
  *presupuesto* del razonamiento, no su *filtrado*.
- El tamaño del contexto → **WAVE-04/05**. Si el prompt sigue siendo grande, el problema no es
  el presupuesto de salida.
- La memoria y su coste en tokens → **WAVE-06**.
- Los `0.0` de Whisper en `stt/listener.py`.
- **Refactor de `llm_backend.py`.** Es grande y la tentación de reordenarlo mientras se tocan
  seis literales es real. El `git diff` de esta WAVE tiene que ser aburrido.

---

## Tests a añadir

Archivo: `tests/test_model_policy.py` (nuevo).

> `tests/test_provider_config.py` ya existe. **No lo modifiques**: si tu cambio lo rompe, la
> política que escribiste cambió comportamiento que no debía cambiar (regla de la Puerta 1).

| Caso | Qué prueba | Debe fallar sin el fix porque… |
|---|---|---|
| `test_temperatura_una_sola_fuente` | En `llm_backend.py` no queda ningún literal de temperatura en los sitios de llamada; todos consultan el punto único. | Hoy hay **seis** literales `0.6`. **Es el hallazgo F.** |
| `test_temperatura_default_sin_cambio` | Sin tipo de consulta declarado, la temperatura sigue siendo la de hoy. | Guardarraíl: esta WAVE no cambia el tono del holograma por accidente. |
| `test_temperatura_por_tipo_de_consulta` | Dato institucional y creativo obtienen temperaturas distintas. | No existe la noción de tipo. |
| `test_presupuesto_por_tipo_de_consulta` | Dos tipos → dos presupuestos, ambos derivados del valor de D1. | Hoy hay un único número para todo. |
| `test_presupuesto_razonamiento_separado` | El presupuesto de respuesta no se ve reducido por el de razonamiento. | Hoy los comparten. **Es el hallazgo G.** |
| `test_respuesta_no_vacia_con_modelo_de_razonamiento` | Con un doble que emite CoT largo y luego respuesta corta, llega respuesta al usuario. | Con 180 compartidos, el doble reproduce el turno vacío de producción. |
| `test_aviso_de_turno_vacio_sin_log_de_cot` | Con `LLM_LOG_COT=0`, el aviso de "sólo hubo razonamiento" **se emite igual**. | `finish` hace `return` en la primera línea. **Es el hallazgo M y el test más importante de esta WAVE.** |
| `test_log_verboso_sigue_detras_del_flag` | Con `LLM_LOG_COT=0`, el volcado de CoT **no** se imprime. | Guardarraíl del lado opuesto: no conviertas todo en ruido. |
| `test_avisos_pasan_por_redact_secrets` | Un aviso que contenga algo con forma de clave sale enmascarado. | Reusa `security.py::redact_secrets`; si escribiste otro, este test lo delata. |
| `test_fast_fail_sin_conectividad` | Sin red, la cadena cloud no se intenta y se responde en < 1 s. | Hoy espera el timeout completo. |
| `test_presupuesto_de_la_cadena` | Con dos proveedores que cuelgan, el tiempo total queda **bajo el objetivo de 20 s**. | Hoy son 90 s × 2. |
| `test_stream_en_curso_no_se_corta` | Una generación que ya emitió tokens no se aborta por el presupuesto de la cadena. | Guardarraíl: el presupuesto gobierna intentos, no generación. |
| `test_proveedor_sin_modelo_no_entra_en_la_cadena` | Un proveedor sin modelo válido se salta, no se intenta. | Hoy se intenta y da 404 tras el timeout. |
| `test_modelo_no_sangra_entre_proveedores` | El id de un proveedor nunca llega a otro. | Blindaje de lo que cerró WAVE-01: si alguien lo reabre, salta acá. |

Para los timeouts, **inyectá el reloj y los dobles de transporte**. Un test que espera 20 s no es
un test — es la misma queja que WAVE-06 hace del `sleep`.

---

## Verificación

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_model_policy.py -v
git stash && .venv/bin/python -m pytest tests/test_model_policy.py -q ; git stash pop
.venv/bin/ruff check .

# Hallazgo F: no debe quedar ningún literal de temperatura en los sitios de llamada
grep -n "temperature\s*=" llm_backend.py

# El punto único, y el presupuesto por tipo (adaptá a los símbolos reales)
.venv/bin/python -c "
from llm_backend import _max_tokens
print('presupuesto por defecto:', _max_tokens())
"

# Configuración viva, SIN secretos
.venv/bin/python -c "
from provider_config import select_backend, resolve_model, configured_cloud_providers
b = select_backend()
print('backend:', b)
print('cadena :', configured_cloud_providers())
for p in configured_cloud_providers():
    print(f'  {p:12} -> {resolve_model(p)}')
"
```

La salida del último bloque va al reporte: **nombres de proveedor y modelo, nunca claves.**

**Prueba manual obligatoria** — esta WAVE se mide con un cronómetro, no con asserts:

1. **Turno normal, por voz.** Cronometrá de la última sílaba de la pregunta a la primera del
   holograma. Anotá el número.
2. **Wifi apagado.** Preguntá algo. Debe responder rápido (skill local o degradación), **no**
   quedarse mudo 180 s.
3. **La pregunta que más se cortaba** según WAVE-03. Debe llegar completa con el presupuesto de
   D1.
4. **`LLM_LOG_COT=0` y un turno que salga vacío** (forzalo bajando el presupuesto a propósito en
   una prueba local): el aviso **tiene que aparecer** en consola.

El paso 4 es el que cierra el hallazgo M. Anotá los cuatro resultados en `PROGRESS.md`.

---

## Criterios de aceptación

1. **D1 y D2 respondidas por un humano** y anotadas en `PROGRESS.md`, con fecha. Sin esto la WAVE
   no se commitea.
2. `grep -n "temperature\s*=" llm_backend.py` no devuelve literales en los sitios de llamada: los
   seis consultan el punto único.
3. Sin tipo de consulta declarado, la temperatura efectiva es **la de hoy**. Número pegado.
4. Existe presupuesto por tipo de consulta, con el valor de D1, y el de razonamiento está
   separado del de respuesta.
5. Con un doble que emite CoT largo, el visitante recibe respuesta. Cero turnos con
   `answer_chars == 0` en las 11 preguntas.
6. El aviso de "sólo hubo razonamiento" **se emite con `LLM_LOG_COT=0`**; el log verboso **no**.
7. Los avisos pasan por `redact_secrets()`; ninguna salida contiene algo con forma de clave.
8. Peor caso de la cadena **< 20 s** (base: ~180 s). Medido, con el número pegado.
9. Sin conectividad, la cadena cloud no se intenta.
10. Un proveedor sin modelo válido no entra en la cadena; ningún id de modelo cruza de proveedor.
11. Las 4 pruebas manuales hechas y anotadas, incluido el cronómetro del paso 1.
12. `.env` y `config.json` **no** aparecen en el diff.
13. `tests/test_provider_config.py` **no** modificado.
14. Las pruebas previas pasan.

---

## Checklist pre-commit

El compartido de `README.md`, más:

```
[ ] D1 respondida por humano, con el número y el reparto anotados en PROGRESS.md
[ ] D2 respondida por humano, con la opción elegida y por qué
[ ] Cero llamadas de pago hechas sin autorización explícita
[ ] grep -n "temperature\s*=" llm_backend.py → sin literales en los sitios de llamada
[ ] Default de temperatura idéntico al actual (test verde)
[ ] Presupuesto de razonamiento separado del de respuesta
[ ] Aviso de turno vacío verde con LLM_LOG_COT=0
[ ] Log verboso sigue apagado con LLM_LOG_COT=0 (el test del lado opuesto)
[ ] Avisos por redact_secrets() de security.py — sin implementación nueva
[ ] Peor caso de la cadena medido y < 20 s
[ ] Fast-fail sin red verificado a mano (wifi apagado)
[ ] stt/listener.py NO tocado (los 0.0 son de Whisper)
[ ] tests/test_provider_config.py NO modificado
[ ] .env y config.json fuera del diff
[ ] git diff | grep -iE 'sk-|gsk_|api[_-]?key' → sin resultados
[ ] Sin refactor oportunista de llm_backend.py (diff leído línea por línea)
[ ] Las 4 pruebas manuales hechas, con el cronómetro anotado
```

---

## Commit

```
fix(llm): WAVE-09 política de modelos, presupuesto y fallback

- temperatura: seis literales 0.6 fijados a mano pasan a un punto único con
  política por tipo de consulta; el default no cambia el comportamiento actual
- presupuesto de tokens por tipo de consulta y, sobre todo, presupuesto de
  razonamiento separado del de respuesta: el thinking deja de comerse la
  respuesta del visitante
- timeout escalonado y presupuesto de cadena en vez de 90 s por proveedor;
  fast-fail sin conectividad y proveedores sin modelo válido fuera de la cadena
- los avisos de diagnóstico dejan de depender de LLM_LOG_COT: el aviso de
  "solo hubo razonamiento, sin respuesta útil" ya existía en el repositorio y
  la configuración lo tenía apagado. El log verboso sigue detrás del flag
Cierra: hallazgos F, G, M · decisiones D1, D2
Métrica: peor caso de cadena 180 s → <medido>; turnos vacíos <n> → 0
         LLM_MAX_TOKENS 180 → <D1> (razonamiento <n> / respuesta <n>)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Rollback

```bash
HOLOGRAM_MODEL_POLICY=0    # temperatura y presupuesto vuelven a los valores previos
```

El presupuesto de cadena y el fast-fail **no** necesitan flag propio: son una reducción de
timeouts, y volver atrás es subir el número en configuración.

Los avisos de diagnóstico **no llevan flag**. Ese es el punto de la WAVE: si volvés a poder
apagarlos, no la hiciste.

```bash
git revert <sha>
```

---

## Handoff — volcar en `PROGRESS.md`

```markdown
### WAVE-09 — Política de modelos, presupuesto y fallback
- Commit: <sha> · Fecha: <YYYY-MM-DD>
- Archivos tocados: <...>
- Tests añadidos: tests/test_model_policy.py::<casos>
- D1 RESUELTA: LLM_MAX_TOKENS = <n> (razonamiento <n> / respuesta <n>) · por: <quién, fecha>
- D2 RESUELTA: <opción a/b/c> · modelo elegido: <nombre> · por: <quién, fecha>
- Dónde vive la política: <módulo y símbolo>
- Temperatura: default <n> · por tipo: <tabla breve>
- Timeouts: conexión <n> s · lectura <n> s · presupuesto de cadena <n> s
- Peor caso de cadena: 180 s → <n> s
- Turnos vacíos en las 11 preguntas: <n> → <n>
- Aviso de turno vacío con LLM_LOG_COT=0: <verificado, salida pegada>
- Pruebas manuales:
  1. cronómetro turno normal: <n> s
  2. sin wifi: <...>
  3. pregunta que se cortaba: <...>
  4. aviso visible con el log apagado: <...>
- Criterios de aceptación: <1–14>
- Desvíos: <...>
- Hallazgos nuevos (NO arreglados): <...>
- Revisión humana: <OK, fecha>
```

Actualizá también la tabla **Decisiones pendientes de humano**: D1 y D2 pasan de `abierta` a
`cerrada`, con el valor elegido. Es el único sitio donde queda registrado por qué el kiosco usa
el modelo que usa.

**Después: PARAR.** Queda WAVE-10, que es la red de seguridad de todo lo anterior. Si el proyecto
tuviera que detenerse acá, el sistema ya es sustancialmente mejor que en `6458e07`: responde,
responde rápido, no habla su propio razonamiento y no manda 18.000 caracteres por turno.
