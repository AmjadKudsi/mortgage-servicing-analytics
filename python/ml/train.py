"""
train.py — Train any scikit-learn model with standardized interface.
"""

import time
import logging
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

log = logging.getLogger("ml")

# Registry of available models
MODEL_REGISTRY = {
    "logistic_regression": {
        "class": LogisticRegression,
        "needs_scaling": True,
    },
    "random_forest": {
        "class": RandomForestClassifier,
        "needs_scaling": False,
    },
    "hist_gradient_boosting": {
        "class": HistGradientBoostingClassifier,
        "needs_scaling": False,
    },
}


def train_model(X_train, y_train, model_name, config):
    """
    Train a model by name using parameters from config.

    Returns:
        dict with keys: model, scaler (or None), model_name, train_time
    """
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model: {model_name}. "
                         f"Available: {list(MODEL_REGISTRY.keys())}")

    reg = MODEL_REGISTRY[model_name]
    model_class = reg["class"]
    needs_scaling = reg["needs_scaling"]

    # Get params from config, fall back to defaults
    params = dict(config.get("models", {}).get(model_name, {}))

    # Add n_jobs for tree models
    if model_name in ("random_forest",):
        params.setdefault("n_jobs", -1)

    log.info(f"  Training {model_name}...")

    # Scale if needed
    scaler = None
    X_fit = X_train
    if needs_scaling:
        scaler = StandardScaler()
        X_fit = scaler.fit_transform(X_train)

    # Train with timing
    start = time.time()
    model = model_class(**params)
    model.fit(X_fit, y_train)
    train_time = round(time.time() - start, 1)

    log.info(f"    Trained in {train_time}s")

    return {
        "model": model,
        "scaler": scaler,
        "model_name": model_name,
        "train_time": train_time,
    }
