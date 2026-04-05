def detect_intent(events):
    
    has_click = any(e.get("event") == "click" for e in events)
    has_input = any(e.get("event") in ("keypress", "input") for e in events)

    if not has_click:
        return "bounce"
    elif has_click and not has_input:
        return "explore_only"
    else:
        return "engaged"


def is_confused(events):
   
    clicks = [e for e in events if e.get("event") == "click"]
    return len(clicks) > 8


def is_low_engagement(events):
    
    meaningful = {"click", "mousemove", "keypress"}
    interaction_count = sum(1 for e in events if e.get("event") in meaningful)
    return interaction_count < 5
