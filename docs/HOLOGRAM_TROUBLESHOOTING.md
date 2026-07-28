# Troubleshooting de tres ventiladores

- **Índice incorrecto:** calibre cada unidad por separado con `scripts/diagnose_hologram.py --simulate --role center --index 0`; en hardware use además `--connect`.
- **No conecta:** confirme DHCP/IP, firewall, puerto 50200 y Third Party Control.
- **Unidad parcial caída:** top, center y bottom se aíslan; revise `last_error` y reintentos sin asumir reproducción confirmada.
- **TF/playlist desordenada:** corrija el catálogo después de registrar índice observado; no cambie el protocolo ni agregue offsets.
- **JSON corrupto:** el store usa configuración segura/backup; conserve `.bak` para inspección.
- **Rotación rara:** revise duración lógica configurada; el ventilador no informa fin de video.
