import json
import math
import os

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

# Dict-based extractor (7 named keys) — used ONLY for baseline building
from analyzer.feature_extractor import extract_features as _extract_dict_features

INPUT_FILE  = "logs/sessions.json"
OUTPUT_FILE = "logs/baseline.json"


# ------------------------------------------------------------------
# LOCAL ML FEATURE EXTRACTOR
# Returns an 8-element list matching the RandomForest feature columns.
# Renamed from extract_features → _extract_ml_features to avoid
# shadowing the import above (FIX #1).
# ------------------------------------------------------------------
def _extract_ml_features(events):
    """
    Extract 8-column feature vector from a raw events list.
    Returns None if there are fewer than 2 events.
    """
    if not isinstance(events, list) or len(events) < 2:
        return None

    first_click  = None
    clicks       = 0
    tab_switches = 0
    idle_events  = 0

    start = events[0].get("timestamp", 0)
    end   = events[-1].get("timestamp", start)

    for e in events:
        etype = e.get("event", "").lower()
        data  = e.get("data", {})

        if etype == "first_click" and first_click is None:
            first_click = data.get("delay", data.get("time", 0))
            # custom.js sends delay in seconds; older code sent ms
            if first_click and first_click > 300:
                first_click /= 1000.0

        elif etype == "click":
            clicks += 1

        elif etype == "tab_hidden":
            tab_switches += 1

        elif etype == "idle":
            idle_events += 1

    duration   = max(0, end - start)
    click_rate = clicks / duration if duration > 0 else 0
    hesitation = first_click if first_click is not None else duration
    engagement = clicks + idle_events

    return [
        first_click or 0,   # 0: first_click_time  (seconds)
        clicks,             # 1: clicks
        tab_switches,       # 2: tab_switches
        idle_events,        # 3: idle_events
        duration,           # 4: duration           (seconds)
        click_rate,         # 5: click_rate
        hesitation,         # 6: hesitation         (seconds)
        engagement,         # 7: engagement
    ]


# Public alias so predictor.py / external callers can still import extract_features
extract_features = _extract_ml_features


# ------------------------------------------------------------------
# BASELINE BUILDER
# Writes logs/baseline.json — consumed by anomaly.py
# FIX #2: correctly iterates dict, unwraps session format
# ------------------------------------------------------------------
def build_baseline():
    with open(INPUT_FILE) as f:
        data = json.load(f)

    all_features: dict = {}

    # FIX #2: sessions.json is a dict keyed by session_id
    for session_id, session_data in data.items():
        if isinstance(session_data, dict) and "events" in session_data:
            session = session_data
        elif isinstance(session_data, list):
            session = {"events": session_data}
        else:
            print(f"[baseline] Skipping invalid session: {session_id}")
            continue

        try:
            features = _extract_dict_features(session)  # dict-based, has named keys
        except Exception as exc:
            print(f"[baseline] Feature extraction failed for {session_id}: {exc}")
            continue

        for k, v in features.items():
            all_features.setdefault(k, []).append(v)

    if not all_features:
        print("❌ No valid sessions — baseline not written.")
        return

    baseline = {}
    for k, values in all_features.items():
        mean     = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std      = math.sqrt(variance)
        baseline[k] = {"mean": round(mean, 4), "std": round(std, 4)}

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(baseline, f, indent=2)

    n_sessions = len(next(iter(all_features.values())))
    print(f"✅ Baseline written → {OUTPUT_FILE}  "
          f"({len(baseline)} features across {n_sessions} sessions)")


# ------------------------------------------------------------------
# DATASET LOADER — called by train_model.py
# ------------------------------------------------------------------
def load_dataset():
    with open(INPUT_FILE) as f:
        data = json.load(f)

    X, y = [], []

    for session_id, session_data in data.items():

        if isinstance(session_data, dict) and "events" in session_data:
            events = session_data["events"]
        elif isinstance(session_data, list):
            events = session_data
        else:
            print(f"[dataset] Skipping invalid session: {session_id}")
            continue

        if not isinstance(events, list) or len(events) < 2:
            print(f"[dataset] Skipping short/bad events: {session_id}")
            continue

        features = _extract_ml_features(events)
        if features is None:
            continue

        label = 1 if any(e.get("event") == "form_submit" for e in events) else 0
        X.append(features)
        y.append(label)

    print(f"[dataset] Loaded {len(X)} valid sessions.")
    return X, y


# ------------------------------------------------------------------
# STANDALONE TRAIN + EVALUATE (not used by train_model.py)
# ------------------------------------------------------------------
def train_model():
    X, y = load_dataset()

    if len(X) == 0:
        print("No valid data found.")
        return None

    print(f"Dataset size: {len(X)} samples")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    feature_names = [
        "first_click_time", "clicks", "tab_switches", "idle_events",
        "duration", "click_rate", "hesitation", "engagement",
    ]
    print("\nFeature Importance:")
    for name, score in zip(feature_names, model.feature_importances_):
        print(f"  {name}: {score:.4f}")

    # FIX #3: return before any debug prints (dead code removed)
    return model


if __name__ == "__main__":
    build_baseline()
    train_model()
