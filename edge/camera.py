# edge/camera.py
"""Abre o stream de vídeo (webcam, ESP32-CAM ou IP Webcam) e devolve frames."""

import logging
import time
from typing import Generator

import cv2
import numpy as np

from config import CAMERA_SOURCE, FRAME_WIDTH

logger = logging.getLogger(__name__)


class Camera:
    """
    Encapsula a captura de vídeo via OpenCV.

    Suporta:
    - Webcam USB: ``CAMERA_SOURCE = 0`` (inteiro)
    - ESP32-CAM:  ``CAMERA_SOURCE = "http://<IP>:81/stream"``
    - IP Webcam:  ``CAMERA_SOURCE = "http://<IP>:8080/video"``

    Em caso de falha, tenta reconectar automaticamente a cada ``retry_delay``
    segundos, indefinidamente, sem derrubar o processo.
    """

    def __init__(
        self,
        source: str | int = CAMERA_SOURCE,
        frame_width: int = FRAME_WIDTH,
        retry_delay: float = 3.0,
    ) -> None:
        self.source = source
        self.frame_width = frame_width
        self.retry_delay = retry_delay
        self._cap: cv2.VideoCapture | None = None

    # ------------------------------------------------------------------
    # Abertura / reconexão
    # ------------------------------------------------------------------

    def _abrir(self) -> bool:
        """Tenta abrir a captura. Retorna True se bem-sucedida."""
        if self._cap is not None:
            self._cap.release()
        logger.info("Abrindo câmera: %s", self.source)
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            logger.warning("Falha ao abrir câmera: %s", self.source)
            self._cap = None
            return False
        logger.info("Câmera aberta com sucesso.")
        return True

    def _reconectar(self) -> None:
        """Fica tentando reconectar até conseguir."""
        while not self._abrir():
            logger.warning("Reconectando em %.0f s…", self.retry_delay)
            time.sleep(self.retry_delay)

    # ------------------------------------------------------------------
    # Leitura de frames
    # ------------------------------------------------------------------

    def ler_frame(self) -> np.ndarray | None:
        """
        Lê um único frame da câmera.

        Retorna o frame BGR redimensionado, ou ``None`` se a câmera
        ainda não estiver aberta (não bloqueia).
        """
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            logger.warning("Frame inválido recebido. Câmera pode ter caído.")
            self._cap = None
            return None
        return self._redimensionar(frame)

    def _redimensionar(self, frame: np.ndarray) -> np.ndarray:
        """Redimensiona mantendo proporção se FRAME_WIDTH > 0."""
        if self.frame_width <= 0:
            return frame
        h, w = frame.shape[:2]
        if w == self.frame_width:
            return frame
        escala = self.frame_width / w
        nova_h = int(h * escala)
        return cv2.resize(frame, (self.frame_width, nova_h), interpolation=cv2.INTER_AREA)

    # ------------------------------------------------------------------
    # Gerador contínuo (usado por main.py e collect.py)
    # ------------------------------------------------------------------

    def gerar_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Gerador infinito de frames.

        Reconecta automaticamente ao detectar falha na câmera.
        Termine o laço externo para parar.
        """
        self._reconectar()
        while True:
            frame = self.ler_frame()
            if frame is None:
                logger.warning("Câmera perdida. Reconectando…")
                self._reconectar()
                continue
            yield frame

    # ------------------------------------------------------------------
    # Contexto
    # ------------------------------------------------------------------

    def liberar(self) -> None:
        """Libera os recursos da câmera."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Câmera liberada.")

    def __enter__(self) -> "Camera":
        self._reconectar()
        return self

    def __exit__(self, *_) -> None:
        self.liberar()


# ------------------------------------------------------------------
# Script de teste rápido (python camera.py)
# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Iniciando teste de câmera. Pressione 'q' para sair.")

    cam = Camera()
    with cam:
        for frame in cam.gerar_frames():
            cv2.imshow("LibrasLink — Teste de câmera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    logger.info("Teste encerrado.")
    sys.exit(0)
