# edge/hand_features.py
"""
Detecção de mão com MediaPipe e extração do vetor de 63 features normalizado.

Este módulo é a ÚNICA fonte de normalização do projeto. Deve ser importado
por collect.py, train.py e main.py — nunca reimplementado em outro lugar.
"""

import logging
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Inicialização do MediaPipe Hands (API clássica)
# ---------------------------------------------------------------------------
_mp_hands = mp.solutions.hands
_mp_draw = mp.solutions.drawing_utils
_mp_draw_styles = mp.solutions.drawing_styles

# Instância reutilizável (criada uma vez para economizar recursos)
_hands = _mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)

# Número de landmarks por mão × coordenadas (x, y, z)
N_LANDMARKS = 21
N_FEATURES = N_LANDMARKS * 3  # 63


# ---------------------------------------------------------------------------
# Função principal de extração
# ---------------------------------------------------------------------------

def extrair_features(frame_bgr: np.ndarray) -> Optional[np.ndarray]:
    """
    Detecta a mão direita no frame e retorna o vetor normalizado de 63 features.

    Parâmetros
    ----------
    frame_bgr : np.ndarray
        Frame BGR capturado pela câmera (formato OpenCV).

    Retorno
    -------
    np.ndarray de shape (63,) com dtype float32 se uma mão for detectada,
    ou ``None`` se nenhuma mão estiver visível.

    Normalização
    ------------
    1. Converte BGR → RGB e processa com MediaPipe Hands.
    2. Coleta os 21 landmarks (x, y, z) → array (21, 3).
    3. Subtrai o landmark 0 (pulso) de todos os pontos.
    4. Divide pelo maior valor absoluto de distância euclidiana pulso→ponto.
    5. Achata para vetor de 63 valores.
    """
    # Converte BGR → RGB (MediaPipe espera RGB)
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # Marca como não-gravável para melhorar performance
    frame_rgb.flags.writeable = False
    resultado = _hands.process(frame_rgb)
    frame_rgb.flags.writeable = True

    if not resultado.multi_hand_landmarks:
        return None

    # Pega apenas a primeira mão detectada (max_num_hands=1 garante no máximo 1)
    landmarks = resultado.multi_hand_landmarks[0]

    # Converte para array numpy (21, 3)
    pontos = np.array(
        [[lm.x, lm.y, lm.z] for lm in landmarks.landmark],
        dtype=np.float32,
    )

    # --- Normalização ---
    # 1. Centraliza no pulso (landmark 0)
    pulso = pontos[0].copy()
    pontos -= pulso

    # 2. Escala pela maior distância euclidiana (pulso → qualquer ponto)
    distancias = np.linalg.norm(pontos, axis=1)  # shape (21,)
    max_dist = distancias.max()

    if max_dist < 1e-6:
        # Mão colapsada / muito próxima — descarta
        logger.debug("Distância máxima quase zero; frame descartado.")
        return None

    pontos /= max_dist

    return pontos.flatten()  # shape (63,)


def obter_resultado_mediapipe(frame_bgr: np.ndarray):
    """
    Retorna o objeto de resultado bruto do MediaPipe para um frame.

    Usado por collect.py e main.py para desenhar landmarks na janela de preview.
    Não normaliza — use ``extrair_features`` para obter o vetor de treino/inferência.
    """
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    frame_rgb.flags.writeable = False
    resultado = _hands.process(frame_rgb)
    frame_rgb.flags.writeable = True
    return resultado


def desenhar_landmarks(frame_bgr: np.ndarray, resultado) -> np.ndarray:
    """
    Desenha os landmarks e conexões da mão sobre o frame (in-place).

    Parâmetros
    ----------
    frame_bgr : np.ndarray
        Frame original em BGR (modificado in-place).
    resultado : mp.solutions.hands.Hands result
        Objeto retornado por ``obter_resultado_mediapipe``.

    Retorno
    -------
    O mesmo frame com os landmarks desenhados.
    """
    if resultado.multi_hand_landmarks:
        for hand_lm in resultado.multi_hand_landmarks:
            _mp_draw.draw_landmarks(
                frame_bgr,
                hand_lm,
                _mp_hands.HAND_CONNECTIONS,
                _mp_draw_styles.get_default_hand_landmarks_style(),
                _mp_draw_styles.get_default_hand_connections_style(),
            )
    return frame_bgr


# ---------------------------------------------------------------------------
# Script de teste rápido (python hand_features.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from camera import Camera

    logger.info("Iniciando teste de features. Pressione 'q' para sair.")
    cam = Camera()

    with cam:
        for frame in cam.gerar_frames():
            resultado = obter_resultado_mediapipe(frame)
            frame_vis = desenhar_landmarks(frame.copy(), resultado)

            vetor = extrair_features(frame)

            if vetor is not None:
                logger.info(
                    "Mão detectada! Vetor de %d features | min=%.3f max=%.3f",
                    len(vetor), vetor.min(), vetor.max(),
                )
                # Exibe os primeiros 9 valores (3 landmarks × 3 coords)
                print("Primeiros 9 valores:", vetor[:9].round(4))
            else:
                cv2.putText(
                    frame_vis, "Sem mao detectada", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2,
                )

            cv2.imshow("LibrasLink — hand_features.py", frame_vis)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    logger.info("Teste encerrado.")
    sys.exit(0)
