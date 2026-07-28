# Catálogo multimedia del holograma

El catálogo JSON asocia IDs semánticos con índices físicos por unidad. Ejemplo:

```text
top: idle=0, listening=1, thinking=2, speaking=3
center: holomind=0, unev=1, itee=2
bottom: general=0, careers=1, admissions=2, scholarships=3
```

Es un ejemplo lógico; no hardcodea IP ni afirma qué archivo físico ocupa cada
posición. La duración de una promoción es lógica y guía la rotación: el hardware
es write-only y no confirma el fin ni la reproducción visual.

Para la demostración mínima puede usar `top: 0,1,2,2`,
`center: holomind=0, unev=0, itee=1` y `bottom: 0,1,2`, con promociones de diez
segundos. El catálogo real vive en `data/hologram_media.json`; Settings guarda
unidades, identidades y promociones, mientras que `mascot_states` se ajusta
manualmente hasta que exista su editor.
