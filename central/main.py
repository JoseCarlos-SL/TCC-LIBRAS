# central/main.py
"""Aplicação FastAPI do módulo central do LibrasLink."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
from config import API_KEY, HOST, PORT
from database import Base, engine, get_db
from ws_manager import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Cria as tabelas no banco ao iniciar a aplicação."""
    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados inicializado.")
    yield


app = FastAPI(title="LibrasLink Central", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Autenticação por API key
# ---------------------------------------------------------------------------

def verificar_api_key(x_api_key: str = Header(...)) -> None:
    """Valida o header X-API-Key em todos os endpoints protegidos."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida.")


# ---------------------------------------------------------------------------
# Endpoints da API
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
def health() -> dict:
    """Verifica se o serviço está no ar."""
    return {"status": "ok"}


@app.post(
    "/api/signs",
    status_code=201,
    response_model=schemas.SignCreatedResponse,
    tags=["sinais"],
    dependencies=[Depends(verificar_api_key)],
)
async def criar_sinal(
    payload: schemas.SignCreate,
    db: Session = Depends(get_db),
) -> schemas.SignCreatedResponse:
    """Recebe um sinal do edge, salva no banco e transmite via WebSocket."""
    sinal = models.Sign(
        camera_id=payload.camera_id,
        label=payload.label,
        confidence=payload.confidence,
        detected_at=payload.detected_at,
    )
    db.add(sinal)
    db.commit()
    db.refresh(sinal)
    logger.info("Sinal recebido: %s (%.2f) de %s", sinal.label, sinal.confidence, sinal.camera_id)

    await manager.broadcast({
        "type": "new_sign",
        "data": schemas.SignResponse.model_validate(sinal).model_dump(mode="json"),
    })
    return schemas.SignCreatedResponse(id=sinal.id)


@app.get(
    "/api/signs",
    response_model=list[schemas.SignResponse],
    tags=["sinais"],
    dependencies=[Depends(verificar_api_key)],
)
def listar_sinais(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[models.Sign]:
    """Retorna os sinais mais recentes primeiro."""
    return (
        db.query(models.Sign)
        .order_by(models.Sign.id.desc())
        .limit(limit)
        .all()
    )


@app.get(
    "/api/signs/latest",
    response_model=schemas.SignResponse,
    tags=["sinais"],
    dependencies=[Depends(verificar_api_key)],
)
def ultimo_sinal(db: Session = Depends(get_db)) -> models.Sign:
    """Retorna o último sinal registrado ou 404 se vazio."""
    sinal = db.query(models.Sign).order_by(models.Sign.id.desc()).first()
    if sinal is None:
        raise HTTPException(status_code=404, detail="Nenhum sinal registrado.")
    return sinal


@app.delete(
    "/api/signs",
    status_code=204,
    tags=["sinais"],
    dependencies=[Depends(verificar_api_key)],
)
async def apagar_sinais(db: Session = Depends(get_db)) -> Response:
    """Apaga todos os sinais do banco e notifica via WebSocket."""
    deletados = db.query(models.Sign).delete()
    db.commit()
    logger.info("Todos os sinais apagados (%d registros).", deletados)
    await manager.broadcast({"type": "cleared"})
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/signs")
async def websocket_signs(websocket: WebSocket) -> None:
    """Endpoint WebSocket para o dashboard receber eventos em tempo real."""
    await manager.connect(websocket)
    try:
        while True:
            # Mantém a conexão viva; cliente pode enviar mensagens mas ignoramos
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Arquivos estáticos (dashboard)
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve a página principal do dashboard."""
    return FileResponse("static/index.html")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
