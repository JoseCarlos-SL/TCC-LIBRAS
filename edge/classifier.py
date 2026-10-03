# edge/classifier.py
"""
Carrega o modelo treinado (.joblib) e realiza predicoes.

Este modulo e importado por main.py. Deve ser carregado apenas
apos o modelo existir (apos rodar train.py).
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "models" / "libras_model.joblib"


class Classificador:
    """Encapsula o modelo RandomForest e expoe o metodo de predicao."""

    def __init__(self, caminho: Path = MODEL_PATH) -> None:
        if not caminho.exists():
            raise FileNotFoundError(
                f"Modelo nao encontrado em '{caminho}'. Execute train.py primeiro."
            )
        payload = joblib.load(caminho)
        self._modelo = payload["modelo"]
        self.classes: list[str] = payload["classes"]
        logger.info("Modelo carregado. Classes: %s", self.classes)

    def predizer(self, vetor: np.ndarray) -> Optional[tuple[str, float]]:
        """
        Realiza a predicao para um vetor de features de shape (63,).

        Retorno
        -------
        (label, confianca) ou None se o vetor for invalido.
        """
        if vetor is None or vetor.shape != (63,):
            return None

        probas = self._modelo.predict_proba(vetor.reshape(1, -1))[0]
        idx = int(np.argmax(probas))
        return self._modelo.classes_[idx], float(probas[idx])
