# edge/collect.py
"""
Coleta de dados para treino do classificador de Libras.

Uso:
    python collect.py

Enquanto uma tecla mapeada a uma classe estiver pressionada, grava uma
linha no CSV: ``label,f0,f1,...,f62``.

Tecla ESC encerra. Consulte a legenda na janela de preview.
"""

import csv
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from camera import Camera
from config import CAMERA_SOURCE, CLASSES, FRAME_WIDTH
from hand_features import desenhar_landmarks, extrair_features, obter_resultado_mediapipe

# ---------------------------------------------------------------------------
# Configuracao de log
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento tecla -> classe
# ---------------------------------------------------------------------------

def _construir_mapeamento(classes: list[str]) -> dict[int, str]:
    """
    Gera automaticamente o mapeamento tecla -> classe com base em CLASSES.

    Regras:
    - Letras do alfabeto (A-Z): tecla = letra minuscula (ord).
    - ESPACO -> tecla 'p'.
    - NENHUM -> tecla 'n'.
    """
    mapa: dict[int, str] = {}
    for cls in classes:
        if cls == "ESPACO":
            mapa[ord("p")] = cls
        elif cls == "NENHUM":
            mapa[ord("n")] = cls
        elif len(cls) == 1 and cls.isalpha():
            mapa[ord(cls.lower())] = cls
        else:
            logger.warning("Classe '%s' sem tecla mapeada -- ignorada.", cls)
    return mapa


TECLA_CLASSE: dict[int, str] = _construir_mapeamento(CLASSES)

# ---------------------------------------------------------------------------
# Caminho do CSV de saida
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
CSV_PATH = DATA_DIR / "dataset.csv"
CSV_HEADER = ["label"] + [f"f{i}" for i in range(63)]

# ---------------------------------------------------------------------------
# Constantes de exibicao
# ---------------------------------------------------------------------------
FONT = cv2.FONT_HERSHEY_SIMPLEX
COR_VERDE = (0, 220, 100)
COR_AMARELO = (0, 210, 255)
COR_VERMELHO = (0, 60, 220)
COR_BRANCO = (240, 240, 240)
COR_CINZA = (120, 120, 120)

# Taxa maxima de gravacao (samples/s)
_SAMPLE_INTERVAL = 0.05  # ~20 amostras/s quando tecla pressionada


# ---------------------------------------------------------------------------
# Funcoes auxiliares de desenho
# ---------------------------------------------------------------------------

def _legenda(frame: np.ndarray, mapa: dict[int, str], contagem: Counter) -> np.ndarray:
    """Desenha a legenda de teclas e o contador de amostras no frame."""
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (w - 200, 0), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    y = 20
    cv2.putText(frame, "TECLA  CLASSE  N", (w - 195, y), FONT, 0.42, COR_CINZA, 1)
    y += 18
    cv2.line(frame, (w - 200, y), (w, y), COR_CINZA, 1)
    y += 12

    for codigo, cls in sorted(mapa.items(), key=lambda x: x[1]):
        tecla_str = chr(codigo).upper()
        n = contagem.get(cls, 0)
        cor = COR_VERDE if n >= 300 else (COR_AMARELO if n >= 150 else COR_BRANCO)
        texto = f"  [{tecla_str}]  {cls:<8} {n}"
        cv2.putText(frame, texto, (w - 195, y), FONT, 0.40, cor, 1)
        y += 16
        if y > h - 20:
            break

    cv2.putText(frame, "[ESC] Sair", (w - 195, h - 10), FONT, 0.38, COR_VERMELHO, 1)
    return frame


def _hud_gravando(frame: np.ndarray, label: str, total: int) -> np.ndarray:
    """Exibe indicador vermelho de gravacao e a classe ativa."""
    cv2.circle(frame, (18, 18), 10, COR_VERMELHO, -1)
    cv2.putText(frame, f"REC  {label}  (total: {total})", (34, 24),
                FONT, 0.55, COR_VERMELHO, 2)
    return frame


def _hud_standby(frame: np.ndarray, mao_detectada: bool) -> np.ndarray:
    """Exibe texto de instrucao quando nenhuma tecla esta pressionada."""
    msg = "Mao detectada -- pressione uma tecla para gravar" if mao_detectada \
        else "Aguardando mao..."
    cv2.putText(frame, msg, (10, 28), FONT, 0.50,
                COR_VERDE if mao_detectada else COR_CINZA, 1)
    return frame


# ---------------------------------------------------------------------------
# Coleta principal
# ---------------------------------------------------------------------------

def coletar() -> None:
    """Loop principal de coleta de dados."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    contagem: Counter = Counter()
    modo_append = CSV_PATH.exists()

    if modo_append:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                contagem[row["label"]] += 1
        logger.info("CSV existente carregado. Amostras por classe: %s", dict(contagem))
    else:
        logger.info("Novo dataset. Criando %s", CSV_PATH)

    csv_file = open(CSV_PATH, "a", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)

    if not modo_append:
        writer.writerow(CSV_HEADER)

    cam = Camera(source=CAMERA_SOURCE, frame_width=FRAME_WIDTH)
    logger.info("Iniciando coleta. Teclas: %s",
                {chr(k): v for k, v in TECLA_CLASSE.items()})

    ultimo_sample = 0.0
    total_sessao = 0

    try:
        with cam:
            for frame in cam.gerar_frames():
                resultado = obter_resultado_mediapipe(frame)
                frame_vis = desenhar_landmarks(frame.copy(), resultado)
                mao_detectada = bool(resultado.multi_hand_landmarks)

                tecla = cv2.waitKey(1) & 0xFF

                if tecla == 27:  # ESC
                    logger.info("ESC pressionado. Encerrando coleta.")
                    break

                gravando = tecla in TECLA_CLASSE

                if gravando and mao_detectada:
                    label = TECLA_CLASSE[tecla]
                    agora = time.monotonic()

                    if agora - ultimo_sample >= _SAMPLE_INTERVAL:
                        vetor = extrair_features(frame)
                        if vetor is not None:
                            writer.writerow([label] + vetor.tolist())
                            csv_file.flush()
                            contagem[label] += 1
                            total_sessao += 1
                            ultimo_sample = agora

                    frame_vis = _hud_gravando(frame_vis, label, contagem[label])
                else:
                    frame_vis = _hud_standby(frame_vis, mao_detectada)

                frame_vis = _legenda(frame_vis, TECLA_CLASSE, contagem)
                cv2.imshow("LibrasLink -- Coleta de dados", frame_vis)

    finally:
        csv_file.close()
        cv2.destroyAllWindows()

    logger.info(
        "Coleta encerrada. Amostras nesta sessao: %d | Total no CSV: %d",
        total_sessao, sum(contagem.values()),
    )
    logger.info("Amostras por classe: %s", dict(contagem))

    for cls in CLASSES:
        n = contagem.get(cls, 0)
        if n < 300:
            logger.warning("Classe '%s' tem apenas %d amostras (meta: 300).", cls, n)


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    coletar()
    sys.exit(0)
