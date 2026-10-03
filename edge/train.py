# edge/train.py
"""
Treina o classificador RandomForest com os dados coletados em data/dataset.csv.

Uso:
    python train.py

Salva o modelo em models/libras_model.joblib.
Imprime acuracia e matriz de confusao.
"""

import logging
import sys
from pathlib import Path

import csv

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
MODEL_DIR  = BASE_DIR / "models"
CSV_PATH   = DATA_DIR / "dataset.csv"
MODEL_PATH = MODEL_DIR / "libras_model.joblib"


def treinar() -> None:
    """Carrega o CSV, treina o modelo e salva em disco."""

    if not CSV_PATH.exists():
        logger.error("CSV nao encontrado: %s", CSV_PATH)
        logger.error("Execute collect.py primeiro para gerar o dataset.")
        sys.exit(1)

    logger.info("Carregando dataset: %s", CSV_PATH)
    rotulos: list[str] = []
    features: list[list[float]] = []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "label" not in (reader.fieldnames or []):
            logger.error("Coluna 'label' nao encontrada no CSV.")
            sys.exit(1)
        for row in reader:
            rotulos.append(row["label"])
            features.append([float(row[f"f{i}"]) for i in range(63)])

    X = np.array(features, dtype=np.float32)
    y = np.array(rotulos)

    classes, contagem = np.unique(y, return_counts=True)
    logger.info("Classes encontradas: %s", dict(zip(classes, contagem)))
    logger.info("Total de amostras: %d | Features por amostra: %d", len(X), X.shape[1])

    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y,
        test_size=0.20,
        stratify=y,
        random_state=42,
    )
    logger.info("Treino: %d amostras | Teste: %d amostras", len(X_treino), len(X_teste))

    logger.info("Treinando RandomForestClassifier(n_estimators=200)...")
    modelo = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    modelo.fit(X_treino, y_treino)

    y_pred = modelo.predict(X_teste)
    acuracia = accuracy_score(y_teste, y_pred)
    logger.info("Acuracia no teste: %.2f%%", acuracia * 100)

    print("\n=== Relatorio de classificacao ===")
    print(classification_report(y_teste, y_pred))

    print("=== Matriz de confusao ===")
    cm = confusion_matrix(y_teste, y_pred, labels=modelo.classes_)
    header = "      " + "  ".join(f"{c:>8}" for c in modelo.classes_)
    print(header)
    for i, row in enumerate(cm):
        linha = f"{modelo.classes_[i]:>6}" + "  ".join(f"{v:>8}" for v in row)
        print(linha)
    print()

    if acuracia < 0.90:
        logger.warning(
            "Acuracia abaixo de 90%% (%.1f%%). Colete mais amostras.",
            acuracia * 100,
        )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"modelo": modelo, "classes": list(modelo.classes_)}
    joblib.dump(payload, MODEL_PATH)
    logger.info("Modelo salvo em: %s", MODEL_PATH)
    logger.info("Classes no modelo: %s", payload["classes"])


if __name__ == "__main__":
    treinar()
    sys.exit(0)
