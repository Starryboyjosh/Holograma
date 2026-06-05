#!/usr/bin/env python3
"""
UNEV Hologram — Script de Configuración Interactiva.
Inspirado en 'hermes setup'.

Este script guía al usuario para configurar su asistente local, estimando el uso de VRAM
y previniendo congelamientos por falta de memoria (especialmente optimizado para GPUs de 4GB
como la Quadro T1000). Genera un archivo config.json unificado.

Regla de Oro A: Rutas con pathlib.Path.
Regla de Oro C: Se integra con el entorno virtual y requirements.txt.
"""

import json
import os
import sys
from pathlib import Path

# Intentar importar rich, si no está instalado, dar instrucciones claras
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.table import Table
    from rich.theme import Theme
except ImportError:
    print("Error: La librería 'rich' es necesaria para ejecutar este configurador.")
    print("Por favor, asegúrate de activar el entorno virtual o instalarla usando:")
    print("  pip install rich")
    sys.exit(1)

# Configuración del tema visual estilo Hermes (Cyberpunk / Terminal Retro)
hermes_theme = Theme(
    {
        "info": "cyan bold",
        "warning": "yellow bold",
        "danger": "red bold",
        "success": "green bold",
        "accent": "magenta bold",
    }
)

console = Console(theme=hermes_theme)
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

# Constantes de consumo de VRAM en Megabytes (MB)
BRAINS_VRAM = {
    "gemma4:e4b": 3000,  # Gemma 4 E4B: ~3.0 GB
    "qwen3:8b": 4800,  # Qwen 3:8B: ~4.8 GB
}

EARS_VRAM = {
    "small": 250,  # Whisper Small INT8
    "medium": 750,  # Whisper Medium INT8
}

VISION_VRAM = 80  # YOLOv11 Nano: ~80 MB
BASE_SYSTEM_VRAM = 500  # Margen base del Sistema Operativo/Entorno Gráfico (500 MB)
VRAM_LIMIT_MB = 4000  # Límite crítico (4.0 GB - Quadro T1000)


def print_header():
    """Imprime el header estilo 'hermes setup'."""
    console.clear()
    banner = """
 ██╗   ██╗  ██╗  ███████╗ ███████╗██╗   ██╗ ██████╗  ██╗   ██╗
 ████╗████║ ██║  ██╔════╝ ██╔════╝╚██╗ ██╔╝██╔═══██╗ ██║   ██║
 ██╔███╔██║ ██║  ███████╗ ███████╗ ╚████╔╝ ██║   ██║ ██║   ██║
 ██║╚═╝ ██║ ██║  ╚════██║ ╚════██║  ╚██╔╝  ██║   ██║ ██║   ██║
 ██║    ██║ ██║  ███████║ ███████║   ██║   ╚██████╔╝ ╚██████╔╝
 ╚═╝    ╚═╝ ╚═╝  ╚══════╝ ╚══════╝   ╚═╝    ╚═════╝   ╚═════╝
           CONFIGURACIÓN ASISTENTE HOLOGRAMA UNEV
    """
    console.print(Panel(banner.strip(), style="accent", border_style="cyan"))
    console.print(
        "[info]Iniciando gestor de sentidos y cerebro para hardware local...[/info]\n"
    )


def select_brain():
    """Flujo interactivo para configurar el Cerebro (LLM)."""
    console.print(
        "\n[accent]1. CONFIGURACIÓN DEL CEREBRO (LLM local vía Ollama)[/accent]"
    )
    table = Table(show_header=True, header_style="cyan")
    table.add_column("Opción", style="bold green")
    table.add_column("Modelo", style="bold white")
    table.add_column("VRAM Estimada", style="bold yellow")
    table.add_column("Descripción")

    table.add_row(
        "1",
        "Gemma 4 E4B",
        "3.0 GB (3000 MB)",
        "Optimizado por Google, ideal para GPUs de 4GB.",
    )
    table.add_row(
        "2",
        "Qwen 3:8B",
        "4.8 GB (4800 MB)",
        "Mayor precisión conversacional, mayor consumo de memoria.",
    )

    console.print(table)

    choice = Prompt.ask("Selecciona el Cerebro", choices=["1", "2"], default="1")

    if choice == "1":
        return "gemma4:e4b", BRAINS_VRAM["gemma4:e4b"]
    else:
        return "qwen3:8b", BRAINS_VRAM["qwen3:8b"]


def select_ears():
    """Flujo interactivo para configurar los Oídos (Whisper)."""
    console.print(
        "\n[accent]2. CONFIGURACIÓN DEL OÍDO (Transcripción local Faster-Whisper)[/accent]"
    )
    table = Table(show_header=True, header_style="cyan")
    table.add_column("Opción", style="bold green")
    table.add_column("Modelo", style="bold white")
    table.add_column("VRAM Estimada (INT8)", style="bold yellow")
    table.add_column("Descripción")

    table.add_row(
        "1",
        "Small (Cuantizado INT8)",
        "250 MB",
        "Balance ideal entre velocidad y precisión.",
    )
    table.add_row(
        "2",
        "Medium (Cuantizado INT8)",
        "750 MB",
        "Máxima precisión en español, mayor huella de VRAM.",
    )

    console.print(table)

    choice = Prompt.ask("Selecciona el Oído", choices=["1", "2"], default="1")

    if choice == "1":
        return "small", EARS_VRAM["small"]
    else:
        return "medium", EARS_VRAM["medium"]


def configure_vision():
    """Flujo interactivo para la Visión (YOLOv11 + OpenCV)."""
    console.print("\n[accent]3. PARÁMETROS DE VISIÓN (YOLOv11 Nano + Cámara)[/accent]")

    activate = Confirm.ask(
        "¿Deseas activar el sentido de la visión en tiempo real (cámara)?", default=True
    )

    if not activate:
        console.print("[info]Sentido de la visión desactivado.[/info]")
        return False, None, 0, 0

    console.print(
        "[success]Visión activada con modelo predeterminado: yolo11n.pt (~80 MB VRAM)[/success]"
    )

    # Preguntar por el ratio de Frame Skipping para optimizar rendimiento
    frame_skipping = IntPrompt.ask(
        "Ratio de 'Frame Skipping' (procesar 1 de cada X fotogramas)", default=5
    )

    return True, "yolo11n.pt", frame_skipping, VISION_VRAM


def run_setup():
    """Ejecuta el asistente interactivo de configuración completo."""
    print_header()

    # 1. Configurar Cerebro
    brain_model, brain_vram = select_brain()

    # 2. Configurar Oído
    ear_model, ear_vram = select_ears()

    # 3. Configurar Visión
    vision_active, yolo_model, frame_skip, vision_vram = configure_vision()

    # 4. Cálculo de VRAM y Hardware Guard
    total_vram = brain_vram + ear_vram + vision_vram + BASE_SYSTEM_VRAM

    console.print("\n[accent]4. ANÁLISIS DE RECURSOS (Hardware Guard)[/accent]")

    # Generar tabla resumen estético en pantalla
    summary_table = Table(
        title="Proyección de Recursos de Hardware",
        show_header=True,
        header_style="cyan",
    )
    summary_table.add_column("Componente", style="bold white")
    summary_table.add_column("Configuración Seleccionada", style="bold green")
    summary_table.add_column("Consumo VRAM Proyectado", style="bold yellow")

    summary_table.add_row("Cerebro (Ollama LLM)", brain_model, f"{brain_vram} MB")
    summary_table.add_row(
        "Oído (Faster-Whisper)", f"{ear_model} (INT8)", f"{ear_vram} MB"
    )
    summary_table.add_row(
        "Visión (YOLOv11)",
        f"Activa ({yolo_model}, skip={frame_skip})" if vision_active else "Inactiva",
        f"{vision_vram} MB",
    )
    summary_table.add_row(
        "Margen Base (SO / UI)", "CachyOS / Windows GUI", f"{BASE_SYSTEM_VRAM} MB"
    )

    # Estilo especial para la fila del total
    total_color = "success" if total_vram <= VRAM_LIMIT_MB else "danger"
    summary_table.add_row(
        "[bold]CONSUMO TOTAL PROYECTADO[/bold]",
        "",
        f"[{total_color}]{total_vram} MB / {VRAM_LIMIT_MB} MB[/{total_color}]",
        end_section=True,
    )

    console.print(summary_table)

    # Validación Crítica: Límite de 4GB (Quadro T1000)
    if total_vram > VRAM_LIMIT_MB:
        warning_msg = (
            f"¡PELIGRO DE OUT-OF-MEMORY!\n\n"
            f"Tu configuración actual proyecta un consumo de {total_vram} MB de VRAM,\n"
            f"lo cual supera el límite crítico de {VRAM_LIMIT_MB} MB (4GB de tu GPU/T1000).\n"
            f"Si continúas, podrías experimentar cuelgues, lentitud severa o congelamientos del sistema."
        )
        console.print(Panel(warning_msg, style="danger", border_style="red"))

        save_anyway = Confirm.ask(
            "[warning]¿Deseas guardar la configuración de todas formas?[/warning]",
            default=False,
        )

        if not save_anyway:
            console.print(
                "[info]Reconfigurando sentidos. Reiniciando asistente...[/info]"
            )
            run_setup()
            return

    # Si todo está en rango o el usuario decidió continuar
    save_config = Confirm.ask(
        "¿Deseas escribir los cambios al archivo de configuración local config.json?",
        default=True,
    )

    if save_config:
        # Mapear los valores elegidos al formato de variables de entorno del holograma
        config_data = {
            "OLLAMA_MODEL": brain_model,
            "WHISPER_MODEL": ear_model,
            "HOLOGRAM_INPUT": "voice",
            "HOLOGRAM_CAMERA": "1" if vision_active else "0",
            "YOLO_MODEL": yolo_model if vision_active else "yolov8n.pt",
            "YOLO_INTERVAL_SECONDS": str(frame_skip / 30.0) if vision_active else "1.0",
        }

        try:
            # Escribir la configuración usando Path (Regla A)
            with CONFIG_FILE.open("w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)

            console.print(
                f"\n[success]✔ Configuración guardada con éxito en {CONFIG_FILE}[/success]"
            )

            # Dar instrucciones de cómo correr la app
            console.print(
                Panel(
                    f"Configuración aplicada. Ahora puedes iniciar el asistente con:\n\n"
                    f"  [bold]python call.py --voice --camera[/bold]\n\n"
                    f"La aplicación cargará automáticamente los valores definidos en tu config.json.",
                    title="Siguientes pasos",
                    border_style="green",
                )
            )

        except Exception as e:
            console.print(
                f"[danger]✘ Error escribiendo el archivo de configuración: {e}[/danger]"
            )
    else:
        console.print("[warning]Configuración descartada sin guardar.[/warning]")


if __name__ == "__main__":
    try:
        run_setup()
    except KeyboardInterrupt:
        console.print(
            "\n[warning]Asistente de configuración cancelado por el usuario.[/warning]"
        )
        sys.exit(0)
