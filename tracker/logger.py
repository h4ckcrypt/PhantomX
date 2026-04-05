# Copyright (c) 2025 Your Name — github.com/h4ckcrypt/PhantomX
# Non-commercial use only. See LICENSE.

import json
import os
import threading
import time

_lock = threading.Lock()  

# Absolute paths anchored to this file's location.
# logger.py lives at  project/tracker/logger.py
# Sessions live at    project/logs/sessions.json
# This ensures the correct file is written regardless of Flask's CWD.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_FILE = os.path.join(_PROJECT_ROOT, "logs", "sessions.json")
TRAINING_FILE = os.path.join(_PROJECT_ROOT, "logs", "training_data.json")


def _read_json(filepath: str) -> dict:
    try:
        with open(filepath) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_json(filepath: str, data: dict) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp = filepath + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, filepath)


def log_event(session_id: str, event: str,
              extra: dict = None,
              cid: str = None,
              uid: str = None) -> None:
   
    if not session_id:
        return

    entry = {
        "event":     event,
        "timestamp": time.time(),
        "data":      extra or {},
    }

    with _lock:
        for filepath in (SESSIONS_FILE, TRAINING_FILE):
            store = _read_json(filepath)

            if session_id not in store:
                record = {
                    "events":     [],
                    "status":     "active",
                    "created_at": time.time(),
                }
                if cid:
                    record["campaign_id"] = cid
                if uid:
                    record["user_id"] = uid
            else:
                record = store[session_id]

            record["events"].append(entry)
            record["last_seen"] = time.time()

            # Status machine — only transitions forward, never back
            if event == "page_close":
                record["status"] = "closed"
            elif event == "tab_visible" and record.get("status") != "closed":
                record["status"] = "active"

            store[session_id] = record
            _write_json(filepath, store)
