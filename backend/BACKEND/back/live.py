"""
Live provider: builds the world state for Jaipur *right now* from what the
ingestion loop has stored (real Open-Meteo weather + air quality, traffic
model or TomTom, resident reports). Same output shape as scenario.state().
"""
from datetime import timedelta

from . import city as C
from . import fusion
from .store import now, parse

STEP = 5


def ist_label(dt):
    t = dt.astimezone(C.IST)
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def _age_min(ts):
    return int((now() - parse(ts)).total_seconds() // 60) if ts else None


def _feed_status(store, kind, fresh, stale):
    rows = store.streams(kind=kind)
    seen = [r["last_seen"] for r in rows if r["last_seen"]]
    age = _age_min(max(seen)) if seen else None
    err = next((r["last_error"] for r in rows if r["last_error"]), None)
    if age is None:
        status = "unavailable"
    elif age <= fresh:
        status = "live"
    elif age <= stale:
        status = "delayed"
    else:
        status = "unavailable"
    return status, age, err, (rows[0]["provider"] if rows else "")


def state(store, delayed=None):
    t = now()
    mod = t.astimezone(C.IST).hour * 60 + t.astimezone(C.IST).minute

    def rain_at(zone, ago):
        v = store.value_at(f"weather:{zone}", t - timedelta(minutes=ago), tolerance_min=25)
        return float(v) if v is not None else 0.0

    weather, forecast = {}, {}
    for z in C.ZONES:
        w = store.latest(f"weather:{z}")
        a = store.latest(f"air:{z}")
        f = store.latest(f"forecast:{z}")
        ex = w["extra"] if w else {}
        weather[z] = dict(rain=round(w["value"], 1) if w else 0.0,
                          temp=ex.get("temp"), humidity=ex.get("humidity"), wind=ex.get("wind"),
                          aqi=int(a["value"]) if a else None,
                          pm2_5=(a["extra"] or {}).get("pm2_5") if a else None)
        if f:
            forecast[z] = f["extra"]

    w_status, w_age, w_err, w_prov = _feed_status(store, "weather", 12, 60)
    reports = store.active_reports()
    levels = fusion.flow_levels(rain_at)

    overrides = {}
    for road in C.ROADS:
        p = store.latest(f"probe:{road}")
        if p and _age_min(p["ts"]) <= 20 and p["extra"].get("free"):
            overrides[road] = (p["value"], p["extra"]["free"])
    roads = fusion.road_metrics(mod, levels, reports, overrides)

    feeds = [
        dict(name="Weather", provider=w_prov or "Open-Meteo", status=w_status, age_min=w_age, error=w_err),
        dict(name="Traffic", provider="TomTom + CityPulse model" if overrides else "CityPulse traffic model",
             status="live" if overrides else "modelled", age_min=0),
        dict(name="Ground reports", provider="Residents via CityPulse", status="live", age_min=0),
    ]
    if delayed:   # test switch: show how the UI copes with a stale feed
        for f in feeds:
            if f["name"] == delayed:
                f["status"], f["age_min"] = "delayed", max(12, f["age_min"] or 0)

    return dict(mode="live", t=None, clock=ist_label(t), minute_of_day=mod, weather=weather,
                weather_ok=w_status != "unavailable", forecast=forecast or None, rain_at=rain_at,
                levels=levels, roads=roads, reports=reports, feeds=feeds,
                points=history(store, t), step_min=STEP, delayed=delayed)


def history(store, t, minutes=180):
    """5-minute buckets over the last 3 hours, from stored observations."""
    points = []
    start = t - timedelta(minutes=minutes)
    b = start
    while b <= t:
        rain = {}
        for z in C.ZONES:
            v = store.value_at(f"weather:{z}", b, tolerance_min=20)
            if v is not None:
                rain[z] = round(v, 1)
        speed = {}
        for road in C.ROADS:
            v = store.value_at(f"traffic:{road}", b, tolerance_min=6)
            if v is not None:
                speed[road] = int(v)
        if rain or speed:
            points.append(dict(label=ist_label(b), rain={z: rain.get(z, 0.0) for z in C.ZONES},
                               speed=speed, reports=store.report_counts_at(b)))
        b += timedelta(minutes=STEP)
    return points
