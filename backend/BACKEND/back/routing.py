"""Route helpers: where you are, what's ahead, and how long it takes."""
import math

from . import city as C


def _project(p, a, b):
    """Distance (km) from point p to segment ab, and fraction along ab."""
    ax, ay = a[0] * C.KM_PER_DEG_LON, a[1] * C.KM_PER_DEG_LAT
    bx, by = b[0] * C.KM_PER_DEG_LON, b[1] * C.KM_PER_DEG_LAT
    px, py = p[0] * C.KM_PER_DEG_LON, p[1] * C.KM_PER_DEG_LAT
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy or 1e-9
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy)), u


def length(route):
    return sum(C.km(route[i], route[i + 1]) for i in range(len(route) - 1))


def point_at(route, frac):
    target = length(route) * frac
    for i in range(len(route) - 1):
        d = C.km(route[i], route[i + 1])
        if target <= d or i == len(route) - 2:
            u = 0 if d == 0 else min(1, target / d)
            a, b = route[i], route[i + 1]
            return (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))
        target -= d
    return route[-1]


def split(route, frac):
    """(travelled_path, remaining_path)"""
    target = length(route) * frac
    done = [route[0]]
    for i in range(len(route) - 1):
        d = C.km(route[i], route[i + 1])
        if target > d:
            done.append(route[i + 1])
            target -= d
        else:
            cut = point_at(route, frac)
            done.append(cut)
            return done, [cut] + list(route[i + 1:])
    return list(route), [route[-1]]


def locate(route, p):
    """(distance_km_from_route, fraction_along_route)"""
    total = length(route) or 1e-9
    best, run = (99.0, 0.0), 0.0
    for i in range(len(route) - 1):
        d, u = _project(p, route[i], route[i + 1])
        seg = C.km(route[i], route[i + 1])
        if d < best[0]:
            best = (d, (run + u * seg) / total)
        run += seg
    return best


def roads_on(route_name):
    route = C.ROUTES[route_name]
    return sorted(road for road, pts in C.ROADS.items()
                  if any(_project(p, route[i], route[i + 1])[0] < 0.5
                         for p in pts for i in range(len(route) - 1)))


def hurdles(route_name, progress, reports, roads):
    route = C.ROUTES[route_name]
    total = length(route)
    out = []
    for r in reports:
        if r["type"] == "Rain alert" or r.get("status", "active") != "active":
            continue
        d, pos = locate(route, (r["lon"], r["lat"]))
        if d <= 0.8:
            out.append(dict(kind=r["type"], where=r["place"], pos=pos, lon=r["lon"], lat=r["lat"],
                            verified=r.get("verified", False), severity=r["severity"]))
    for name, m in roads.items():
        if m["congestion"] < 0.7:
            continue
        mid = C.road_mid(name)
        d, pos = locate(route, mid)
        if d <= 0.6:
            out.append(dict(kind="Heavy traffic", where=f"{name} ({m['speed']} km/h)", pos=pos,
                            lon=mid[0], lat=mid[1], verified=True, severity=2))
    for h in out:
        h["ahead_km"] = round((h["pos"] - progress) * total, 1)
        h["upcoming"] = h["pos"] >= progress
    return sorted(out, key=lambda h: h["pos"])


def eta(route_name, roads):
    route = C.ROUTES[route_name]
    speeds = [roads[r]["speed"] for r in roads_on(route_name) if r in roads]
    v = sum(speeds) / len(speeds) if speeds else 30
    return int(length(route) / v * 60), int(v)


def block(route_name, progress, reports, roads):
    """Everything the frontend needs for Route mode."""
    route = C.ROUTES[route_name]
    done, ahead = split(route, progress)
    minutes, v = eta(route_name, roads)
    near = set(roads_on(route_name))
    plan = [c for c in C.CALENDAR if set(c["roads"]) & near][:2] or C.CALENDAR[:1]
    hs = hurdles(route_name, progress, reports, roads)
    return dict(name=route_name, progress=progress, path=[list(p) for p in route],
                done=[list(p) for p in done], ahead=[list(p) for p in ahead],
                here=list(point_at(route, progress)), length_km=round(length(route), 1),
                eta_total=minutes, eta_left=int(minutes * (1 - progress)), avg_speed=v,
                roads=sorted(near), hurdles=hs, plan=plan)
