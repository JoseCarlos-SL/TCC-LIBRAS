# central/models.py
"""Modelo ORM da tabela 'signs' no banco de dados SQLite."""

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Sign(Base):
    """Registro de um sinal de Libras capturado pelo edge."""

    __tablename__ = "signs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
