"""
Fusion engine. Pure functions, no I/O, so the same logic runs for the
live city and for the replay scenario.

Inputs are already normalized:
  rain_at(zone, minutes_ago) -> mm/hr
  reports: list of normalized report dicts
Outputs are plain dicts ready for the API.
"""
from . import city as C


def flow_levels(rain_at):
    """Waterlogging risk (0..1) at each downstream hotspot."""
    out = []
    for f in C.FLOWS:
        upstream = rain_at(f["src"], C.mid_lag(f))
        local = rain_at(f["zone"], 0)
        level = round(min(1.0, (upstream * f["factor"] + local * 0.6) / 22), 2)
        out.append({**f, "level": level, "risk": C.risk_label(level),
                    "upstream_rain": round(upstream, 1),
                    "src_pos": list(C.ZONE_CENTROIDS[f["src"]])})
    return out


def road_metrics(minute_of_day, levels, reports, overrides=None):
    """Congestion and speed per road.

    Model = base load + rush hour + nearby waterlogging + incidents on the road.
    If a measured speed exists (e.g. TomTom), it replaces the model value.
    """
    rush = C.rush_factor(minute_of_day)
    overrides = overrides or {}
    out = {}
    for road in C.ROADS:
        water = max([l["level"] for l in levels if road in l["roads"]] or [0])
        incident = sum(0.07 * r["severity"] for r in reports
                       if r.get("road") == road and r["type"] != "Rain alert"
                       and r.get("status", "active") == "active")
        if road in overrides:
            current, free = overrides[road]
            cong = max(0.0, min(0.95, 1 - current / max(free, 1)))
            spd, source = int(round(current)), "measured"
        else:
            cong = min(0.9, C.ROAD_BASE[road] + rush + 0.28 * water + incident)
            spd, source = int(round(48 * (1 - cong) + 4)), "model"
        out[road] = dict(name=road, congestion=round(cong, 2), speed=spd,
                         zone=C.road_zone(road), source=source, water=water)
    return out


def zone_stress(zone, rain_now, roads, reports):
    rs = [r for r in roads.values() if r["zone"] == zone]
    cong = sum(r["congestion"] for r in rs) / max(1, len(rs))
    reps = sum(r["severity"] for r in reports if r["zone"] == zone and r.get("status", "active") == "active")
    return round(min(1.0, rain_now / 30 * 0.35 + cong * 0.45 + reps / 12 * 0.3), 3)


def pulse(stresses):
    stress = sum(stresses.values()) / max(1, len(stresses))
    score = int(max(15, min(99, 100 - stress * 90)))
    state = ("Calm" if score >= 75 else "Busy" if score >= 58
             else "Stressed" if score >= 42 else "Critical")
    return dict(score=score, state=state, stress=round(stress, 3))


def cause_chains(levels, roads, reports):
    """Rule-based 'possible links' between feeds. Evidence is attached later
    by analytics (lagged correlation)."""
    chains = []
    active = [r for r in reports if r.get("status", "active") == "active"]
    for f in levels:
        if f["level"] < 0.45:
            continue
        worst = min(f["roads"], key=lambda r: roads[r]["speed"])
        reported = any(r["type"] == "Waterlogging" and (r["place"] == f["hotspot"] or
                       C.km((r["lon"], r["lat"]), (f["lon"], f["lat"])) < 1.0) for r in active)
        chains.append(dict(
            id=f"flow:{f['id']}", color="weather", flow=f["id"], road=worst, src=f["src"],
            steps=[f"{C.rain_label(f['upstream_rain']).capitalize()} in {f['src']} Jaipur "
                   f"about {int(C.mid_lag(f))} min ago",
                   f"Runoff heading to {f['hotspot']} (est. {f['lag'][0]} to {f['lag'][1]} min)",
                   f"{worst} slowed to {roads[worst]['speed']} km/h"],
            strength="strong" if reported else "moderate",
            note="Waterlogging also reported by residents" if reported
            else "No resident report yet; based on rain and slope"))
    by_type = {}
    for r in active:
        by_type.setdefault(r["type"], []).append(r)
    for sig in by_type.get("Signal down", []):
        outage = next((o for o in by_type.get("Power outage", []) if o["zone"] == sig["zone"]), None)
        if outage:
            road = sig.get("road") or "the area"
            spd = roads[road]["speed"] if road in roads else None
            chains.append(dict(
                id=f"power:{sig['id']}", color="reports", road=road,
                steps=[f"Power outage at {outage['place']}", f"Traffic signal down at {sig['place']}",
                       f"{road} at {spd} km/h" if spd else "Traffic affected nearby"],
                strength="strong", note="Outage and signal report line up in time and area"))
    for vip in by_type.get("VIP movement", []):
        road = vip.get("road")
        if road in roads:
            chains.append(dict(
                id=f"vip:{vip['id']}", color="route", road=road,
                steps=["VIP movement advisory", f"{road} held in stretches",
                       f"{road} at {roads[road]['speed']} km/h"],
                strength="strong" if vip["source"] != "Citizen" else "moderate",
                note="Official advisory" if vip["source"] != "Citizen" else "Resident report"))
    return chains


def summary(weather, roads, reports, chains, delayed=None, forecast=None, weather_ok=True):
    parts = []
    if not weather_ok:
        parts.append("Weather feed is unavailable right now.")
    else:
        wettest = max(weather, key=lambda z: weather[z]["rain"])
        r = weather[wettest]["rain"]
        parts.append("Dry across the city." if r < 0.5 else
                     f"{C.rain_label(r).capitalize()} in {wettest} Jaipur ({r} mm/hr).")
        if forecast:
            coming = [z for z, f in forecast.items() if f.get("next_60", 0) >= 2 and weather[z]["rain"] < 1]
            if coming:
                parts.append(f"Rain likely within the hour in {', '.join(coming)}.")
    slow = sorted((r for r in roads.values() if r["congestion"] >= 0.6), key=lambda r: r["speed"])
    if slow:
        parts.append(f"{len(slow)} roads are slow, worst is {slow[0]['name']} at {slow[0]['speed']} km/h.")
    else:
        parts.append("Roads are moving normally.")
    wl = [x["place"] for x in reports if x["type"] == "Waterlogging" and x.get("status", "active") == "active"]
    if wl:
        parts.append(f"Waterlogging reported at {', '.join(wl[:2])}.")
    if chains:
        parts.append("Some of this looks connected; see possible links.")
    if delayed:
        parts.append(f"{delayed} data is 12 min old.")
    return " ".join(parts)
