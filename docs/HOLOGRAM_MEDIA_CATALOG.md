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
