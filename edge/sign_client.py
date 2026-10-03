# edge/sign_client.py
"""
Cliente HTTP para enviar letras reconhecidas a central LibrasLink.

Usado por main.py. Falhas de rede sao logadas mas nao param o loop.
"""

import logging
from datetime import datetime, timezone

import requests

from config import API_KEY, CAMERA_ID, CENTRAL_URL

logger = logging.getLogger(__name__)

_ENDPOINT = f"{CENTRAL_URL}/api/signs"
_HEADERS  = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
_TIMEOUT  = 3  # segundos


def enviar_sinal(label: str, confidence: float) -> bool:
    """
    Envia uma letra reconhecida a central via POST /api/signs.

    Parametros
    ----------
    label : str
        Letra ou 'ESPACO'.
    confidence : float
        Probabilidade da predicao (0 a 1).

    Retorno
    -------
    True se o envio foi bem-sucedido, False caso contrario.
    """
    payload = {
        "camera_id":   CAMERA_ID,
        "label":       label,
        "confidence":  round(confidence, 4),
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp = requests.post(_ENDPOINT, json=payload, headers=_HEADERS, timeout=_TIMEOUT)
        if resp.status_code == 201:
            logger.info("Sinal enviado: %s (%.2f%%)", label, confidence * 100)
            return True
        logger.warning("Central respondeu %d ao enviar '%s'.", resp.status_code, label)
        return False
    except requests.exceptions.ConnectionError:
        logger.warning("Sem conexao com a central (%s). Sinal '%s' descartado.", _ENDPOINT, label)
    except requests.exceptions.Timeout:
        logger.warning("Timeout ao enviar sinal '%s' para a central.", label)
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro inesperado ao enviar sinal: %s", exc)
    return False
