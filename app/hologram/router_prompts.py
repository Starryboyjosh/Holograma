"""Instrucción mínima para implementaciones externas del submodelo.

El dominio no usa este texto directamente; evita que un proveedor necesite
conocer catálogo físico, IPs o comandos TCP.
"""

MEDIA_ROUTER_PROMPT = (
    "Selecciona solo IDs permitidos. Devuelve identidad, acción promocional, "
    "promoción/categoría y confianza entre 0 y 1. Nunca incluyas hardware."
)
