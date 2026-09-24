"""
Replay provider: a scripted monsoon evening in Jaipur, 5:00 to 8:00 PM.
Used for demos and for "historical replay". Produces the same state shape
as the live provider, so everything downstream is shared.
"""
import math

from . import city as C
from . import fusion

STEP = 5
RAIN_PROFILE = {"North": (60, 28, 26), "East": (80, 30, 12),
                "West": (85, 30, 9), "South": (110, 30, 7)}   # peak minute, spread, peak mm/hr

SCRIPT = [
    # t, type, place, lon, lat, road, severity, source, reporter, corroborations
    (22, "Rain alert", "North Jaipur hills", 75.800, 26.965, None, 2, "Weather alert feed", None, 0),
    (48, "Stray cattle", "Agra Road near Galta Gate", 75.8450, 26.9180, "Agra Road", 1, "Citizen", "galta_gate_guy", 3),
    (62, "Tree fall", "Sikar Road, Vidhyadhar Nagar", 75.7820, 26.9560, "Sikar Road", 2, "Citizen", "vkia_nightshift", 5),
    (74, "Waterlogging", "Johari Bazaar & Badi Chaupar", 75.8270, 26.9196, "MI Road", 3, "Citizen", "pinkcity_rider", 9),
    (76, "Power outage", "Vaishali Nagar, sector 4", 75.7437, 26.9117, "Queens Road", 2, "Utility outage feed", None, 0),
    (80, "Signal down", "Queens Road junction", 75.7650, 26.9120, "Queens Road", 2, "Citizen", "ward42_watch", 4),
    (86, "Waterlogging", "Jhotwara underpass", 75.7400, 26.9480, "Sikar Road", 3, "Citizen", "jhotwara_updates", 6),
    (95, "VIP movement", "JLN Marg, Secretariat to airport", 75.8110, 26.8930, "JLN Marg", 2, "Traffic police advisory", None, 0),
    (100, "Police naka", "Ajmer Road near 200 ft bypass", 75.7300, 26.8960, "Ajmer Road", 1, "Citizen", "ajmerroad_daily", 2),
    (112, "Waterlogging", "Gopalpura, Tonk Road", 75.7920, 26.8660, "Tonk Road", 3, "Citizen", "mansarovar_mom", 7),
    (118, "Waterlogging", "Mansarovar metro stretch", 75.7621, 26.8505, "New Sanganer Road", 2, "Citizen", "sodala_scout", 3),
    (122, "Baraat", "Tonk Road near Jawahar Circle", 75.7920, 26.8420, "Tonk Road", 2, "Citizen", "tonkroad_tales", 4),
    (135, "Road work", "Station Road, metro works", 75.8000, 26.9230, "Station Road", 1, "Municipal works feed", None, 0),
    (140, "Accident", "Ajmer Road near Sodala", 75.7700, 26.9030, "Ajmer Road", 2, "Citizen", "pinkcity_rider", 2),
]


def clock(t):
    h, m = divmod(17 * 60 + int(t), 60)
    return f"{h - 12}:{m:02d} PM"


def rain(zone, t):
    peak, spread, amp = RAIN_PROFILE[zone]
    return round(amp * math.exp(-((t - peak) / spread) ** 2), 1)


def weather(zone, t):
    r = rain(zone, t)
    return dict(rain=r, temp=round(32.5 - 0.22 * r - 0.01 * t, 1), aqi=int(118 - 2.2 * r - 0.08 * t),
                humidity=int(min(98, 62 + 1.3 * r)), wind=round(8 + 0.4 * r, 1))


def reports_at(t):
    out = []
    for (t0, typ, place, lon, lat, road, sev, src, who, corr) in SCRIPT:
        if t0 <= t < t0 + C.DURATION_MIN.get(typ, 60):
            out.append(dict(id=f"replay-{t0}", type=typ, place=place, lon=lon, lat=lat, road=road,
                            zone=C.zone_of(lon, lat), severity=sev, source=src, reporter=who,
                            corroborations=corr, disputes=0, status="active", ago=int(t - t0),
                            created=clock(t0), live=False))
    return out


def _roads_at(t):
    levels = fusion.flow_levels(lambda z, ago: rain(z, t - ago))
    return fusion.road_metrics(17 * 60 + t, levels, reports_at(t))


def history(t_end):
    points = []
    for t in range(0, int(t_end) + 1, STEP):
        reps = reports_at(t)
        roads = _roads_at(t)
        points.append(dict(label=clock(t),
                           rain={z: rain(z, t) for z in C.ZONES},
                           speed={r: m["speed"] for r, m in roads.items()},
                           reports={z: sum(1 for r in reps if r["zone"] == z) for z in C.ZONES}))
    return points


def state(t, delayed=None, extra_reports=None):
    """World state at replay minute t. `delayed` makes one feed 12 min stale."""
    t = max(0, min(180, int(t)))
    tw = max(0, t - 12) if delayed == "Weather" else t
    tt = max(0, t - 12) if delayed == "Traffic" else t
    tr = max(0, t - 12) if delayed == "Ground reports" else t

    rain_at = lambda z, ago: rain(z, tw - ago)                    # noqa: E731
    reports = reports_at(tr) + list(extra_reports or [])
    levels = fusion.flow_levels(rain_at)
    traffic_levels = fusion.flow_levels(lambda z, ago: rain(z, tt - ago))
    roads = fusion.road_metrics(17 * 60 + tt, traffic_levels, reports_at(tt) + list(extra_reports or []))

    feeds = []
    for name, provider in [("Weather", "Scripted replay"), ("Traffic", "Scripted replay"),
                           ("Ground reports", "Scripted replay + live residents")]:
        late = name == delayed
        feeds.append(dict(name=name, provider=provider, status="delayed" if late else "replay",
                          age_min=12 if late else 0))
    return dict(mode="replay", t=t, clock=clock(t), minute_of_day=17 * 60 + t,
                weather={z: weather(z, tw) for z in C.ZONES}, weather_ok=True, forecast=None,
                rain_at=rain_at, levels=levels, roads=roads, reports=reports, feeds=feeds,
                points=history(t), step_min=STEP, delayed=delayed)
