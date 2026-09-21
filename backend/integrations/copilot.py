"""Perplexity Sonar-Pro Mission Copilot for SWARM-X Guardian.

Sends the user question + a compact snapshot of live simulation state
to Perplexity and returns the answer with citations. Non-streaming.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("swarm.copilot")

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "").strip()
# Perplexity retired /chat/completions on 2026-09-27. Use Agent API presets.
# sonar-pro -> "low", sonar-reasoning-pro -> "medium", sonar-deep-research -> "high"
PERPLEXITY_PRESET = os.environ.get("PERPLEXITY_MODEL", "low")
# Backward-compat: map old model names to presets
_LEGACY_MODEL_TO_PRESET = {
    "sonar": "fast", "sonar-pro": "low",
    "sonar-reasoning-pro": "medium", "sonar-deep-research": "high",
}
if PERPLEXITY_PRESET in _LEGACY_MODEL_TO_PRESET:
    PERPLEXITY_PRESET = _LEGACY_MODEL_TO_PRESET[PERPLEXITY_PRESET]
PERPLEXITY_URL = "https://api.perplexity.ai/v1/agent"

SYSTEM_PROMPT = (
    "You are the on-mission analyst for SWARM-X Guardian, a decentralized "
    "multi-agent autonomous logistics simulation. You get: (a) the operator's "
    "question, (b) the current live simulation snapshot as JSON. "
    "Answer concisely (max 6 short paragraphs). When you reference "
    "external concepts (e.g. auction allocation, gossip protocols, A* replanning) "
    "cite web sources. If the question is answered entirely by the snapshot, "
    "don't invent citations. Never claim real-world flight or safety guarantees."
)


def is_enabled() -> bool:
    return bool(PERPLEXITY_API_KEY)


def _compact_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Trim the snapshot to what the analyst actually needs."""
    if not snapshot:
        return {}
    agents = [
        {
            "id": a.get("id"),
            "status": a.get("status"),
            "battery": a.get("battery"),
            "task": a.get("current_task"),
            "neighbors": len(a.get("neighbors") or []),
            "comm": a.get("comm_quality"),
            "health": a.get("health"),
        }
        for a in (snapshot.get("agents") or [])[:20]
    ]
    tasks = [
        {"id": t.get("id"), "status": t.get("status"), "priority": t.get("priority"),
         "assigned": t.get("assigned_agent"), "reassignments": t.get("reassignments")}
        for t in (snapshot.get("tasks") or [])[:20]
    ]
    events = [
        {"time": e.get("time"), "kind": e.get("kind"), "message": e.get("message")}
        for e in (snapshot.get("events") or [])[:15]
    ]
    return {
        "tick": snapshot.get("tick"),
        "sim_time": snapshot.get("sim_time"),
        "mode": snapshot.get("mode"),
        "scenario": snapshot.get("scenario"),
        "network_state": snapshot.get("network_state"),
        "metrics": snapshot.get("metrics"),
        "agents": agents,
        "tasks": tasks,
        "events": events,
    }


async def ask(question: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    if not is_enabled():
        return {
            "answer": "Copilot is offline — PERPLEXITY_API_KEY is not configured.",
            "citations": [],
            "disabled": True,
        }
    compact = _compact_snapshot(snapshot)
    user_content = (
        f"Operator question:\n{question}\n\n"
        f"Live simulation snapshot (JSON):\n{json.dumps(compact, separators=(',', ':'))}"
    )
    payload = {
        "preset": PERPLEXITY_PRESET,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "tools": [{"type": "web_search"}],
        "max_output_tokens": 700,
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                PERPLEXITY_URL,
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if r.status_code == 429:
            return {"answer": "Perplexity rate limit reached. Try again in a moment.",
                    "citations": [], "rate_limited": True}
        r.raise_for_status()
        data = r.json()
    except httpx.TimeoutException:
        return {"answer": "The analyst timed out. Try a shorter question.", "citations": []}
    except httpx.HTTPStatusError as e:
        logger.exception("Perplexity upstream error")
        detail = ""
        try:
            detail = " " + (e.response.json().get("error", {}).get("message") or "")[:200]
        except Exception:  # noqa: BLE001, S110
            pass
        return {"answer": f"Analyst upstream error ({e.response.status_code}).{detail}",
                "citations": []}
    except Exception as e:  # noqa: BLE001
        logger.exception("Copilot failure")
        return {"answer": f"Analyst error: {e}", "citations": []}

    # Agent API response: output[] contains message + search/tool items.
    # - final answer is in items with type=="message" -> content[].text
    # - citations live in tool-result items with a "results" array of {url, title, ...}
    answer_parts: list[str] = []
    citations: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(url: str, title: str = "", snippet: str = "") -> None:
        if not url or url in seen:
            return
        seen.add(url)
        citations.append({"url": url, "title": title or url, "snippet": snippet[:220]})

    for item in data.get("output") or []:
        if item.get("type") == "message":
            for c in item.get("content") or []:
                if c.get("type") == "output_text" and c.get("text"):
                    answer_parts.append(c["text"])
                for a in c.get("annotations") or []:
                    url = a.get("url") or (a.get("citation") or {}).get("url")
                    if url:
                        _add(url, a.get("title", ""), a.get("snippet", ""))
        # Web-search tool results — may or may not have an explicit type.
        for res in item.get("results") or []:
            _add(res.get("url", ""), res.get("title", ""), res.get("snippet", ""))
        for c in item.get("contents") or []:
            _add(c.get("url", ""), c.get("title", ""), c.get("snippet", ""))

    answer = "\n\n".join(answer_parts).strip()
    return {
        "answer": answer or "No answer was returned.",
        "citations": citations,
        "usage": data.get("usage"),
        "model": data.get("model", PERPLEXITY_PRESET),
    }
