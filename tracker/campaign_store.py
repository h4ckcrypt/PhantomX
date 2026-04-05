import json
import os
import time
import uuid

CAMPAIGNS_FILE = os.path.join("logs", "campaigns.json")



def _read() -> dict:
    try:
        with open(CAMPAIGNS_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write(data: dict) -> None:
    os.makedirs(os.path.dirname(CAMPAIGNS_FILE), exist_ok=True)
    tmp = CAMPAIGNS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CAMPAIGNS_FILE)




def create_campaign(name: str, template: str,
                    start_time=None, end_time=None) -> dict:
    campaigns = _read()
    cid = "cid_" + uuid.uuid4().hex[:10]
    campaign = {
        "id":         cid,
        "name":       name,
        "template":   template,
        "status":     "active",
        "created_at": time.time(),
        "start_time": start_time,
        "end_time":   end_time,
        "targets":    {},
    }
    campaigns[cid] = campaign
    _write(campaigns)
    return campaign


def get_campaign(cid: str) -> dict | None:
    return _read().get(cid)


def list_campaigns() -> list:
    data = _read()
    out  = []
    for cid, c in data.items():
        metrics = compute_metrics(cid)
        out.append({**c, "metrics": metrics})
    out.sort(key=lambda c: c.get("created_at", 0), reverse=True)
    return out


def update_campaign_status(cid: str, status: str) -> bool:
    campaigns = _read()
    if cid not in campaigns:
        return False
    campaigns[cid]["status"] = status
    _write(campaigns)
    return True


def delete_campaign(cid: str) -> bool:
    campaigns = _read()
    if cid not in campaigns:
        return False
    del campaigns[cid]
    _write(campaigns)
    return True



def add_target(cid: str, email: str, name: str = "") -> dict | None:
    campaigns = _read()
    if cid not in campaigns:
        return None
    uid = "uid_" + uuid.uuid4().hex[:10]
    target = {
        "uid":        uid,
        "email":      email,
        "name":       name,
        "link_token": "tok_" + uuid.uuid4().hex[:16],
        "outcome":    "ignored",
        "session_id": None,
        "events":     [],
    }
    campaigns[cid]["targets"][uid] = target
    _write(campaigns)
    return target


def add_targets_bulk(cid: str, entries: list[dict]) -> list:
    """entries = [{"email": "...", "name": "..."}, ...]"""
    created = []
    for e in entries:
        t = add_target(cid, e.get("email", ""), e.get("name", ""))
        if t:
            created.append(t)
    return created


def get_target_by_token(token: str) -> tuple[str | None, str | None, dict | None]:
    """Returns (campaign_id, user_id, target_dict) for a link token."""
    for cid, campaign in _read().items():
        for uid, target in campaign.get("targets", {}).items():
            if target.get("link_token") == token:
                return cid, uid, target
    return None, None, None


def get_target(cid: str, uid: str) -> dict | None:
    campaigns = _read()
    return campaigns.get(cid, {}).get("targets", {}).get(uid)



FLOW_STEPS = ["email_sent", "link_clicked", "page_visited",
              "interaction", "compromised"]

OUTCOME_MAP = {
    
    "email_sent":   "ignored",
    "link_clicked": "clicked",
    "page_visited": "clicked",
    "interaction":  "engaged",
    "compromised":  "compromised",
}

OUTCOME_RANK = {"ignored": 0, "clicked": 1, "engaged": 2, "compromised": 3}


def record_flow_step(cid: str, uid: str, step: str,
                     session_id: str = None) -> bool:
    """
    Record an attack-flow milestone for a target.
    Outcome only upgrades (compromised can't go back to engaged).
    """
    campaigns = _read()
    if cid not in campaigns or uid not in campaigns[cid]["targets"]:
        return False

    target = campaigns[cid]["targets"][uid]

    # Append event
    target["events"].append({"step": step, "ts": time.time()})

    # Upgrade outcome
    new_outcome = OUTCOME_MAP.get(step, target["outcome"])
    if OUTCOME_RANK.get(new_outcome, 0) > OUTCOME_RANK.get(target["outcome"], 0):
        target["outcome"] = new_outcome

    
    if session_id and not target.get("session_id"):
        target["session_id"] = session_id

    _write(campaigns)
    return True


def mark_email_sent(cid: str, uid: str) -> bool:
    return record_flow_step(cid, uid, "email_sent")


def compute_metrics(cid: str) -> dict:
    campaign = _read().get(cid, {})
    targets  = campaign.get("targets", {})

    total       = len(targets)
    sent        = sum(1 for t in targets.values()
                      if any(e["step"] == "email_sent" for e in t.get("events", [])))
    clicked     = sum(1 for t in targets.values()
                      if t.get("outcome") in ("clicked", "engaged", "compromised"))
    engaged     = sum(1 for t in targets.values()
                      if t.get("outcome") in ("engaged", "compromised"))
    compromised = sum(1 for t in targets.values()
                      if t.get("outcome") == "compromised")
    ignored     = sum(1 for t in targets.values()
                      if t.get("outcome") == "ignored")

    def rate(n, d=sent or total or 1):
        return round(n / max(d, 1) * 100, 1)

    return {
        "total":            total,
        "sent":             sent,
        "clicked":          clicked,
        "engaged":          engaged,
        "compromised":      compromised,
        "ignored":          ignored,
        "click_rate":       rate(clicked),
        "interaction_rate": rate(engaged),
        "compromise_rate":  rate(compromised),
    }
