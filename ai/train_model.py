import os

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

TRAINING_FILE = "logs/training_data.json"
MODEL_PATH    = "ai/model.pkl"


def load_dataset(filepath: str = TRAINING_FILE):
   
    import json, math

    try:
        with open(filepath) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Training file not found: {filepath}")
        return [], []
    except json.JSONDecodeError:
        print(f"❌ Training file is corrupt: {filepath}")
        return [], []

    X, y = [], []

    for session_id, session_data in data.items():
        if isinstance(session_data, dict) and "events" in session_data:
            events = session_data["events"]
        elif isinstance(session_data, list):
            events = session_data
        else:
            continue

        if not isinstance(events, list) or len(events) < 2:
            continue

        features = _extract_features(events)
        if features is None:
            continue

        label = 1 if any(e.get("event") == "form_submit" for e in events) else 0
        X.append(features)
        y.append(label)

    print(f"[train] Loaded {len(X)} sessions from {filepath}")
    return X, y


def _extract_features(events: list):
    """8-column feature vector for RandomForest."""
    if len(events) < 2:
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
        first_click or 0,
        clicks,
        tab_switches,
        idle_events,
        duration,
        click_rate,
        hesitation,
        engagement,
    ]


def build_baseline(filepath: str = TRAINING_FILE):
    """
    FIX #3: Build logs/baseline.json from training data.
    Must be called before anomaly detection works correctly.
    """
    import json, math

    try:
        with open(filepath) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("❌ Cannot build baseline — training file missing or corrupt.")
        return

    from analyzer.feature_extractor import extract_features as extract_dict

    all_features = {}

    for session_id, session_data in data.items():
        if isinstance(session_data, dict) and "events" in session_data:
            session = session_data
        elif isinstance(session_data, list):
            session = {"events": session_data}
        else:
            continue

        try:
            feats = extract_dict(session)
        except Exception:
            continue

        for k, v in feats.items():
            all_features.setdefault(k, []).append(v)

    if not all_features:
        print("❌ No valid sessions for baseline.")
        return

    baseline = {}
    for k, values in all_features.items():
        mean     = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std      = math.sqrt(variance)
        baseline[k] = {"mean": round(mean, 4), "std": round(std, 4)}

    os.makedirs("logs", exist_ok=True)
    with open("logs/baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)

    print(f"✅ Baseline written → logs/baseline.json ({len(baseline)} features, "
          f"{len(next(iter(all_features.values())))} sessions)")


def main():
    print("\n=== AI Training Pipeline ===\n")

    print("[1/3] Building anomaly baseline…")
    build_baseline()


    print("[2/3] Loading dataset…")
    X, y = load_dataset()

    if len(X) == 0:
        print("❌ No training data available.")
        print("   Collect sessions by having users visit the phishing page.")
        print("   At least some sessions must have form_submit events (label=1).")
        return

    
    unique_labels = set(y)
    if len(unique_labels) < 2:
        label_name = "submitted" if 1 in unique_labels else "not submitted"
        print(f"⚠️  All {len(X)} sessions have the same label ({label_name}).")
        print("   Need BOTH sessions with and without form_submit to train.")
        print("   Collect more varied sessions and try again.")
        return

    label_counts = {l: y.count(l) for l in sorted(unique_labels)}
    print(f"   {len(X)} samples — labels: {label_counts}")

    print("[3/3] Training RandomForest…")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    preds    = model.predict(X_test)
    accuracy = accuracy_score(y_test, preds)
    print(f"\nAccuracy: {accuracy * 100:.2f}%\n")
    print(classification_report(y_test, preds, zero_division=0))

    feature_names = [
        "first_click_time", "clicks", "tab_switches", "idle_events",
        "duration", "click_rate", "hesitation", "engagement",
    ]
    print("Feature Importance:")
    for name, score in zip(feature_names, model.feature_importances_):
        print(f"  {name}: {score:.4f}")

    os.makedirs("ai", exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\n✅ Model saved → {MODEL_PATH}")
    print("   Run this script again after collecting more sessions to improve accuracy.\n")


if __name__ == "__main__":
    main()
