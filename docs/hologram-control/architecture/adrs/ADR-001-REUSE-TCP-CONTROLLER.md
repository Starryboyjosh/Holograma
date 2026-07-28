# ADR-001 — Reutilizar el controlador TCP

## Estado

Aceptado.

## Decisión

Mantener `HologramFanController` como transporte.

## Razón

Ya implementa el protocolo probado y evita reintroducir errores físicos.

## Consecuencia

La nueva lógica se construye encima mediante UnitManager y Director.
