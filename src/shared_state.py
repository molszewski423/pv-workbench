import json
from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "state.json"

def _load_state():
    if not STATE_FILE.exists():
        return {"active_drug": "Ozempic", "pipeline_statuses": {}}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"active_drug": "Ozempic", "pipeline_statuses": {}}

def _save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except IOError as e:
        print(f"Error saving state: {e}")

def get_active_drug():
    state = _load_state()
    return state.get("active_drug", "Ozempic")

def set_active_drug(name):
    state = _load_state()
    state["active_drug"] = name
    _save_state(state)

def get_pipeline_status(name):
    state = _load_state()
    return state.get("pipeline_statuses", {}).get(name, "Idle")

def set_pipeline_status(name, status):
    state = _load_state()
    if "pipeline_statuses" not in state:
        state["pipeline_statuses"] = {}
    state["pipeline_statuses"][name] = status
    _save_state(state)
