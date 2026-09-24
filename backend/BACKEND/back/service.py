"""
Service layer used by the API *and* by the frontend's offline fallback.

build_snapshot()  -> one JSON document for the UI (live or replay)
ingest_forever()  -> background loop that keeps live data flowing
"""
import asyncio
import logging
import os
import time

from . import city as C
from . import feeds, live, scenario, snapshot, trust

log = logging.getLogger("citypulse")
DELAY_CHOICES = (None, "Weather", "Traffic", "Ground reports")


def board(store=None):
    if store is None:
        return trust.leaderboard(C.CONTRIBUTORS_SEED)
    return trust.leaderboard(store.contributors(), store.ledger_sums())


def build_snapshot(store=None, mode="replay", t=95, area="All Jaipur", route=None,
                   progress=0.2, delayed=None):
    if area not in ["All Jaipur"] + C.ZONES:
        area = "All Jaipur"
    if delayed not in DELAY_CHOICES:
        delayed = None
    if mode == "live" and store is not None:
        state = live.state(store, delayed)
    else:
        mode = "replay"
        extra = store.active_reports(window_min=60) if store is not None else []
        state = scenario.state(t, delayed, extra)
    rules = store.rules() if store is not None else []
    return snapshot.build(state, area, route, progress, rules, board(store))


# ---------------------------------------------------------------- ingestion
def record_traffic(store):
    """Store the current fused road speeds so live history builds up."""
    st = live.state(store)
    for road, m in st["roads"].items():
        store.observe(f"traffic:{road}", m["speed"], extra=dict(congestion=m["congestion"], source=m["source"]))


def check_alerts(store):
    if not store.rules():
        return
    snap = build_snapshot(store, mode="live")
    for a in snap["alerts"]:
        if not store.recent_alert_event(a["rule_id"]):
            store.event("alert", a["message"], dict(rule_id=a["rule_id"]))


async def ingest_forever(store):
    import httpx   # imported here so the offline fallback never needs it

    key = os.environ.get("TOMTOM_API_KEY", "").strip()
    if key:
        for road in C.ROADS:
            lon, lat = C.road_mid(road)
            store.register(f"probe:{road}", f"Measured speed {road}", "probe", "TomTom Traffic Flow",
                           C.road_zone(road), road, lon, lat, "km/h", 600)
    due = dict(weather=0.0, air=0.0, tomtom=0.0, purge=0.0)
    weather_down = False
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "CityPulse-Jaipur/1.0"}) as client:
        while True:
            t = time.monotonic()
            if t >= due["weather"]:
                try:
                    await feeds.poll_weather(store, client)
                    due["weather"] = t + 300
                    if weather_down:
                        store.event("feed_up", "Weather feed is back", {})
                    weather_down = False
                except Exception as e:  # network down, API change, etc.
                    log.warning("weather poll failed: %s", e)
                    for z in C.ZONES:
                        store.mark_error(f"weather:{z}", e)
                    due["weather"] = t + 60
                    if not weather_down:
                        store.event("feed_down", "Weather feed unavailable, retrying", {"error": str(e)[:120]})
                    weather_down = True
            if t >= due["air"]:
                try:
                    await feeds.poll_air(store, client)
                    due["air"] = t + 900
                except Exception as e:
                    log.warning("air poll failed: %s", e)
                    due["air"] = t + 120
            if key and t >= due["tomtom"]:
                try:
                    await feeds.poll_tomtom(store, client, key)
                    due["tomtom"] = t + 600
                except Exception as e:
                    log.warning("tomtom poll failed: %s", e)
                    due["tomtom"] = t + 300
            try:
                await asyncio.to_thread(record_traffic, store)
                await asyncio.to_thread(check_alerts, store)
            except Exception as e:
                log.exception("fusion tick failed: %s", e)
            if t >= due["purge"]:
                store.purge()
                due["purge"] = t + 3600
            await asyncio.sleep(60)
