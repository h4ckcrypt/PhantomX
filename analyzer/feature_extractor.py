from analyzer.feature_utils import (
    avg_typing_speed,
    count,
    get_total_time,
    hesitation_time,
    mouse_variance,
    typing_variance,
)


def extract_features(session):

    if isinstance(session, dict):
        events = session.get("events", [])
    else:
        events = []

    return {
        "total_time":      get_total_time(events),
        "typing_speed":    avg_typing_speed(events),
        "typing_variance": typing_variance(events),
        "mouse_variance":  mouse_variance(events),
        "tab_switches":    count(events, "tab_hidden"),
        "copy_events":     count(events, "copy"),
        "hesitation":      hesitation_time(events),
    }
