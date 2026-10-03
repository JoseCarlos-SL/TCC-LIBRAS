# central/config.py
"""Carrega e expõe as configurações do módulo central a partir do .env."""

from dotenv import load_dotenv
import os

load_dotenv()

API_KEY: str = os.getenv("API_KEY", "troque-esta-chave")
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
DATABASE_URL: str = "sqlite:///./data/signs.db"
