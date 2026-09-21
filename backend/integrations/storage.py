"""Emergent Object Storage adapter for SWARM-X Guardian.

Wraps `PUT/GET /objstore/api/v1/storage/objects/{path}` with a cached
session-scoped storage_key. Files are stored under the app-name prefix
`swarm-x-guardian/uploads/{category}/{uuid}.{ext}`.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import requests

logger = logging.getLogger("swarm.storage")

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = os.environ.get("APP_NAME", "swarm-x-guardian")

_storage_key: str | None = None
_disabled: bool = False

ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp", "pdf"}
MIME_BY_EXT = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def is_enabled() -> bool:
    return not _disabled and bool(EMERGENT_KEY)


def init_storage(force: bool = False) -> str | None:
    """Mint and cache a storage_key. Returns None if the integration is unavailable."""
    global _storage_key, _disabled
    if _disabled:
        return None
    if _storage_key and not force:
        return _storage_key
    if not EMERGENT_KEY:
        _disabled = True
        logger.warning("EMERGENT_LLM_KEY missing — object storage disabled")
        return None
    try:
        r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        r.raise_for_status()
        _storage_key = r.json().get("storage_key")
        logger.info("Object storage initialized")
        return _storage_key
    except Exception as e:  # noqa: BLE001
        _disabled = True
        logger.warning(f"Object storage init failed → disabled: {e}")
        return None


def _resolve_ext(filename: str) -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXT))}")
    return ext


def build_path(category: str, filename: str) -> tuple[str, str, str]:
    ext = _resolve_ext(filename)
    fid = uuid.uuid4().hex
    path = f"{APP_NAME}/uploads/{category}/{fid}.{ext}"
    content_type = MIME_BY_EXT[ext]
    return path, fid, content_type


def put_object(path: str, data: bytes, content_type: str) -> dict[str, Any]:
    key = init_storage()
    if not key:
        raise RuntimeError("storage_unavailable")
    r = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    if r.status_code == 404:  # cached key went stale
        init_storage(force=True)
        r = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": _storage_key or "", "Content-Type": content_type},
            data=data,
            timeout=120,
        )
    r.raise_for_status()
    return r.json()


def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    if not key:
        raise RuntimeError("storage_unavailable")
    r = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    if r.status_code == 404:
        init_storage(force=True)
        r = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": _storage_key or ""},
            timeout=60,
        )
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")
