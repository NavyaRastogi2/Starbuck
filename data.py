"""
CityPulse Jaipur - data layer (no UI code here).

Everything is SIMULATED so the demo runs offline. The scenario is a
monsoon evening in Jaipur, replayed from 5:00 PM to 8:00 PM.
`t` everywhere = minutes after 5:00 PM (0..180).

Three feeds are fused into one model:
  1. Weather   - rain / temperature / AQI per zone (N, E, S, W)
  2. Traffic   - congestion and speed per road
  3. Reports   - citizen + official ground reports (incidents)
Swap any generator below for a real API later; the rest of the app
only depends on the function signatures.
"""
import math

# --------------------------------------------------------------------------
# Geography
# --------------------------------------------------------------------------
CENTER = (75.800, 26.905)                      # (lon, lat) roughly MI Road area
BBOX = dict(w=75.70, e=75.90, s=26.81, n=27.00)
ZONES = ["North", "East", "South", "West"]
ZONE_CENTROIDS = {
    "North": (75.800, 26.965),
    "East": (75.858, 26.905),
    "South": (75.800, 26.842),
    "West": (75.742, 26.905),
}
KM_PER_DEG_LON = 99.3    # at Jaipur's latitude
KM_PER_DEG_LAT = 110.6


def zone_of(lon, lat):
    dx = (lon - CENTER[0]) / (BBOX["e"] - CENTER[0])
    dy = (lat - CENTER[1]) / (BBOX["n"] - CENTER[1])
    if abs(dy) >= abs(dx):
        return "North" if dy >= 0 else "South"
    return "East" if dx >= 0 else "West"


def zone_polygon(zone):
    c = list(CENTER)
    nw, ne = [BBOX["w"], BBOX["n"]], [BBOX["e"], BBOX["n"]]
    se, sw = [BBOX["e"], BBOX["s"]], [BBOX["w"], BBOX["s"]]
    return {"North": [c, nw, ne], "East": [c, ne, se],
            "South": [c, se, sw], "West": [c, sw, nw]}[zone]


def clock(t):
    total = 17 * 60 + int(t)
    h, m = divmod(total, 60)
    return f"{h - 12}:{m:02d} PM"


def km(a, b):
    dx = (a[0] - b[0]) * KM_PER_DEG_LON
    dy = (a[1] - b[1]) * KM_PER_DEG_LAT
    return math.hypot(dx, dy)


# --------------------------------------------------------------------------
# Feed 1: weather
# --------------------------------------------------------------------------
# (peak minute, spread, peak mm/hr) - rain starts over the northern hills
RAIN_PROFILE = {"North": (60, 28, 26), "East": (80, 30, 12),
                "West": (85, 30, 9), "South": (110, 30, 7)}


def rain(zone, t):
    peak, spread, amp = RAIN_PROFILE[zone]
    return round(amp * math.exp(-((t - peak) / spread) ** 2), 1)


def weather(zone, t):
    r = rain(zone, t)
    return dict(zone=zone, rain=r,
                temp=round(32.5 - 0.22 * r - 0.01 * t, 1),
                aqi=int(118 - 2.2 * r - 0.08 * t),
                humidity=int(min(98, 62 + 1.3 * r)))


def rain_label(r):
    if r >= 15:
        return "heavy rain"
    if r >= 6:
        return "moderate rain"
    if r >= 1:
        return "light rain"
    return "dry"


# Where runoff goes. Based on the general lie of the land (hills to the
# north, city drains southward). Lags are ESTIMATES shown as ranges.
FLOWS = [
    dict(src="North", hotspot="Johari Bazaar & Badi Chaupar", zone="East",
         lon=75.8270, lat=26.9196, lag=(30, 45),
         roads=["MI Road", "Agra Road"], factor=0.9),
    dict(src="North", hotspot="Jhotwara underpass", zone="West",
         lon=75.7400, lat=26.9480, lag=(40, 55),
         roads=["Sikar Road", "Queens Road"], factor=0.7),
    dict(src="East", hotspot="Gopalpura, Tonk Road", zone="South",
         lon=75.7920, lat=26.8660, lag=(45, 70),
         roads=["Tonk Road", "JLN Marg"], factor=1.1),
    dict(src="West", hotspot="Mansarovar metro stretch", zone="South",
         lon=75.7621, lat=26.8505, lag=(40, 60),
         roads=["New Sanganer Road", "Ajmer Road"], factor=1.2),
]


def mid_lag(flow):
    return sum(flow["lag"]) / 2


def water_level(flow, t):
    """0..1 waterlogging risk at a hotspot."""
    upstream = rain(flow["src"], t - mid_lag(flow))
    local = rain(flow["zone"], t)
    return round(min(1.0, (upstream * flow["factor"] + local * 0.6) / 22), 2)


def risk_label(x):
    return "high" if x >= 0.65 else "medium" if x >= 0.35 else "low"


# --------------------------------------------------------------------------
# Feed 3: ground reports (defined before traffic, which reacts to them)
# --------------------------------------------------------------------------
DURATION = {"Rain alert": 90, "Waterlogging": 75, "VIP movement": 30,
            "Baraat": 50, "Power outage": 60, "Signal down": 55}
REPORTS = [
    # t, type, place, lon, lat, road, severity 1-3, source, reporter, corroborations
    (22, "Rain alert", "North Jaipur hills", 75.800, 26.965, None, 2,
     "Weather alert feed", None, 0),
    (48, "Stray cattle", "Agra Road near Galta Gate", 75.8450, 26.9180,
     "Agra Road", 1, "Citizen", "galta_gate_guy", 3),
    (62, "Tree fall", "Sikar Road, Vidhyadhar Nagar", 75.7820, 26.9560,
     "Sikar Road", 2, "Citizen", "vkia_nightshift", 5),
    (74, "Waterlogging", "Johari Bazaar & Badi Chaupar", 75.8270, 26.9196,
     "MI Road", 3, "Citizen", "pinkcity_rider", 9),
    (76, "Power outage", "Vaishali Nagar, sector 4", 75.7437, 26.9117,
     "Queens Road", 2, "Utility outage feed", None, 0),
    (80, "Signal down", "Queens Road junction", 75.7650, 26.9120,
     "Queens Road", 2, "Citizen", "ward42_watch", 4),
    (86, "Waterlogging", "Jhotwara underpass", 75.7400, 26.9480,
     "Sikar Road", 3, "Citizen", "jhotwara_updates", 6),
    (95, "VIP movement", "JLN Marg, Secretariat to airport", 75.8110, 26.8930,
     "JLN Marg", 2, "Traffic police advisory", None, 0),
    (100, "Police naka", "Ajmer Road near 200 ft bypass", 75.7300, 26.8960,
     "Ajmer Road", 1, "Citizen", "ajmerroad_daily", 2),
    (112, "Waterlogging", "Gopalpura, Tonk Road", 75.7920, 26.8660,
     "Tonk Road", 3, "Citizen", "mansarovar_mom", 7),
    (118, "Waterlogging", "Mansarovar metro stretch", 75.7621, 26.8505,
     "New Sanganer Road", 2, "Citizen", "sodala_scout", 3),
    (122, "Baraat", "Tonk Road near Jawahar Circle", 75.7920, 26.8420,
     "Tonk Road", 2, "Citizen", "tonkroad_tales", 4),
    (135, "Road work", "Station Road, metro works", 75.8000, 26.9230,
     "Station Road", 1, "Municipal works feed", None, 0),
    (140, "Accident", "Ajmer Road near Sodala", 75.7700, 26.9030,
     "Ajmer Road", 2, "Citizen", "pinkcity_rider", 2),
]
REPORT_COLORS = {
    "Waterlogging": [28, 143, 176], "Rain alert": [70, 110, 220],
    "Power outage": [123, 63, 196], "Signal down": [123, 63, 196],
    "VIP movement": [224, 69, 123], "Baraat": [240, 138, 36],
    "Police naka": [60, 60, 110], "Tree fall": [46, 158, 106],
    "Stray cattle": [150, 110, 60], "Road work": [200, 150, 30],
    "Accident": [210, 40, 50],
}


def active_reports(t):
    out = []
    for (t0, typ, place, lon, lat, road, sev, src, who, corr) in REPORTS:
        if t0 <= t < t0 + DURATION.get(typ, 60):
            official = src != "Citizen"
            out.append(dict(
                t0=t0, type=typ, place=place, lon=lon, lat=lat, road=road,
                severity=sev, source=src, reporter=who, corroborations=corr,
                verified=official or corr >= 3, zone=zone_of(lon, lat),
                ago=int(t - t0)))
    return sorted(out, key=lambda r: (-r["severity"], r["ago"]))


# --------------------------------------------------------------------------
# Feed 2: traffic
# --------------------------------------------------------------------------
ROADS = {
    "Station Road": [(75.7878, 26.9196), (75.8000, 26.9230), (75.8140, 26.9250)],
    "MI Road": [(75.7960, 26.9160), (75.8050, 26.9150), (75.8180, 26.9170), (75.8270, 26.9196)],
    "JLN Marg": [(75.8180, 26.9150), (75.8110, 26.8930), (75.8150, 26.8700), (75.8030, 26.8420)],
    "Tonk Road": [(75.8050, 26.9050), (75.7980, 26.8850), (75.7920, 26.8660),
                  (75.7920, 26.8420), (75.8030, 26.8250)],
    "Ajmer Road": [(75.7950, 26.9120), (75.7700, 26.9030), (75.7300, 26.8960)],
    "Amer Road": [(75.8260, 26.9280), (75.8460, 26.9530), (75.8513, 26.9855)],
    "Sikar Road": [(75.7980, 26.9290), (75.7820, 26.9560), (75.7400, 26.9480)],
    "Queens Road": [(75.7437, 26.9117), (75.7650, 26.9120), (75.7878, 26.9196)],
    "Agra Road": [(75.8270, 26.9196), (75.8450, 26.9180), (75.8800, 26.9100)],
    "New Sanganer Road": [(75.7621, 26.8505), (75.7750, 26.8800), (75.7700, 26.9000)],
}
ROAD_BASE = {"Station Road": .38, "MI Road": .42, "JLN Marg": .30, "Tonk Road": .36,
             "Ajmer Road": .32, "Amer Road": .25, "Sikar Road": .34,
             "Queens Road": .28, "Agra Road": .30, "New Sanganer Road": .30}


def road_zone(name):
    pts = ROADS[name]
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return zone_of(lon, lat)


def congestion(road, t, reports=None):
    reports = active_reports(t) if reports is None else reports
    rush = 0.22 * math.exp(-((t - 75) / 55) ** 2)            # evening peak
    water = max([water_level(f, t) for f in FLOWS if road in f["roads"]] or [0])
    incident = sum(0.07 * r["severity"] for r in reports if r["road"] == road)
    return round(min(0.9, ROAD_BASE[road] + rush + 0.28 * water + incident), 2)


def speed(road, t, reports=None):
    return int(round(48 * (1 - congestion(road, t, reports)) + 4))


def traffic_color(c):
    if c >= 0.7:
        return [224, 40, 80]
    if c >= 0.5:
        return [240, 138, 36]
    return [46, 158, 106]


# --------------------------------------------------------------------------
# Routes (Route mode)
# --------------------------------------------------------------------------
ROUTES = {
    "Vaishali Nagar to Hawa Mahal": [(75.7437, 26.9117), (75.7650, 26.9120), (75.7878, 26.9196),
                                     (75.8000, 26.9230), (75.8140, 26.9250), (75.8267, 26.9239)],
    "Mansarovar to Jaipur Junction": [(75.7621, 26.8505), (75.7750, 26.8800), (75.7700, 26.9000),
                                      (75.7800, 26.9100), (75.7878, 26.9196)],
    "Malviya Nagar to Amer Fort": [(75.8243, 26.8549), (75.8150, 26.8700), (75.8110, 26.8930),
                                   (75.8180, 26.9150), (75.8260, 26.9280), (75.8460, 26.9530),
                                   (75.8513, 26.9855)],
    "Airport to Johari Bazaar": [(75.8122, 26.8242), (75.8030, 26.8420), (75.7920, 26.8660),
                                 (75.7980, 26.8850), (75.8050, 26.9050), (75.8180, 26.9170),
                                 (75.8270, 26.9196)],
}


def _project(p, a, b):
    """Distance (km) from p to segment ab, and fraction along ab."""
    ax, ay = a[0] * KM_PER_DEG_LON, a[1] * KM_PER_DEG_LAT
    bx, by = b[0] * KM_PER_DEG_LON, b[1] * KM_PER_DEG_LAT
    px, py = p[0] * KM_PER_DEG_LON, p[1] * KM_PER_DEG_LAT
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy or 1e-9
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy)), u


def route_length(route):
    return sum(km(route[i], route[i + 1]) for i in range(len(route) - 1))


def point_at(route, frac):
    target = route_length(route) * frac
    for i in range(len(route) - 1):
        d = km(route[i], route[i + 1])
        if target <= d or i == len(route) - 2:
            u = 0 if d == 0 else min(1, target / d)
            a, b = route[i], route[i + 1]
            return (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))
        target -= d
    return route[-1]


def split_route(route, frac):
    """Return (travelled_path, remaining_path)."""
    target = route_length(route) * frac
    done = [route[0]]
    for i in range(len(route) - 1):
        d = km(route[i], route[i + 1])
        if target > d:
            done.append(route[i + 1])
            target -= d
        else:
            cut = point_at(route, frac)
            done.append(cut)
            return done, [cut] + list(route[i + 1:])
    return list(route), [route[-1]]


def route_hurdles(route_name, t, progress, reports=None):
    """Reports and slow stretches near the route, sorted by position."""
    route = ROUTES[route_name]
    reports = active_reports(t) if reports is None else reports
    total = route_length(route)
    hurdles = []

    def locate(p):
        best = (99, 0)
        run = 0
        for i in range(len(route) - 1):
            d, u = _project(p, route[i], route[i + 1])
            seg = km(route[i], route[i + 1])
            if d < best[0]:
                best = (d, (run + u * seg) / total)
            run += seg
        return best

    for r in reports:
        if r["type"] == "Rain alert":
            continue
        d, pos = locate((r["lon"], r["lat"]))
        if d <= 0.8:
            hurdles.append(dict(kind=r["type"], where=r["place"], pos=pos,
                                lon=r["lon"], lat=r["lat"], verified=r["verified"],
                                severity=r["severity"]))
    for road, pts in ROADS.items():
        c = congestion(road, t, reports)
        if c < 0.7:
            continue
        mid = pts[len(pts) // 2]
        d, pos = locate(mid)
        if d <= 0.6:
            hurdles.append(dict(kind="Heavy traffic", where=f"{road} ({speed(road, t, reports)} km/h)",
                                pos=pos, lon=mid[0], lat=mid[1], verified=True, severity=2))
    for h in hurdles:
        h["ahead_km"] = round((h["pos"] - progress) * total, 1)
        h["upcoming"] = h["pos"] >= progress
    return sorted(hurdles, key=lambda h: h["pos"])


def route_roads(route_name):
    """Names of roads that run along a route."""
    route = ROUTES[route_name]
    return {road for road, pts in ROADS.items()
            if any(_project(p, route[i], route[i + 1])[0] < 0.5
                   for p in pts for i in range(len(route) - 1))}


def route_eta(route_name, t, reports=None):
    """Very rough: average speed of roads the route touches."""
    route = ROUTES[route_name]
    reports = active_reports(t) if reports is None else reports
    speeds = []
    for road, pts in ROADS.items():
        near = any(_project(p, route[i], route[i + 1])[0] < 0.5
                   for p in pts for i in range(len(route) - 1))
        if near:
            speeds.append(speed(road, t, reports))
    v = sum(speeds) / len(speeds) if speeds else 30
    return int(route_length(route) / v * 60), int(v)


# --------------------------------------------------------------------------
# Predictive layer: disruptions that are known in advance
# --------------------------------------------------------------------------
CALENDAR = [
    dict(when="Tonight, 7 to 11 PM", what="Wedding baraats",
         where="Tonk Road, Ajmer Road, Mansarovar", roads=["Tonk Road", "Ajmer Road"],
         why="Auspicious wedding date on the calendar; many baraats expected", level="High"),
    dict(when="Saturday, 5 to 9 PM", what="Cricket match at SMS Stadium",
         where="JLN Marg and Tonk Road near the stadium", roads=["JLN Marg", "Tonk Road"],
         why="Scheduled match; crowd and parking spill onto roads", level="High"),
    dict(when="Sunday, 4 to 8 PM", what="Religious procession",
         where="Walled City, Tripolia Bazaar to Chaugan", roads=["MI Road", "Station Road"],
         why="Annual procession route; lanes closed in stages", level="Medium"),
    dict(when="Monday, 10 AM to 1 PM", what="Planned protest",
         where="Around Shaheed Smarak", roads=["MI Road"],
         why="Permission granted for a sit-in; diversions likely", level="Medium"),
]


# --------------------------------------------------------------------------
# Fusion: correlations, pulse score, plain-language summary
# --------------------------------------------------------------------------
def cause_chains(t_weather, t_traffic, t_reports):
    reports = active_reports(t_reports)
    chains = []
    for f in FLOWS:
        lvl = water_level(f, t_weather)
        if lvl < 0.45:
            continue
        up = rain(f["src"], t_weather - mid_lag(f))
        worst = min(f["roads"], key=lambda r: speed(r, t_traffic, reports))
        reported = any(r["type"] == "Waterlogging" and r["place"] == f["hotspot"] for r in reports)
        chains.append(dict(
            color="weather",
            steps=[f"{rain_label(up).capitalize()} in {f['src']} Jaipur about {int(mid_lag(f))} min ago",
                   f"Runoff heading to {f['hotspot']} (est. {f['lag'][0]} to {f['lag'][1]} min)",
                   f"{worst} slowed to {speed(worst, t_traffic, reports)} km/h"],
            strength="strong" if reported else "moderate",
            note="Waterlogging also reported by residents" if reported
            else "No resident report yet; based on rain and slope"))
    types = {r["type"]: r for r in reports}
    if "Power outage" in types and "Signal down" in types:
        chains.append(dict(
            color="reports",
            steps=["Power outage in Vaishali Nagar", "Traffic signal down at Queens Road junction",
                   f"Queens Road at {speed('Queens Road', t_traffic, reports)} km/h"],
            strength="strong", note="Outage feed and resident report line up in time and place"))
    if "VIP movement" in types:
        chains.append(dict(
            color="route",
            steps=["VIP movement advisory", "JLN Marg held in stretches",
                   f"JLN Marg at {speed('JLN Marg', t_traffic, reports)} km/h"],
            strength="strong", note="Official advisory"))
    return chains


def zone_stress(zone, t_weather, t_traffic, t_reports):
    reports = active_reports(t_reports)
    roads = [r for r in ROADS if road_zone(r) == zone]
    cong = sum(congestion(r, t_traffic, reports) for r in roads) / max(1, len(roads))
    reps = sum(r["severity"] for r in reports if r["zone"] == zone)
    return min(1.0, rain(zone, t_weather) / 30 * 0.35 + cong * 0.45 + reps / 12 * 0.3)


def pulse(t_weather, t_traffic, t_reports):
    stress = sum(zone_stress(z, t_weather, t_traffic, t_reports) for z in ZONES) / 4
    score = int(max(15, min(99, 100 - stress * 90)))
    label = ("Calm" if score >= 75 else "Busy" if score >= 58
             else "Stressed" if score >= 42 else "Critical")
    return score, label, stress


def summary(t_weather, t_traffic, t_reports, delayed=None):
    reports = active_reports(t_reports)
    wettest = max(ZONES, key=lambda z: rain(z, t_weather))
    r = rain(wettest, t_weather)
    parts = []
    parts.append("Dry across the city." if r < 1 else
                 f"{rain_label(r).capitalize()} in {wettest} Jaipur ({r} mm/hr).")
    slow = sorted(ROADS, key=lambda x: speed(x, t_traffic, reports))
    slow = [x for x in slow if congestion(x, t_traffic, reports) >= 0.6]
    if slow:
        parts.append(f"{len(slow)} roads are slow, worst is {slow[0]} at "
                     f"{speed(slow[0], t_traffic, reports)} km/h.")
    else:
        parts.append("Roads are moving normally.")
    wl = [x["place"] for x in reports if x["type"] == "Waterlogging"]
    if wl:
        parts.append(f"Waterlogging reported at {', '.join(wl[:2])}.")
    chains = cause_chains(t_weather, t_traffic, t_reports)
    if chains:
        parts.append("Some of this looks connected; see possible links.")
    if delayed:
        parts.append(f"{delayed} data is 12 min old.")
    return " ".join(parts)


def timeseries(zone, t_now, step=5):
    """Rows for trend charts: rain, avg speed, active reports per zone."""
    rows = []
    zones = ZONES if zone == "All Jaipur" else [zone]
    for t in range(0, int(t_now) + 1, step):
        reports = active_reports(t)
        row = {"time": clock(t)}
        for z in zones:
            roads = [r for r in ROADS if road_zone(r) == z]
            row[f"rain_{z}"] = rain(z, t)
            row[f"speed_{z}"] = round(sum(speed(r, t, reports) for r in roads) / max(1, len(roads)), 1)
            row[f"reports_{z}"] = sum(1 for r in reports if r["zone"] == z)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# Civic contributors (leaderboard) - handles only, no real names
# --------------------------------------------------------------------------
CONTRIBUTORS = [
    # handle, ward/area, verified, total, badge
    ("pinkcity_rider", "Walled City", 48, 52, "Monsoon scout"),
    ("mansarovar_mom", "Mansarovar", 41, 44, "Waterlogging watch"),
    ("ward42_watch", "Vaishali Nagar", 37, 41, "Signal saver"),
    ("jhotwara_updates", "Jhotwara", 33, 39, "Monsoon scout"),
    ("vkia_nightshift", "Vidhyadhar Nagar", 29, 31, "Night owl"),
    ("tonkroad_tales", "Tonk Road", 26, 34, "Baraat spotter"),
    ("sodala_scout", "Sodala", 22, 25, "Rising reporter"),
    ("galta_gate_guy", "Galta Gate", 19, 27, "Rising reporter"),
    ("ajmerroad_daily", "Ajmer Road", 15, 23, "Commuter"),
    ("amer_side_guide", "Amer", 11, 12, "Heritage lookout"),
]


def leaderboard():
    rows = []
    for handle, area, ver, tot, badge in CONTRIBUTORS:
        accuracy = ver / tot
        points = ver * 10 + (tot - ver) * 1
        trust = round(min(1.0, 0.5 * accuracy + 0.5 * min(1, ver / 50)), 2)
        rows.append(dict(handle=handle, area=area, verified=ver, submitted=tot,
                         accuracy=round(accuracy * 100), points=points, trust=trust, badge=badge))
    return sorted(rows, key=lambda r: -r["points"])


# --------------------------------------------------------------------------
# AI Navi - grounded, rule-based answers from current feed state.
# (Swap `answer` for an LLM call later; pass it the same facts as context.)
# --------------------------------------------------------------------------
KEYS = {
    "weather": ["weather", "rain", "baarish", "barish", "mausam", "aqi", "water",
                "paani", "flood", "temperature", "garmi"],
    "route": ["route", "raasta", "rasta", "way", "commute", "reach", "trip",
              "jaana", "jana", "drive", "safar"],
    "traffic": ["traffic", "jam", "slow", "speed", "road"],
    "incidents": ["incident", "report", "accident", "outage", "bijli", "power",
                  "happened", "kya hua", "signal", "police", "vip", "tree"],
    "upcoming": ["tomorrow", "later", "upcoming", "baraat", "match", "event", "kal",
                 "weekend", "saturday", "sunday", "plan"],
    "why": ["why", "kyun", "kyon", "cause", "reason", "connected", "link"],
}


def _matches(q, key):
    return any(k in q for k in KEYS[key])


def answer(question, t_weather, t_traffic, t_reports, route_name, progress):
    q = question.lower()
    reports = active_reports(t_reports)
    zone = next((z for z in ZONES if z.lower() in q), None)
    out = []

    if _matches(q, "weather"):
        zs = [zone] if zone else ZONES
        lines = [f"{z}: {rain_label(rain(z, t_weather))}, {rain(z, t_weather)} mm/hr, "
                 f"{weather(z, t_weather)['temp']} C, AQI {weather(z, t_weather)['aqi']}" for z in zs]
        out.append("Weather right now:\n- " + "\n- ".join(lines))
        flows = [f for f in FLOWS if water_level(f, t_weather) >= 0.35 and (not zone or f["src"] == zone or f["zone"] == zone)]
        if flows:
            out.append("Where the water is heading (estimates):\n- " + "\n- ".join(
                f"From {f['src']} to {f['hotspot']} in about {f['lag'][0]} to {f['lag'][1]} min, "
                f"risk {risk_label(water_level(f, t_weather))}; watch {', '.join(f['roads'])}" for f in flows))

    if _matches(q, "route") or (_matches(q, "traffic") and not zone):
        hs = [h for h in route_hurdles(route_name, t_traffic, progress / 100, reports) if h["upcoming"]]
        eta, v = route_eta(route_name, t_traffic, reports)
        if hs:
            out.append(f"On {route_name} (about {eta} min at {v} km/h), coming up:\n- " + "\n- ".join(
                f"{h['kind']} at {h['where']}, {max(0, h['ahead_km'])} km ahead"
                + ("" if h["verified"] else " (unverified)") for h in hs))
        else:
            out.append(f"{route_name} looks clear ahead, about {eta} min at {v} km/h.")

    if _matches(q, "traffic") and zone:
        roads = [r for r in ROADS if road_zone(r) == zone]
        out.append(f"Roads in {zone} Jaipur:\n- " + "\n- ".join(
            f"{r}: {speed(r, t_traffic, reports)} km/h" for r in roads))

    if _matches(q, "incidents"):
        rs = [r for r in reports if not zone or r["zone"] == zone]
        if rs:
            out.append("Active reports:\n- " + "\n- ".join(
                f"{r['type']} at {r['place']} ({r['ago']} min ago, "
                f"{'verified' if r['verified'] else 'unverified'}, via {r['source']})" for r in rs[:6]))
        else:
            out.append("No active reports" + (f" in {zone} Jaipur." if zone else "."))

    if _matches(q, "upcoming"):
        out.append("Known in advance:\n- " + "\n- ".join(
            f"{c['when']}: {c['what']} around {c['where']}" for c in CALENDAR))

    if _matches(q, "why") or (not out and zone is None and "?" in q and len(q) > 60):
        chains = cause_chains(t_weather, t_traffic, t_reports)
        if chains:
            out.append("Possible links (not confirmed causes):\n- " + "\n- ".join(
                " then ".join(c["steps"]) + f" [{c['strength']} match]" for c in chains))
        else:
            out.append("I don't see linked events in the feeds right now.")

    if not out and zone:
        z = zone
        out.append(f"{z} Jaipur: {rain_label(rain(z, t_weather))}, "
                   f"{sum(1 for r in reports if r['zone'] == z)} active reports, stress "
                   f"{int(zone_stress(z, t_weather, t_traffic, t_reports) * 100)}/100.")

    if not out:
        out.append(summary(t_weather, t_traffic, t_reports))
        out.append("You can ask me about weather, your route, traffic in an area, incidents, "
                   "upcoming events, or why something is happening. Hindi words like "
                   "baarish, raasta and kal work too.")

    out.append(f"Based only on the live feeds as of {clock(t_reports)}. Links are possible, not proven.")
    return "\n\n".join(out)
