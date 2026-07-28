# Validación física

## Preparación

1. Misma red.
2. Third party control.
3. Puerto 50200.
4. Confirmar IP.
5. Identificar unidad.
6. Asignar rol.
7. Registrar índices.
8. Probar por separado.
9. Probar simultáneo.
10. Guardar evidencia.

## IP históricas

- 10.10.2.211
- 10.10.2.212
- 10.10.2.213

No asumir posición.

## Evidencia

- fecha;
- commit;
- IP/rol;
- índices;
- log;
- video;
- limitaciones.

## Contrato vigente

El software solicita índices base cero `0..255`; `0` es válido. El hardware se
trata como write-only: un envío sin excepción significa comando enviado, no
reproducción visual confirmada. La correspondencia IP/rol e índice/playlist está
pendiente de calibración física.

Para la demostración escolar, cargue tres clips de top, dos de center y tres de
bottom en playlists independientes mediante HoloMissYou. Pruebe `0`, `1` y `2`
por rol y registre el contenido observado. Si difiere, corrija
`data/hologram_media.json`; no agregue offsets globales.
