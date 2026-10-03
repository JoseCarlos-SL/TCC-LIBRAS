#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# libraslink/continuar.py
"""
Script de retomada do LibrasLink.
Execute com: python continuar.py
Mostra o estado atual do projeto e o próximo passo a executar.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Definição das fases e seus arquivos de verificação
# ---------------------------------------------------------------------------
FASES = [
    {
        "num": 1,
        "nome": "Central - banco + endpoints + WebSocket",
        "arquivos": [
            "central/main.py",
            "central/database.py",
            "central/models.py",
            "central/schemas.py",
            "central/ws_manager.py",
            "central/config.py",
            "central/requirements.txt",
        ],
        "como_testar": (
            "cd central\n"
            "pip install -r requirements.txt\n"
            "python -m uvicorn main:app --reload\n"
            "# Em outro terminal:\n"
            "curl -X POST http://localhost:8000/api/signs "
            "-H 'X-API-Key: troque-esta-chave' "
            "-H 'Content-Type: application/json' "
            "-d '{\"camera_id\":\"cam-01\",\"label\":\"A\","
            "\"confidence\":0.9,\"detected_at\":\"2026-01-01T00:00:00Z\"}'"
        ),
    },
    {
        "num": 2,
        "nome": "Dashboard (HTML/CSS/JS)",
        "arquivos": [
            "central/static/index.html",
            "central/static/style.css",
            "central/static/app.js",
        ],
        "como_testar": (
            "# Com o servidor da Fase 1 rodando:\n"
            "Abra http://localhost:8000 no navegador.\n"
            "Envie um POST /api/signs e veja a letra aparecer em tempo real."
        ),
    },
    {
        "num": 3,
        "nome": "Edge - camera.py + hand_features.py",
        "arquivos": [
            "edge/camera.py",
            "edge/hand_features.py",
            "edge/config.py",
            "edge/requirements.txt",
        ],
        "como_testar": (
            "cd edge\n"
            "pip install -r requirements.txt\n"
            "python hand_features.py\n"
            "# Uma janela abrirá mostrando os landmarks da mão.\n"
            "# No terminal, o vetor de 63 valores será impresso."
        ),
    },
    {
        "num": 4,
        "nome": "Coleta de dados (collect.py)",
        "arquivos": [
            "edge/collect.py",
        ],
        "como_testar": (
            "cd edge\n"
            "python collect.py\n"
            "# Pressione a tecla da letra enquanto faz o sinal.\n"
            "# Meta: >= 300 amostras por classe.\n"
            "# Verifique: edge/data/dataset.csv"
        ),
    },
    {
        "num": 5,
        "nome": "Treino do modelo (train.py)",
        "arquivos": [
            "edge/train.py",
            "edge/models/libras_model.joblib",
        ],
        "como_testar": (
            "cd edge\n"
            "python train.py\n"
            "# Acurácia deve ser >= 90%.\n"
            "# Modelo salvo em edge/models/libras_model.joblib"
        ),
    },
    {
        "num": 6,
        "nome": "Reconhecimento em tempo real (main.py - sem envio)",
        "arquivos": [
            "edge/main.py",
            "edge/classifier.py",
            "edge/models/libras_model.joblib",
        ],
        "como_testar": (
            "cd edge\n"
            "python main.py\n"
            "# SHOW_PREVIEW=true mostra a janela com a letra predita.\n"
            "# Verifique estabilidade e anti-repetição."
        ),
    },
    {
        "num": 7,
        "nome": "Integração Edge -> Central",
        "arquivos": [
            "edge/sign_client.py",
        ],
        "como_testar": (
            "# Terminal 1:\n"
            "cd central && python -m uvicorn main:app --reload\n"
            "# Terminal 2:\n"
            "cd edge && python main.py\n"
            "# Sinalize letras e veja o texto aparecer no dashboard."
        ),
    },
    {
        "num": 8,
        "nome": "ESP32-CAM via Wi-Fi",
        "arquivos": [
            "firmware/README.md",
        ],
        "como_testar": (
            "# Altere CAMERA_SOURCE no edge/.env para http://<IP_ESP32>:81/stream\n"
            "# python main.py\n"
            "# Verifique o mesmo fluxo via Wi-Fi."
        ),
    },
    {
        "num": 10,
        "nome": "README + roteiro de demo",
        "arquivos": [
            "README.md",
        ],
        "como_testar": (
            "# Peça para outra pessoa seguir apenas o README e conseguir rodar."
        ),
    },
]

# ---------------------------------------------------------------------------
# Verificação
# ---------------------------------------------------------------------------

VERDE    = ""
AMARELO  = ""
VERMELHO = ""
RESET    = ""
NEGRITO  = ""


def checar_fase(fase: dict) -> tuple[bool, list[str]]:
    """Retorna (completa, arquivos_faltando)."""
    faltando = []
    for arq in fase["arquivos"]:
        if not (ROOT / arq).exists():
            faltando.append(arq)
    return (len(faltando) == 0, faltando)


def main() -> None:
    print(f"\n{NEGRITO}=== LibrasLink - Estado do Projeto ==={RESET}\n")

    primeira_incompleta = None

    for fase in FASES:
        completa, faltando = checar_fase(fase)
        icone = "[OK]" if completa else "[--]"
        print(f"  {icone}  Fase {fase['num']:>2}: {fase['nome']}")
        if not completa:
            for arq in faltando:
                print(f"           >> faltando: {arq}")
            if primeira_incompleta is None:
                primeira_incompleta = fase

    print()

    if primeira_incompleta is None:
        print("Projeto completo! Todos os arquivos foram criados.\n")
        return

    fase = primeira_incompleta
    print(f"--- Proximo passo: Fase {fase['num']} - {fase['nome']} ---")
    print()
    print("Como testar:")
    for linha in fase["como_testar"].split("\n"):
        print(f"  {linha}")
    print()
    print("Diga ao assistente:")
    print(f'  "comece a parte {fase["num"]}"')
    print()


if __name__ == "__main__":
    main()
