"""
Statistics that back up the fusion rules with evidence from the data.

1. Robust anomaly detection: compares the latest value of each stream to
   its own recent history using median and MAD (median absolute deviation),
   which is not thrown off by a few extreme points the way mean/stdev is.
2. Lagged correlation: for each rain -> road link, finds the delay at which
   upstream rain and road speed move together most strongly. This is what
   turns "these happened near each other" into "this pattern repeats with a
   ~40 min delay" - still a correlation, never claimed as proof of cause.
"""
import math
import statistics

from . import city as C


def robust_z(history, latest, floor):
    med = statistics.median(history)
    mad = statistics.median(abs(x - med) for x in history)
    scale = max(1.4826 * mad, floor)
    return (latest - med) / scale, med


def anomalies(points, min_history=8, window=24):
    """points: list of {'label','rain':{zone:v},'speed':{road:v},'reports':{zone:n}} oldest first."""
    if len(points) < min_history + 1:
        return []
    past, now = points[-(window + 1):-1], points[-1]
    out = []
    for road, v in now["speed"].items():
        hist = [p["speed"][road] for p in past if road in p["speed"]]
        if len(hist) < min_history:
            continue
        z, med = robust_z(hist, v, floor=2.0)
        if z <= -3 and med - v >= 12:
            out.append(dict(kind="speed", target=road, value=v, typical=round(med), z=round(z, 1),
                            message=f"{road} is unusually slow: {v} km/h vs a typical {round(med)} km/h"))
    for zone, v in now["rain"].items():
        hist = [p["rain"][zone] for p in past if zone in p["rain"]]
        if len(hist) < min_history:
            continue
        z, med = robust_z(hist, v, floor=1.0)
        if z >= 3 and v >= 3:
            out.append(dict(kind="rain", target=zone, value=v, typical=round(med, 1), z=round(z, 1),
                            message=f"Rain in {zone} Jaipur jumped to {v} mm/hr (usually {round(med, 1)})"))
    for zone, v in now["reports"].items():
        hist = [p["reports"][zone] for p in past if zone in p["reports"]]
        if len(hist) < min_history:
            continue
        z, med = robust_z(hist, v, floor=1.0)
        if z >= 2.5 and v >= 3:
            out.append(dict(kind="reports", target=zone, value=v, typical=round(med), z=round(z, 1),
                            message=f"Report spike in {zone} Jaipur: {v} active vs usually {round(med)}"))
    return sorted(out, key=lambda a: -abs(a["z"]))[:4]


def pearson(x, y):
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx < 1e-9 or sy < 1e-9:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def best_lag(cause, effect, step_min, max_lag_min=90, min_points=6):
    """Lag (minutes) at which effect correlates most negatively with earlier cause."""
    best = (0, 0.0, 0)
    for k in range(0, max_lag_min // step_min + 1):
        x = cause[:len(cause) - k] if k else cause
        y = effect[k:]
        n = min(len(x), len(y))
        if n < min_points:
            break
        r = pearson(x[:n], y[:n])
        if r < best[1]:
            best = (k * step_min, r, n)
    return best


def attach_evidence(chains, points, step_min):
    """Add a data check to each rain -> road chain."""
    if len(points) < 8:
        return chains
    for ch in chains:
        if not ch["id"].startswith("flow:"):
            continue
        rain = [p["rain"].get(ch["src"], 0) for p in points]
        speed = [p["speed"].get(ch["road"], 0) for p in points]
        lag, r, n = best_lag(rain, speed, step_min)
        if r <= -0.5:
            ch["evidence"] = dict(lag_min=lag, r=round(r, 2), points=n,
                                  text=f"Data check: {ch['road']} speed tends to drop about {lag} min "
                                       f"after rain in {ch['src']} (correlation {r:.2f} over {n} readings)")
    return chains


def zone_series(points, area):
    """Chart rows for the frontend: rain / avg speed / reports per zone."""
    zones = C.ZONES if area == "All Jaipur" else [area]
    rows = []
    for p in points:
        row = {"time": p["label"]}
        for z in zones:
            speeds = [v for road, v in p["speed"].items() if C.road_zone(road) == z]
            row[f"rain_{z}"] = p["rain"].get(z, 0)
            row[f"speed_{z}"] = round(sum(speeds) / len(speeds), 1) if speeds else None
            row[f"reports_{z}"] = p["reports"].get(z, 0)
        rows.append(row)
    return rows
