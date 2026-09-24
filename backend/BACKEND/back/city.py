"""
Static model of Jaipur used by every other module: zones, roads, drainage
flows, routes, named places and known-in-advance events.

This plays the role of CityPulse's "Geospatial Data Infrastructure":
it answers "what is where" so the rest of the system can ask
"which streams / roads / reports are in this area?".
"""
import math
from datetime import timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

CENTER = (75.800, 26.905)                      # (lon, lat)
BBOX = dict(w=75.70, e=75.90, s=26.81, n=27.00)
ZONES = ["North", "East", "South", "West"]
ZONE_CENTROIDS = {
    "North": (75.800, 26.965),
    "East": (75.858, 26.905),
    "South": (75.800, 26.842),
    "West": (75.742, 26.905),
}
KM_PER_DEG_LON = 99.3
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


def km(a, b):
    return math.hypot((a[0] - b[0]) * KM_PER_DEG_LON, (a[1] - b[1]) * KM_PER_DEG_LAT)


def in_bbox(lon, lat, w, s, e, n):
    return w <= lon <= e and s <= lat <= n


# ------------------------------------------------------------------ drainage
# Hills lie to the north; the city drains broadly southward. Lags are
# ESTIMATES (ranges), always presented to users as such.
FLOWS = [
    dict(id="n-e", src="North", hotspot="Johari Bazaar & Badi Chaupar", zone="East",
         lon=75.8270, lat=26.9196, lag=(30, 45), roads=["MI Road", "Agra Road"], factor=0.9),
    dict(id="n-w", src="North", hotspot="Jhotwara underpass", zone="West",
         lon=75.7400, lat=26.9480, lag=(40, 55), roads=["Sikar Road", "Queens Road"], factor=0.7),
    dict(id="e-s", src="East", hotspot="Gopalpura, Tonk Road", zone="South",
         lon=75.7920, lat=26.8660, lag=(45, 70), roads=["Tonk Road", "JLN Marg"], factor=1.1),
    dict(id="w-s", src="West", hotspot="Mansarovar metro stretch", zone="South",
         lon=75.7621, lat=26.8505, lag=(40, 60), roads=["New Sanganer Road", "Ajmer Road"], factor=1.2),
]


def mid_lag(flow):
    return sum(flow["lag"]) / 2


# ------------------------------------------------------------------ roads
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
FREE_FLOW_KMH = 52


def road_mid(name):
    pts = ROADS[name]
    return pts[len(pts) // 2]


def road_zone(name):
    pts = ROADS[name]
    return zone_of(sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


# ------------------------------------------------------------------ places
# Named spots residents can pick when reporting (no free-text GPS needed).
PLACES = {
    "Johari Bazaar": (75.8270, 26.9196, "MI Road"),
    "Hawa Mahal": (75.8267, 26.9239, "Station Road"),
    "Chandpole": (75.8140, 26.9250, "Station Road"),
    "Sindhi Camp": (75.8000, 26.9230, "Station Road"),
    "Jaipur Junction": (75.7878, 26.9196, "Station Road"),
    "MI Road, Panch Batti": (75.8050, 26.9150, "MI Road"),
    "Galta Gate": (75.8450, 26.9180, "Agra Road"),
    "Amer Fort": (75.8513, 26.9855, "Amer Road"),
    "Jal Mahal": (75.8460, 26.9530, "Amer Road"),
    "Vidhyadhar Nagar": (75.7820, 26.9560, "Sikar Road"),
    "Jhotwara": (75.7400, 26.9480, "Sikar Road"),
    "Vaishali Nagar": (75.7437, 26.9117, "Queens Road"),
    "Queens Road junction": (75.7650, 26.9120, "Queens Road"),
    "Sodala": (75.7700, 26.9030, "Ajmer Road"),
    "200 ft bypass": (75.7300, 26.8960, "Ajmer Road"),
    "Mansarovar": (75.7621, 26.8505, "New Sanganer Road"),
    "Gopalpura": (75.7920, 26.8660, "Tonk Road"),
    "Jawahar Circle": (75.7920, 26.8420, "Tonk Road"),
    "SMS Stadium": (75.8070, 26.8940, "JLN Marg"),
    "Malviya Nagar": (75.8243, 26.8549, "JLN Marg"),
    "Airport": (75.8122, 26.8242, "Tonk Road"),
}

# ------------------------------------------------------------------ routes
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

# ------------------------------------------------------------------ reports
REPORT_TYPES = ["Waterlogging", "Traffic jam", "Accident", "Power outage", "Signal down",
                "Tree fall", "Police naka", "VIP movement", "Baraat", "Procession",
                "Road work", "Stray cattle", "Protest", "Rain alert"]
DURATION_MIN = {"Rain alert": 90, "Waterlogging": 75, "VIP movement": 30, "Baraat": 50,
                "Power outage": 60, "Signal down": 55, "Procession": 90, "Protest": 120,
                "Road work": 240}
REPORT_COLORS = {
    "Waterlogging": [28, 143, 176], "Rain alert": [70, 110, 220],
    "Power outage": [123, 63, 196], "Signal down": [123, 63, 196],
    "VIP movement": [224, 69, 123], "Baraat": [240, 138, 36], "Procession": [240, 138, 36],
    "Police naka": [60, 60, 110], "Tree fall": [46, 158, 106], "Protest": [180, 60, 120],
    "Stray cattle": [150, 110, 60], "Road work": [200, 150, 30],
    "Accident": [210, 40, 50], "Traffic jam": [224, 40, 80],
}

# ------------------------------------------------------------------ calendar
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

# ------------------------------------------------------------------ contributors seed
CONTRIBUTORS_SEED = [
    # handle, area, verified, submitted, badge
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


# ------------------------------------------------------------------ helpers
def rain_label(r):
    if r >= 15:
        return "heavy rain"
    if r >= 6:
        return "moderate rain"
    if r >= 1:
        return "light rain"
    if r > 0:
        return "drizzle"
    return "dry"


def risk_label(x):
    return "high" if x >= 0.65 else "medium" if x >= 0.35 else "low"


def traffic_color(c):
    if c >= 0.7:
        return [224, 40, 80]
    if c >= 0.5:
        return [240, 138, 36]
    return [46, 158, 106]


def rush_factor(minute_of_day):
    """Typical Jaipur weekday rush: morning 9-11, evening 5:30-8:30."""
    morning = 0.16 * math.exp(-((minute_of_day - 600) / 55) ** 2)
    evening = 0.22 * math.exp(-((minute_of_day - 1140) / 60) ** 2)
    return morning + evening
