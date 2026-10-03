# central/database.py
"""Configuração do SQLAlchemy e criação da sessão do banco de dados."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import DATABASE_URL

# Garante que o diretório data/ existe
os.makedirs("data", exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # necessário para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe base para os modelos ORM."""
    pass


def get_db():
    """Dependency do FastAPI para fornecer uma sessão de banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
