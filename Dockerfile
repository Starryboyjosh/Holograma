# ============================================================
# Holograma UNEV — imagen del backend FastAPI
#
# Solo se usa con el perfil "full" de docker-compose.yml. El despliegue de
# kiosko corre en el host, donde cámara, micrófono, Piper y GPU son directos.
# ============================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias de sistema: OpenCV necesita libGL/libglib; sounddevice, PortAudio.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libportaudio2 \
        && rm -rf /var/lib/apt/lists/*

# Capa de dependencias separada del código: cambiar un .py no reinstala todo.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
