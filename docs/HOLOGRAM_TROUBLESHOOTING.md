# Troubleshooting de tres ventiladores

- **Índice incorrecto:** calibre cada unidad por separado con `scripts/diagnose_hologram.py --simulate --role center --index 0`; en hardware use además `--connect`.
- **No conecta:** confirme DHCP/IP, firewall, puerto 50200 y Third Party Control.
- **Unidad parcial caída:** top, center y bottom se aíslan; revise `last_error` y reintentos sin asumir reproducción confirmada.
- **TF/playlist desordenada:** corrija el catálogo después de registrar índice observado; no cambie el protocolo ni agregue offsets.
- **JSON corrupto:** el store usa configuración segura/backup; conserve `.bak` para inspección.
- **Rotación rara:** revise duración lógica configurada; el ventilador no informa fin de video.
- **Demo local sin token:** use `127.0.0.1` y deje `HOLOGRAM_API_TOKEN` /
  `VITE_HOLOGRAM_API_TOKEN` vacíos. Para red compartida configure ambos con el
  mismo valor y mantenga la red controlada.
- **Rotación pausada tras guardar:** el contenido actual se restaura una vez al
  nuevo manager; no debería avanzar al siguiente hasta pulsar reanudar.
