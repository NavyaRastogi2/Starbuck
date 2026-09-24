"""
Feed adapters. Each one fetches a public source and normalizes it into
stream observations (stream_id, timestamp UTC, value, extra).

- Open-Meteo forecast API: current rain/temperature/humidity/wind, the last
  3 hours of 15-minute rainfall (backfill) and the next hour (forecast).
  Free, no API key.
- Open-Meteo air-quality API: US AQI, PM2.5, PM10. Free, no key.
- TomTom Traffic Flow (optional): measured road speeds. Only used if the
  TOMTOM_API_KEY environment variable is set.
"""
from datetime import datetime, timedelta, timezone

from . import city as C
from .store import now

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY = "https://air-quality-api.open-meteo.com/v1/air-quality"
TOMTOM = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"


def _coords():
    lats = ",".join(f"{C.ZONE_CENTROIDS[z][1]:.4f}" for z in C.ZONES)
    lons = ",".join(f"{C.ZONE_CENTROIDS[z][0]:.4f}" for z in C.ZONES)
    return lats, lons


def weather_params():
    lats, lons = _coords()
    return dict(latitude=lats, longitude=lons, timezone="GMT",
                current="temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,"
                        "wind_direction_10m,weather_code",
                minutely_15="precipitation", past_minutely_15=12, forecast_minutely_15=4)


def air_params():
    lats, lons = _coords()
    return dict(latitude=lats, longitude=lons, timezone="GMT", current="us_aqi,pm2_5,pm10")


def _as_list(data):
    return data if isinstance(data, list) else [data]


def _ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def ingest_weather(store, data):
    """Normalize an Open-Meteo forecast response. Precipitation arrives as mm
    per 15 minutes; we store mm/hr (x4) so every feed uses the same unit."""
    t = now()
    for zone, d in zip(C.ZONES, _as_list(data)):
        cur = d.get("current") or {}
        rain = float(cur.get("precipitation") or 0) * 4
        store.observe(f"weather:{zone}", round(rain, 1), extra=dict(
            temp=cur.get("temperature_2m"), humidity=cur.get("relative_humidity_2m"),
            wind=cur.get("wind_speed_10m"), wind_dir=cur.get("wind_direction_10m"),
            code=cur.get("weather_code")), ts=t)
        m = d.get("minutely_15") or {}
        future = []
        for s, v in zip(m.get("time", []), m.get("precipitation", [])):
            if v is None:
                continue
            when = _ts(s)
            if when < t - timedelta(minutes=1):
                store.observe_if_new(f"weather:{zone}", round(v * 4, 1), when)
            else:
                future.append((when, v * 4))
        n30 = max([v for w, v in future if w <= t + timedelta(minutes=30)], default=0.0)
        n60 = max([v for w, v in future if w <= t + timedelta(minutes=60)], default=0.0)
        store.observe(f"forecast:{zone}", round(n60, 1),
                      extra=dict(next_30=round(n30, 1), next_60=round(n60, 1)), ts=t)


def ingest_air(store, data):
    for zone, d in zip(C.ZONES, _as_list(data)):
        cur = d.get("current") or {}
        if cur.get("us_aqi") is None:
            continue
        store.observe(f"air:{zone}", float(cur["us_aqi"]),
                      extra=dict(pm2_5=cur.get("pm2_5"), pm10=cur.get("pm10")))


async def poll_weather(store, client):
    r = await client.get(OPEN_METEO, params=weather_params())
    r.raise_for_status()
    ingest_weather(store, r.json())


async def poll_air(store, client):
    r = await client.get(AIR_QUALITY, params=air_params())
    r.raise_for_status()
    ingest_air(store, r.json())


async def poll_tomtom(store, client, key):
    for road in C.ROADS:
        lon, lat = C.road_mid(road)
        r = await client.get(TOMTOM, params=dict(point=f"{lat},{lon}", unit="KMPH", key=key))
        r.raise_for_status()
        fs = r.json().get("flowSegmentData") or {}
        if fs.get("currentSpeed") is not None:
            store.observe(f"probe:{road}", float(fs["currentSpeed"]),
                          extra=dict(free=fs.get("freeFlowSpeed"), confidence=fs.get("confidence")))
