import os
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def test_health_and_initial_snapshot():
    health = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    requests.post(f"{BASE_URL}/api/simulation/reset", json={"scenario": "normal"}, timeout=10)
    snapshot = requests.get(f"{BASE_URL}/api/simulation", timeout=10).json()
    assert snapshot["scenario"] == "normal"
    assert len(snapshot["agents"]) == 12
    assert snapshot["transport"]["fallback"] is True


def test_toggle_pause_resume():
    before = requests.get(f"{BASE_URL}/api/simulation", timeout=10).json()
    paused = requests.post(f"{BASE_URL}/api/simulation/toggle", timeout=10).json()
    resumed = requests.post(f"{BASE_URL}/api/simulation/toggle", timeout=10).json()
    assert paused["running"] is (not before["running"])
    assert resumed["running"] is before["running"]


def test_all_scenarios():
    expected = {"normal": 12, "failure": 12, "comms": 12, "obstacle": 12, "battery": 12, "scale50": 50, "scale100": 100}
    for scenario, count in expected.items():
        response = requests.post(f"{BASE_URL}/api/simulation/reset", json={"scenario": scenario}, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"] == scenario
        assert len(data["agents"]) == count


def test_failure_injection_and_task_creation():
    state = requests.post(f"{BASE_URL}/api/simulation/reset", json={"scenario": "normal"}, timeout=10).json()
    agent_id = state["agents"][0]["id"]
    failed = requests.post(f"{BASE_URL}/api/simulation/agents/{agent_id}/fail", timeout=10)
    assert failed.status_code == 200
    failed_data = failed.json()
    agent = next(a for a in failed_data["agents"] if a["id"] == agent_id)
    assert agent["status"] == "FAILED"
    assert any(event["kind"] == "FAILURE" for event in failed_data["events"])
    created = requests.post(f"{BASE_URL}/api/tasks", json={"pickup_x": 10, "pickup_y": 20, "dropoff_x": 800, "dropoff_y": 500, "priority": "HIGH"}, timeout=10)
    assert created.status_code == 200
    assert created.json()["tasks"][0]["priority"] == "HIGH"
    assert created.json()["tasks"][0]["status"] == "AUCTION"


def test_invalid_scenario_and_missing_agent():
    invalid = requests.post(f"{BASE_URL}/api/simulation/reset", json={"scenario": "nope"}, timeout=10)
    assert invalid.status_code == 400
    missing = requests.post(f"{BASE_URL}/api/simulation/agents/AX-999/fail", timeout=10)
    assert missing.status_code == 404