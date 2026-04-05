import json

BASELINE_FILE = "logs/baseline.json"


def load_baseline():
    try:
        with open(BASELINE_FILE) as f:
            return json.load(f)
    except:
        return {}


def z_score(value, mean, std):
    if std == 0:
        return 0
    return abs((value - mean) / std)


def detect_anomaly(features):
    baseline = load_baseline()

    total_anomaly = 0
    details = {}

    for key, value in features.items():
        if key not in baseline:
            continue

        mean = baseline[key]["mean"]
        std = baseline[key]["std"]

        z = z_score(value, mean, std)
        details[key] = round(z, 2)

        if z > 3:
            total_anomaly += 2
        elif z > 2:
            total_anomaly += 1
        elif z > 1:
            total_anomaly += 0.5

    return total_anomaly, details