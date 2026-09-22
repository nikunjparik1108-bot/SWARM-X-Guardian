"""Tests for the new integration endpoints: /integrations/status, /files/*, /copilot/*."""
import io
import os
import struct
import zlib
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _tiny_png() -> bytes:
    # Minimal valid 1x1 red PNG
    sig = b"\x89PNG\r\n\x1a\n"
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    return s


def test_integrations_status(client):
    r = client.get(f"{BASE_URL}/api/integrations/status")
    assert r.status_code == 200
    d = r.json()
    assert d["storage_enabled"] is True
    assert d["copilot_enabled"] is True
    assert d.get("model")  # 'low' preset


def test_files_list_ok(client):
    r = client.get(f"{BASE_URL}/api/files")
    assert r.status_code == 200
    d = r.json()
    assert "files" in d and isinstance(d["files"], list)


def test_files_upload_and_persist(client):
    png = _tiny_png()
    files = {"file": ("TEST_backend.png", png, "image/png")}
    data = {"category": "delivery", "ref_id": "TEST-DEL-001", "caption": "backend test"}
    r = client.post(f"{BASE_URL}/api/files/upload", files=files, data=data)
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["category"] == "delivery"
    assert rec["ref_id"] == "TEST-DEL-001"
    assert rec["content_type"] == "image/png"
    fid = rec["id"]

    # Verify persisted in listing filtered by ref_id
    r2 = client.get(f"{BASE_URL}/api/files", params={"ref_id": "TEST-DEL-001"})
    assert r2.status_code == 200
    ids = [f["id"] for f in r2.json()["files"]]
    assert fid in ids

    # Download works and returns bytes
    r3 = client.get(f"{BASE_URL}/api/files/{fid}/download")
    assert r3.status_code == 200
    assert r3.content[:8] == b"\x89PNG\r\n\x1a\n"

    # Delete (soft) cleanup
    r4 = client.delete(f"{BASE_URL}/api/files/{fid}")
    assert r4.status_code == 200


def test_files_upload_invalid_category(client):
    files = {"file": ("x.png", _tiny_png(), "image/png")}
    r = client.post(f"{BASE_URL}/api/files/upload", files=files, data={"category": "bogus"})
    assert r.status_code == 400


def test_copilot_ask(client):
    r = client.post(f"{BASE_URL}/api/copilot/ask",
                    json={"question": "What is the current network state?"}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("answer") and isinstance(d["answer"], str)
    assert "citations" in d and isinstance(d["citations"], list)
