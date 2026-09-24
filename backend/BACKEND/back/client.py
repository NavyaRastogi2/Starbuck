"""
Frontend -> backend client. If the backend isn't running, the frontend
still works: it builds the replay snapshot in-process from the same engine.
"""
import os

import httpx

API = os.environ.get("CITYPULSE_API", "http://127.0.0.1:8000").rstrip("/")
OFFLINE_MSG = "Backend not reachable. Start everything with: python3 run.py"


def _local_snapshot(t, area, route, progress, delayed):
    from backend import service
    return service.build_snapshot(None, "replay", t, area, route, progress, delayed)


def snapshot(mode, t, area, route, progress, delayed):
    params = dict(mode=mode, t=t, area=area, route=route, progress=progress)
    if delayed:
        params["delayed"] = delayed
    try:
        r = httpx.get(f"{API}/api/snapshot", params=params, timeout=20)
        r.raise_for_status()
        snap = r.json()
        snap["meta"]["source"] = "backend"
        return snap
    except Exception:
        snap = _local_snapshot(t, area, route, progress, delayed)
        snap["meta"]["source"] = "local"
        snap["meta"]["note"] = ("Backend is offline, so you're seeing the built-in replay."
                                + (" Live mode needs the backend." if mode == "live" else ""))
        return snap


def get(path, params=None, default=None):
    try:
        r = httpx.get(f"{API}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return default


def post(path, payload=None):
    try:
        r = httpx.post(f"{API}{path}", json=payload or {}, timeout=20)
        if r.status_code >= 400:
            try:
                return False, r.json().get("detail", r.text)
            except Exception:
                return False, r.text
        return True, r.json()
    except Exception:
        return False, OFFLINE_MSG


def delete(path):
    try:
        return httpx.delete(f"{API}{path}", timeout=10).status_code < 400
    except Exception:
        return False


def ask_navi(question, mode, t, route, progress, area, delayed):
    ok, data = post("/api/navi", dict(question=question, mode=mode, t=t, route=route,
                                      progress=progress, area=area, delayed=delayed))
    if ok:
        return data
    from backend import navi
    return navi.answer(question, _local_snapshot(t, area, route, progress, delayed))
