from analyzer.anomaly import detect_anomaly
from analyzer.feature_extractor import extract_features
from analyzer.intent import detect_intent, is_confused


# ── Human-likeness scorer ─────────────────────────────────────────

def _human_score(features: dict) -> float:
    """
    0–100: how human-like is the session?
    Higher = more human = LOWER base risk.
    """
    score = 0.0

    ts = features.get("typing_speed", 0)
    if 50 < ts < 600:
        score += 25
    elif ts >= 600:
        score += 12   # very fast but not zero

    if features.get("typing_variance", 0) > 15:
        score += 20

    if features.get("hesitation", 0) > 1.0:
        score += 15

    if features.get("mouse_variance", 0) > 800:
        score += 20

    if features.get("tab_switches", 99) <= 2:
        score += 10

    if features.get("copy_events", 1) == 0:
        score += 10

    return min(score, 100.0)



def _event_modifiers(events: list) -> float:
    
    modifier = 0.0

    autofill_events    = [e for e in events if e.get("event") == "autofill"]
    field_focus_events = [e for e in events if e.get("event") == "field_focus"]
    keypresses         = sum(1 for e in events if e.get("event") == "keypress")
   
    paste_events       = sum(1 for e in events if e.get("event") == "paste")

    if autofill_events:
        n = len(autofill_events)
        if keypresses < 3:
            modifier += n * 6.0  
        else:
            modifier += n * 2.0  

    if paste_events > 0:
        modifier += paste_events * 4.0  
    if field_focus_events:
        modifier -= len(field_focus_events) * 2.0  
    return modifier



def _analyze_events(events: list) -> float:
    
    session          = {"events": events}
    features         = extract_features(session)
    anomaly_score, _ = detect_anomaly(features)
    human            = _human_score(features)
    event_mod        = _event_modifiers(events)

    raw = (100.0 - human) + (anomaly_score * 8.0) + event_mod
    return max(0.0, min(100.0, raw))


def _form_submit_score(events: list) -> float:
    
    base = 85.0

    
    if len(events) >= 2:
        duration = events[-1].get("timestamp", 0) - events[0].get("timestamp", 0)
        if duration < 3.0:
            base += 10.0   
        elif duration < 8.0:
            base += 5.0

    
    keypresses    = sum(1 for e in events if e.get("event") == "keypress")
    autofill_ev   = sum(1 for e in events if e.get("event") == "autofill")
    paste_ev      = sum(1 for e in events if e.get("event") == "paste")

    if autofill_ev > 0 and keypresses < 3:
        base += 5.0  

    if paste_ev > 0:
        base += 3.0   
    session  = {"events": events}
    features = extract_features(session)
    human    = _human_score(features)
    if human >= 80:
        base -= 5.0 

    return max(65.0, min(100.0, base))



def _bounce_score(events: list) -> float:
    if len(events) < 2:
        return 65.0
    duration = events[-1].get("timestamp", 0) - events[0].get("timestamp", 0)
    if duration < 1.0 and len(events) <= 2:
        return 80.0   
    if duration < 5.0:
        return 60.0
    return max(30.0, 60.0 - duration)



def _explore_score(events: list) -> float:
    clicks = sum(1 for e in events if e.get("event") == "click")
    confused = is_confused(events)
    if len(events) < 2:
        return 40.0
    duration   = events[-1].get("timestamp", 0) - events[0].get("timestamp", 0)
    base       = 35.0
    if confused:
        base += 15.0
    click_rate = clicks / max(duration, 1.0)
    if click_rate > 2.0:
        base += 10.0
    return min(base, 65.0)


def calculate_score(events: list) -> float:
  
    if not events or not isinstance(events, list):
        return 0.0

    
    has_submit = any(e.get("event") == "form_submit" for e in events)
    if has_submit:
        return round(_form_submit_score(events), 1)

    intent = detect_intent(events)
    if intent == "bounce":
        return round(_bounce_score(events), 1)
    elif intent == "explore_only":
        return round(_explore_score(events), 1)
    else:
        return round(_analyze_events(events), 1)


def classify_user(score: float) -> str:
    if score < 30:
        return "Low Risk"
    elif score < 60:
        return "Medium Risk"
    else:
        return "High Risk"
