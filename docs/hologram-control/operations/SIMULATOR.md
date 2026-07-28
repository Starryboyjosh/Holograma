# Simulador

Debe registrar:

```text
timestamp role ip command semantic_id resolved_index context_id result error
```

Debe soportar:

- conexión;
- desconexión;
- latencia;
- error;
- reconexión;
- captura de comandos;
- tres unidades;
- reloj virtual.

Ejemplo:

```text
00:00 top idle
00:00 center holomind
00:00 bottom promo-a
00:05 top listening
00:07 center unev
00:07 bottom careers
00:09 top speaking
00:20 top idle
00:24 center holomind
00:24 bottom promo-b
```
