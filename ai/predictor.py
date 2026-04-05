"""
ai/predictor.py  — FIXED VERSION

Changes
───────
A. PROBABILITY-BASED LABEL — uses model.predict_proba() instead of
   predict() so we get a confidence-weighted label, not always the
   majority class.  Falls back to predict() if proba is unavailable.

B. THREE-TIER LABEL — returns "High Risk" / "Suspicious" / "Safe"
   based on probability thresholds rather than a hard 0/1 split.
   This means the AI actually differentiates borderline sessions.

C. LAZY LOAD — model loaded on first call, not at import time.

D. GRACEFUL FALLBACK — model not found or too few events → "Unknown".
"""

import joblib

MODEL_PATH = "ai/model.pkl"

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            _model = joblib.load(MODEL_PATH)
        except FileNotFoundError:
            raise RuntimeError(
                f"Model not found at '{MODEL_PATH}'. "
                "Run `python -m ai.train_model` first."
            )
    return _model


def predict_user(events: list) -> str:
    """
    Predict risk label from a raw events list.

    Returns
    ───────
    "High Risk"   — model assigns ≥ 65 % probability to label 1
    "Suspicious"  — model assigns 35–65 % probability to label 1
    "Safe"        — model assigns < 35 % probability to label 1
    "Unknown"     — insufficient data or model unavailable
    """
    from ai.dataset_builder import extract_features

    features = extract_features(events)
    if features is None:
        return "Unknown"

    try:
        model = _get_model()

        # Prefer probability output for nuanced labelling
        if hasattr(model, "predict_proba"):
            proba    = model.predict_proba([features])[0]
            # proba[1] = probability of class 1 (phished / high risk)
            # Classes may be [0,1] or just [0] if single-class trained
            classes  = list(model.classes_)
            if 1 in classes:
                p_risk = proba[classes.index(1)]
            else:
                p_risk = 0.0

            if p_risk >= 0.65:
                return "High Risk"
            elif p_risk >= 0.35:
                return "Suspicious"
            else:
                return "Safe"

        # Fallback: hard prediction
        pred = model.predict([features])[0]
        return "High Risk" if pred == 1 else "Safe"

    except RuntimeError as exc:
        print(f"[predictor] {exc}")
        return "Not trained"
    except Exception as exc:
        print(f"[predictor] Prediction error: {exc}")
        return "Unknown"
