# edge/config.py
"""Carrega e expõe as configurações do módulo edge a partir do .env."""

import os
from dotenv import load_dotenv

load_dotenv()

# Identificador desta câmera enviado à central
CAMERA_ID: str = os.getenv("CAMERA_ID", "cam-01")

# Fonte de vídeo: URL HTTP (ESP32/celular) ou inteiro (webcam USB)
_src = os.getenv("CAMERA_SOURCE", "0")
CAMERA_SOURCE: str | int = int(_src) if _src.strip().lstrip("-").isdigit() else _src

# URL base da central (sem barra final)
CENTRAL_URL: str = os.getenv("CENTRAL_URL", "http://127.0.0.1:8000").rstrip("/")

# Chave de API da central
API_KEY: str = os.getenv("API_KEY", "troque-esta-chave")

# Limiar mínimo de confiança para aceitar uma predição
MIN_CONFIDENCE: float = float(os.getenv("MIN_CONFIDENCE", "0.80"))

# Número de frames consecutivos com mesma classe para confirmar uma letra
CONSECUTIVE_FRAMES: int = int(os.getenv("CONSECUTIVE_FRAMES", "8"))

# Frames sem a letra (ou com outra) necessários para liberar o anti-repetição
RELEASE_FRAMES: int = int(os.getenv("RELEASE_FRAMES", "5"))

# Processa 1 a cada N frames (alivia CPU)
PROCESS_EVERY_N_FRAMES: int = int(os.getenv("PROCESS_EVERY_N_FRAMES", "2"))

# Largura alvo para redimensionar o frame antes de processar
FRAME_WIDTH: int = int(os.getenv("FRAME_WIDTH", "640"))

# Exibe janela de preview (requer display)
SHOW_PREVIEW: bool = os.getenv("SHOW_PREVIEW", "true").lower() == "true"

# Classes reconhecidas (ajuste conforme o dataset coletado)
CLASSES: list[str] = [
    "A", "B", "C", "E", "I", "L", "O", "U", "V", "ESPACO", "NENHUM"
]
