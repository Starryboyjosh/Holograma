---
id: HC-GOV-RULES
status: accepted
---

# Reglas para agentes

## Antes de modificar

1. Leer `AGENTS.md` del repositorio.
2. Leer `docs/hologram-control/INDEX.md`.
3. Leer `implementation/STATUS.md`.
4. Leer la wave activa.
5. Leer el último handoff.
6. Revisar `git status`.
7. Ejecutar baseline relevante.
8. Confirmar el código real antes de asumir.

## Restricciones duras

- La IA nunca recibe IP, puerto o índice.
- La IA nunca llama directamente `play_file`.
- Los estados de mascota son deterministas.
- Holomind es fallback central.
- La rotación inferior funciona sin LLM.
- Una unidad caída no detiene las otras.
- No duplicar lógica sync/async.
- No mezclar JSON de control con TTS o UI.
- No eliminar compatibilidad heredada sin adaptador.
- No agregar base de datos en v1.
- No hacer refactors ajenos.
- No afirmar pruebas físicas sin hardware.
- No dejar workers, tasks o timers vivos.
- No desactivar pruebas para lograr verde.

## Protocolo de inicio

Antes de editar, reportar:

- wave;
- requisitos;
- estado encontrado;
- archivos previstos;
- contratos afectados;
- pruebas;
- riesgos;
- supuestos.

## Protocolo de cierre

Entregar:

- resumen;
- archivos;
- pruebas y resultados exactos;
- diff check;
- limitaciones;
- handoff;
- estado de siguiente wave.

## Regla para modelos débiles

Cuando existan dos opciones razonables:

1. Elegir la más compatible.
2. Mantener contratos.
3. Documentar la decisión.
4. Evitar crear infraestructura nueva.

## Definition of Done

Una tarea está terminada cuando:

- cumple criterios;
- tiene pruebas;
- maneja error y vacío;
- preserva compatibilidad;
- cierra recursos;
- actualiza docs;
- deja evidencia reproducible.
