"""
CityPulse Jaipur API.

Run from the project folder:
    python3 -m uvicorn backend.main:app --port 8000
Interactive docs: http://127.0.0.1:8000/docs

Mapping to the original CityPulse framework:
  Resource management      -> /api/streams, /api/streams/{id}/observations
  Geospatial infrastructure-> /api/streams?w=&s=&e=&n=, /api/city
  Data federation          -> /api/snapshot (fuses every feed into one view)
  Event detection          -> anomalies + possible links in the snapshot, /api/events
New for Jaipur:
  Resident reports, confirm/dispute, points ledger -> /api/reports, /api/leaderboard
  Alert rules + live event stream (SSE)            -> /api/alerts/rules, /api/events/stream
  AI Navi                                          -> /api/navi
"""
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import city as C
from . import navi, service
from .store import Store, StoreError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
store = Store(os.environ.get("CITYPULSE_DB", "citypulse.db"))


@asynccontextmanager
async def lifespan(app):
    task = None
    if os.environ.get("CITYPULSE_OFFLINE") != "1":
        task = asyncio.create_task(service.ingest_forever(store))
    yield
    if task:
        task.cancel()


app = FastAPI(title="CityPulse Jaipur API", version="1.0.0", lifespan=lifespan,
              description="Live civic pulse for Jaipur: weather, traffic and resident reports fused into one view.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ------------------------------------------------------------------ models
class ReportIn(BaseModel):
    type: str = Field(examples=["Waterlogging"])
    place: str = Field(examples=["Gopalpura"])
    severity: int = Field(2, ge=1, le=3)
    handle: str = Field(examples=["pinkcity_rider"])
    note: str = ""


class VoteIn(BaseModel):
    handle: str


class RuleIn(BaseModel):
    metric: str = Field(examples=["rain"], description="rain | speed | pulse | report")
    target: str = Field(examples=["North"], description="zone, road, 'Jaipur' or report type")
    threshold: float = Field(examples=[10])
    label: str = ""


class NaviIn(BaseModel):
    question: str
    mode: str = "replay"
    t: int = 95
    route: Optional[str] = None
    progress: float = 0.2
    area: str = "All Jaipur"
    delayed: Optional[str] = None


def _bad(e):
    raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------ core
@app.get("/", tags=["meta"])
def root():
    return {"name": "CityPulse Jaipur API", "docs": "/docs", "snapshot": "/api/snapshot"}


@app.get("/api/health", tags=["meta"])
def health():
    snap = service.build_snapshot(store, mode="live")
    return {"ok": True, "feeds": snap["feeds"], "clock": snap["meta"]["clock"]}


@app.get("/api/snapshot", tags=["fusion"])
def get_snapshot(mode: str = Query("replay", pattern="^(live|replay)$"),
                 t: int = Query(95, ge=0, le=180, description="Replay minute after 5 PM"),
                 area: str = "All Jaipur", route: Optional[str] = None,
                 progress: float = Query(0.2, ge=0, le=1), delayed: Optional[str] = None):
    """Everything the dashboard shows, fused into one document."""
    return service.build_snapshot(store, mode, t, area, route, progress, delayed or None)


@app.get("/api/city", tags=["geo"])
def city():
    """Static city model: zones, roads, routes, drainage flows, places, report types."""
    return dict(zones={z: dict(centroid=C.ZONE_CENTROIDS[z], polygon=C.zone_polygon(z)) for z in C.ZONES},
                roads={k: [list(p) for p in v] for k, v in C.ROADS.items()},
                routes={k: [list(p) for p in v] for k, v in C.ROUTES.items()},
                flows=C.FLOWS, places={k: dict(lon=v[0], lat=v[1], road=v[2]) for k, v in C.PLACES.items()},
                report_types=C.REPORT_TYPES, calendar=C.CALENDAR)


# ------------------------------------------------------------------ resource management
@app.get("/api/streams", tags=["streams"])
def streams(kind: Optional[str] = None, zone: Optional[str] = None,
            w: Optional[float] = None, s: Optional[float] = None,
            e: Optional[float] = None, n: Optional[float] = None):
    """Available data sources, optionally inside a bounding box (like CityPulse's area selection)."""
    bbox = (w, s, e, n) if None not in (w, s, e, n) else None
    return store.streams(kind, zone, bbox)


@app.get("/api/streams/{stream_id}/observations", tags=["streams"])
def observations(stream_id: str, minutes: int = Query(180, ge=5, le=2880)):
    st = store.stream(stream_id)
    if not st:
        raise HTTPException(404, "Stream not found")
    return dict(stream=st, observations=store.history(st["id"], minutes))


# ------------------------------------------------------------------ reports
@app.get("/api/reports", tags=["reports"])
def reports():
    return store.active_reports()


@app.post("/api/reports", tags=["reports"], status_code=201)
def create_report(body: ReportIn):
    try:
        return store.create_report(body.type, body.place, body.severity, body.handle, body.note)
    except StoreError as e:
        _bad(e)


@app.post("/api/reports/{rid}/confirm", tags=["reports"])
def confirm(rid: str, body: VoteIn):
    try:
        return store.vote(rid, body.handle, "confirm")
    except StoreError as e:
        _bad(e)


@app.post("/api/reports/{rid}/dispute", tags=["reports"])
def dispute(rid: str, body: VoteIn):
    try:
        return store.vote(rid, body.handle, "dispute")
    except StoreError as e:
        _bad(e)


@app.post("/api/reports/{rid}/resolve", tags=["reports"])
def resolve(rid: str):
    store.resolve(rid)
    return {"ok": True}


@app.get("/api/leaderboard", tags=["reports"])
def leaderboard(area: Optional[str] = None):
    rows = service.board(store)
    return [r for r in rows if not area or r["area"] == area]


# ------------------------------------------------------------------ alerts + events
@app.get("/api/alerts/rules", tags=["alerts"])
def rules():
    return store.rules()


@app.post("/api/alerts/rules", tags=["alerts"], status_code=201)
def add_rule(body: RuleIn):
    try:
        return store.add_rule(body.metric, body.target, body.threshold, body.label)
    except StoreError as e:
        _bad(e)


@app.delete("/api/alerts/rules/{rule_id}", tags=["alerts"])
def delete_rule(rule_id: int):
    store.delete_rule(rule_id)
    return {"ok": True}


@app.get("/api/events", tags=["alerts"])
def events(since_id: int = 0, limit: int = Query(50, ge=1, le=200)):
    return store.events(since_id, limit)


@app.get("/api/events/stream", tags=["alerts"])
async def event_stream(request: Request):
    """Server-Sent Events: new reports, verifications, alerts and feed outages as they happen."""
    async def gen():
        existing = store.events(0, 1)
        last = existing[-1]["id"] if existing else 0
        idle = 0
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            new = store.events(last)
            for ev in new:
                last = ev["id"]
                yield f"id: {ev['id']}\nevent: {ev['kind']}\ndata: {json.dumps(ev)}\n\n"
            idle = 0 if new else idle + 1
            if idle and idle % 8 == 0:
                yield ": keepalive\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(gen(), media_type="text/event-stream")


# ------------------------------------------------------------------ AI Navi
@app.post("/api/navi", tags=["navi"])
def ask_navi(body: NaviIn):
    snap = service.build_snapshot(store, body.mode, body.t, body.area, body.route, body.progress, body.delayed)
    return navi.answer(body.question, snap)
