import math


def count(events, event_type):
    return sum(1 for e in events if e.get("event") == event_type)


def get_total_time(events):
    if len(events) < 2:
        return 0
    start = events[0].get("timestamp", 0)
    end   = events[-1].get("timestamp", start)
    return max(0, end - start)


def avg_typing_speed(events):
   
    key_events = [e for e in events if e.get("event") == "keypress"]
    if len(key_events) < 2:
        return 0
    times     = [e["timestamp"] for e in key_events]
    intervals = [t2 - t1 for t1, t2 in zip(times, times[1:])]
    return sum(intervals) / len(intervals)


def typing_variance(events):
    
    key_events = [e for e in events if e.get("event") == "keypress"]
    if len(key_events) < 2:
        return 0
    times     = [e["timestamp"] for e in key_events]
    intervals = [t2 - t1 for t1, t2 in zip(times, times[1:])]
    mean      = sum(intervals) / len(intervals)
    return sum((x - mean) ** 2 for x in intervals) / len(intervals)


def mouse_variance(events):
    
    moves = [e for e in events if e.get("event") == "mousemove" and "data" in e]
    if len(moves) < 2:
        return 0
    xs = [e["data"].get("x", 0) for e in moves]
    ys = [e["data"].get("y", 0) for e in moves]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    var = sum((x - mean_x) ** 2 + (y - mean_y) ** 2 for x, y in zip(xs, ys))
    return var / len(xs)


def mouse_speed(events):
    
    moves = [e for e in events if e.get("event") == "mousemove" and "data" in e]
    if len(moves) < 2:
        return 0
    distances = []
    for i in range(1, len(moves)):
        dx = moves[i]["data"].get("x", 0) - moves[i - 1]["data"].get("x", 0)
        dy = moves[i]["data"].get("y", 0) - moves[i - 1]["data"].get("y", 0)
        distances.append(math.sqrt(dx ** 2 + dy ** 2))
    return sum(distances) / len(distances)


def hesitation_time(events):
    
    first_key = None
    page_load = None

    for e in events:
        
        etype = e.get("event")
        if etype in ("page_load", "page_loaded") and page_load is None:
            page_load = e.get("timestamp")
        elif etype == "keypress" and first_key is None:
            first_key = e.get("timestamp")

    if page_load is None or first_key is None:
        return 0

    diff = first_key - page_load

    
    if diff > 300:
        diff = diff / 1000.0

    return max(0, diff)
