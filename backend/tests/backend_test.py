"""SWARM-X Guardian backend regression tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if "REACT_APP_BACKEND_URL" in os.environ else "https://resilient-fleet.preview.emergentagent.com"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---- Health / meta ----
def test_health(client):
    r = client.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    for k in ("running", "agents", "tick"):
        assert k in data
    assert isinstance(data["agents"], int) and data["agents"] > 0


# ---- Simulation snapshot ----
def test_simulation_snapshot(client):
    r = client.get(f"{BASE_URL}/api/simulation")
    assert r.status_code == 200
    d = r.json()
    for key in ("agents", "tasks", "links", "obstacles", "events", "metrics"):
        assert key in d, f"missing {key}"
    assert isinstance(d["agents"], list) and len(d["agents"]) > 0
    valid_states = {"IDLE", "EN_ROUTE_TO_PICKUP", "PICKING_UP", "EN_ROUTE_TO_DROPOFF",
                    "DELIVERING", "RETURNING", "CHARGING", "FAILED", "AVOIDING", "EN_ROUTE"}
    # Just assert every agent has a status string
    for a in d["agents"]:
        assert "status" in a or "state" in a
    m = d["metrics"]
    assert isinstance(m, dict) and len(m) > 0


# ---- Reset + mode ----
def test_reset_agent_failure_scenario(client):
    r = client.post(f"{BASE_URL}/api/simulation/reset",
                    json={"scenario": "agent_failure", "agent_count": 10, "mode": "decentralized"})
    assert r.status_code == 200
    snap = r.json()
    assert len(snap["agents"]) == 10


def test_toggle_mode(client):
    r = client.post(f"{BASE_URL}/api/simulation/mode", json={"mode": "centralized"})
    assert r.status_code == 200
    r2 = client.post(f"{BASE_URL}/api/simulation/mode", json={"mode": "decentralized"})
    assert r2.status_code == 200


# ---- Network ----
def test_network_state_change(client):
    r = client.post(f"{BASE_URL}/api/simulation/network", json={"state": "HIGH_PACKET_LOSS"})
    assert r.status_code == 200
    time.sleep(1.0)
    snap = client.get(f"{BASE_URL}/api/simulation").json()
    ns = snap.get("network_state") or snap.get("metrics", {}).get("network_state")
    assert ns == "HIGH_PACKET_LOSS" or "HIGH_PACKET_LOSS" in str(snap)
    # Restore
    client.post(f"{BASE_URL}/api/simulation/network", json={"state": "NORMAL"})


def test_network_invalid(client):
    r = client.post(f"{BASE_URL}/api/simulation/network", json={"state": "BOGUS"})
    assert r.status_code == 400


# ---- Tasks ----
def test_create_task(client):
    r = client.post(f"{BASE_URL}/api/tasks", json={
        "pickup_x": 100, "pickup_y": 100,
        "dropoff_x": 800, "dropoff_y": 500,
        "priority": "HIGH", "payload_weight": 2.0,
    })
    assert r.status_code == 200
    d = r.json()
    assert "task" in d
    tid = d["task"]["id"]
    assert d["task"]["status"] in {"AUCTIONING", "ASSIGNED", "PENDING", "CREATED"}

    # Give the sim a moment to auction it
    time.sleep(2.5)
    tasks = client.get(f"{BASE_URL}/api/tasks").json()
    found = next((t for t in tasks["tasks"] + tasks["completed"] if t["id"] == tid), None)
    assert found is not None
    # After a few ticks task should be assigned or progressed
    assert found["status"] != "CREATED"


# ---- Agent failure ----
def test_agent_failure_and_recovery(client):
    # reset to known state
    client.post(f"{BASE_URL}/api/simulation/reset",
                json={"scenario": "normal", "agent_count": 10, "mode": "decentralized"})
    time.sleep(0.5)
    snap = client.get(f"{BASE_URL}/api/simulation").json()
    aid = snap["agents"][0]["id"]
    r = client.post(f"{BASE_URL}/api/agents/{aid}/fail")
    assert r.status_code == 200
    d = r.json()
    a = next(x for x in d["agents"] if x["id"] == aid)
    status = a.get("status") or a.get("state")
    assert status == "FAILED"
    # Check events include a failure entry
    kinds = " ".join(str(e) for e in d["events"])
    assert "FAIL" in kinds.upper()


def test_agent_failure_missing(client):
    r = client.post(f"{BASE_URL}/api/agents/DR-DOES-NOT-EXIST/fail")
    assert r.status_code == 404


# ---- Experiments ----
def test_experiments_scenarios(client):
    r = client.get(f"{BASE_URL}/api/experiments/scenarios")
    assert r.status_code == 200
    d = r.json()
    assert len(d["scenarios"]) == 5
    ids = {s["id"] for s in d["scenarios"]}
    assert {"baseline", "agent_failure", "multi_failure", "network_degradation", "high_load"} <= ids


def test_experiments_run(client):
    r = client.post(f"{BASE_URL}/api/experiments/run",
                    json={"scenario": "baseline", "mode": "decentralized"},
                    timeout=120)
    assert r.status_code == 200
    d = r.json()
    for k in ("completion_rate", "avg_delivery_time", "safety_events"):
        assert k in d, f"missing {k}. keys={list(d.keys())}"


def test_experiments_compare(client):
    r = client.post(f"{BASE_URL}/api/experiments/compare",
                    json={"scenario": "agent_failure"},
                    timeout=180)
    assert r.status_code == 200
    d = r.json()
    assert "centralized" in d and "decentralized" in d
    assert "completion_rate" in d["centralized"] and "completion_rate" in d["decentralized"]


# ---- Judge mode ----
def test_judge_script(client):
    r = client.get(f"{BASE_URL}/api/judge/script")
    assert r.status_code == 200
    steps = r.json()["steps"]
    assert len(steps) == 13


def test_judge_start(client):
    r = client.post(f"{BASE_URL}/api/judge/start")
    assert r.status_code == 200
    d = r.json()
    high = [t for t in d["tasks"] if t.get("priority") == "HIGH"]
    assert len(high) >= 1
