"""
Turns a world state (live or replay) into the single JSON "snapshot" the
frontend renders. This is the heart of the fusion: every panel in the UI
reads from here, so the map, cards, charts and AI Navi never disagree.
"""
from . import analytics, fusion, routing, trust
from . import city as C


def evaluate_rules(rules, snap):
    """User alert rules -> list of triggered alerts."""
    fired = []
    zones = {z["zone"]: z for z in snap["zones"]}
    roads = {r["name"]: r for r in snap["roads"]}
    for rule in rules:
        m, target, thr = rule["metric"], rule["target"], float(rule["threshold"])
        msg = None
        if m == "rain" and target in zones and zones[target]["rain"] >= thr:
            msg = f"Rain in {target} Jaipur is {zones[target]['rain']} mm/hr (your limit {thr:g})"
        elif m == "speed" and target in roads and roads[target]["speed"] <= thr:
            msg = f"{target} is down to {roads[target]['speed']} km/h (your limit {thr:g})"
        elif m == "pulse" and snap["pulse"]["score"] <= thr:
            msg = f"Jaipur pulse dropped to {snap['pulse']['score']} (your limit {thr:g})"
        elif m == "report":
            hits = [r for r in snap["reports"] if r["type"] == target and r["verified"]]
            if len(hits) >= max(1, thr):
                msg = f"{len(hits)} verified {target.lower()} report(s): {hits[0]['place']}"
        if msg:
            fired.append(dict(rule_id=rule.get("id"), label=rule.get("label") or msg, message=msg))
    return fired


def build(state, area="All Jaipur", route=None, progress=0.2, rules=(), board=None):
    board = board if board is not None else trust.leaderboard(C.CONTRIBUTORS_SEED)
    trust_by = {b["handle"]: b["trust"] for b in board}
    rain_at, roads, levels = state["rain_at"], state["roads"], state["levels"]

    # --- reports + verification
    reports = []
    for r in state["reports"]:
        a = trust.assess(r, state["reports"], rain_at, lambda h: trust_by.get(h, 0.3))
        reports.append({**r, **a, "color": C.REPORT_COLORS.get(r["type"], [110, 110, 110])})
    reports.sort(key=lambda r: (r["status"] != "active", -r["severity"], r["ago"]))
    active = [r for r in reports if r["status"] == "active"]

    # --- zones
    zones = []
    stresses = {}
    for z in C.ZONES:
        w = state["weather"][z]
        s = fusion.zone_stress(z, w["rain"], roads, active)
        stresses[z] = s
        f = (state.get("forecast") or {}).get(z)
        zones.append(dict(zone=z, **w, rain_text=C.rain_label(w["rain"]), stress=s,
                          centroid=list(C.ZONE_CENTROIDS[z]), polygon=C.zone_polygon(z), forecast=f))

    # --- roads for the map
    road_list = [dict(**m, path=[list(p) for p in C.ROADS[name]], color=C.traffic_color(m["congestion"]))
                 for name, m in roads.items()]

    chains = fusion.cause_chains(levels, roads, active)
    chains = analytics.attach_evidence(chains, state["points"], state["step_min"])
    pulse = fusion.pulse(stresses)
    route_name = route if route in C.ROUTES else next(iter(C.ROUTES))

    snap = dict(
        meta=dict(mode=state["mode"], clock=state["clock"], t=state.get("t"), area=area,
                  delayed=state.get("delayed"), weather_ok=state.get("weather_ok", True)),
        feeds=state["feeds"],
        pulse=pulse,
        summary=fusion.summary(state["weather"], roads, active, chains, state.get("delayed"),
                               state.get("forecast"), state.get("weather_ok", True)),
        zones=zones,
        roads=road_list,
        flows=levels,
        reports=reports,
        chains=chains,
        anomalies=analytics.anomalies(state["points"]),
        route=routing.block(route_name, max(0.0, min(1.0, progress)), active, roads),
        timeseries=analytics.zone_series(state["points"], area),
        calendar=C.CALENDAR,
        leaderboard=board,
    )
    snap["alerts"] = evaluate_rules(rules, snap)
    return snap
