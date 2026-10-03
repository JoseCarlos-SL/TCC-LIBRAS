# central/schemas.py
"""Esquemas Pydantic para validação de entrada e saída da API."""

from datetime import datetime
from pydantic import BaseModel


class SignCreate(BaseModel):
    """Corpo da requisição POST /api/signs enviado pelo edge."""

    camera_id: str
    label: str
    confidence: float
    detected_at: datetime


class SignResponse(BaseModel):
    """Representação de um sinal retornado pela API."""

    id: int
    camera_id: str
    label: str
    confidence: float
    detected_at: datetime

    model_config = {"from_attributes": True}


class SignCreatedResponse(BaseModel):
    """Resposta mínima ao criar um sinal (apenas o id)."""

    id: int
