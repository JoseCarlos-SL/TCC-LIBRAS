# edge/main.py
"""
Loop principal de reconhecimento de Libras em tempo real.

Uso:
    python main.py

Le frames da camera, extrai features, classifica e envia letras
confirmadas a central via HTTP.
"""

import logging
import sys

import cv2

from camera import Camera
from classifier import Classificador
from config import (
    CAMERA_SOURCE,
    CONSECUTIVE_FRAMES,
    FRAME_WIDTH,
    MIN_CONFIDENCE,
    PROCESS_EVERY_N_FRAMES,
    RELEASE_FRAMES,
    SHOW_PREVIEW,
)
from hand_features import desenhar_landmarks, extrair_features, obter_resultado_mediapipe
from sign_client import enviar_sinal

# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de exibicao (preview)
# ---------------------------------------------------------------------------
FONT        = cv2.FONT_HERSHEY_SIMPLEX
COR_VERDE   = (0, 220, 100)
COR_AMARELO = (0, 210, 255)
COR_CINZA   = (120, 120, 120)
COR_BRANCO  = (240, 240, 240)


def _desenhar_hud(
    frame,
    label_previsto: str,
    confianca: float,
    frames_consec: int,
    bloqueado: bool,
) -> None:
    """Exibe informacoes de debug no frame de preview."""
    cor = COR_VERDE if confianca >= MIN_CONFIDENCE else COR_AMARELO

    cv2.putText(frame, f"Letra: {label_previsto}", (10, 30), FONT, 0.9, cor, 2)
    cv2.putText(frame, f"Conf: {confianca:.0%}", (10, 60), FONT, 0.65, cor, 1)
    cv2.putText(frame, f"Consec: {frames_consec}/{CONSECUTIVE_FRAMES}", (10, 85), FONT, 0.55, COR_CINZA, 1)

    if bloqueado:
        cv2.putText(frame, "AGUARDANDO LIBERACAO", (10, 110), FONT, 0.50, COR_AMARELO, 1)

    cv2.putText(frame, "Pressione 'q' para sair", (10, frame.shape[0] - 10), FONT, 0.45, COR_CINZA, 1)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def executar() -> None:
    """Inicia o loop de reconhecimento em tempo real."""

    logger.info("Carregando modelo...")
    clf = Classificador()

    cam    = Camera(source=CAMERA_SOURCE, frame_width=FRAME_WIDTH)
    frame_n = 0  # contador de frames brutos

    # --- Estado do reconhecimento ---
    label_atual:    str   = ""   # classe que esta sendo acumulada
    frames_consec:  int   = 0    # frames consecutivos com mesma classe
    bloqueado:      bool  = False  # anti-repeticao ativo
    frames_release: int   = 0    # contador de frames sem a letra bloqueada

    logger.info("Iniciando reconhecimento. SHOW_PREVIEW=%s", SHOW_PREVIEW)

    with cam:
        for frame in cam.gerar_frames():
            frame_n += 1

            # Processa apenas 1 a cada N frames
            if frame_n % PROCESS_EVERY_N_FRAMES != 0:
                if SHOW_PREVIEW:
                    cv2.imshow("LibrasLink -- Reconhecimento", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                continue

            # --- Extrair features ---
            resultado = obter_resultado_mediapipe(frame)
            vetor     = extrair_features(frame)

            label_previsto = ""
            confianca      = 0.0

            if vetor is not None:
                pred = clf.predizer(vetor)
                if pred is not None:
                    label_previsto, confianca = pred

            # --- Logica de estabilidade ---
            if label_previsto and label_previsto != "NENHUM" and confianca >= MIN_CONFIDENCE:

                if label_previsto == label_atual:
                    frames_consec += 1
                else:
                    label_atual   = label_previsto
                    frames_consec = 1

                # Gerencia liberacao do anti-repeticao
                if bloqueado:
                    if label_previsto != label_atual or vetor is None:
                        frames_release += 1
                        if frames_release >= RELEASE_FRAMES:
                            bloqueado      = False
                            frames_release = 0
                            logger.info("Liberado para nova letra.")
                    else:
                        frames_release = 0

                # Confirma e envia a letra
                if frames_consec >= CONSECUTIVE_FRAMES and not bloqueado:
                    logger.info(
                        "Letra confirmada: %s (%.2f%%)", label_atual, confianca * 100
                    )
                    enviar_sinal(label_atual, confianca)
                    bloqueado      = True
                    frames_release = 0
                    frames_consec  = 0

            else:
                # Sem mao ou confianca baixa: contabiliza frames de release
                if bloqueado:
                    frames_release += 1
                    if frames_release >= RELEASE_FRAMES:
                        bloqueado      = False
                        frames_release = 0
                        logger.info("Liberado (sem mao/confianca).")
                else:
                    label_atual   = ""
                    frames_consec = 0

            # --- Preview ---
            if SHOW_PREVIEW:
                frame_vis = desenhar_landmarks(frame.copy(), resultado)
                _desenhar_hud(frame_vis, label_previsto, confianca, frames_consec, bloqueado)
                cv2.imshow("LibrasLink -- Reconhecimento", frame_vis)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    logger.info("Encerrado pelo usuario.")
                    break

    cv2.destroyAllWindows()
    logger.info("Loop encerrado.")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    executar()
    sys.exit(0)
