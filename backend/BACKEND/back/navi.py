"""
AI Navi. Answers questions using ONLY the current snapshot.

Default engine: rules (works offline, instant, never makes things up).
Optional: if ANTHROPIC_API_KEY is set, the same facts are sent to Claude,
which is told to answer only from them. Any failure falls back to rules.
"""
import json
import os

from . import city as C

KEYS = {
    "weather": ["weather", "rain", "baarish", "barish", "mausam", "aqi", "water", "paani", "pani",
                "flood", "temperature", "garmi", "air", "pollution"],
    "route": ["route", "raasta", "rasta", "way", "commute", "reach", "trip", "jaana", "jana",
              "drive", "safar", "my road"],
    "traffic": ["traffic", "jam", "slow", "speed", "road"],
    "incidents": ["incident", "report", "accident", "outage", "bijli", "power", "happened",
                  "kya hua", "signal", "police", "vip", "tree", "baraat"],
    "upcoming": ["tomorrow", "later", "upcoming", "match", "event", "kal", "weekend",
                 "saturday", "sunday", "plan", "advance"],
    "why": ["why", "kyun", "kyon", "cause", "reason", "connected", "link"],
    "unusual": ["unusual", "anomal", "strange", "odd", "ajeeb"],
}


def _has(q, key):
    return any(k in q for k in KEYS[key])


def answer_rules(question, snap):
    q = question.lower()
    zones = {z["zone"]: z for z in snap["zones"]}
    roads = {r["name"]: r for r in snap["roads"]}
    active = [r for r in snap["reports"] if r["status"] == "active"]
    zone = next((z for z in C.ZONES if z.lower() in q), None)
    road = next((r for r in C.ROADS if r.lower() in q or r.lower().replace(" road", "") + " road" in q), None)
    out = []

    if road:
        m = roads[road]
        lines = [f"{road}: {m['speed']} km/h, {int(m['congestion'] * 100)}% congested"
                 + (" (measured)" if m["source"] == "measured" else "")]
        for f in snap["flows"]:
            if road in f["roads"] and f["level"] >= 0.35:
                lines.append(f"Runoff from {f['src']} is heading to {f['hotspot']} "
                             f"(about {f['lag'][0]} to {f['lag'][1]} min, risk {f['risk']})")
        for r in active:
            if r.get("road") == road:
                lines.append(f"{r['type']} at {r['place']}, {r['ago']} min ago "
                             f"({'verified' if r['verified'] else 'unverified'})")
        z = zones[m["zone"]]
        lines.append(f"Weather there: {z['rain_text']}, {z['rain']} mm/hr")
        out.append("\n- ".join([f"About {road}:"] + lines))

    if _has(q, "weather") and not road:
        zs = [zone] if zone else C.ZONES
        lines = []
        for z in zs:
            w = zones[z]
            extra = f", {w['temp']} C" if w.get("temp") is not None else ""
            extra += f", AQI {w['aqi']}" if w.get("aqi") is not None else ""
            fc = w.get("forecast") or {}
            if fc.get("next_60", 0) >= 1:
                extra += f"; up to {fc['next_60']} mm/hr expected within the hour"
            lines.append(f"{z}: {w['rain_text']}, {w['rain']} mm/hr{extra}")
        out.append("Weather right now:\n- " + "\n- ".join(lines))
        flows = [f for f in snap["flows"] if f["level"] >= 0.35 and (not zone or zone in (f["src"], f["zone"]))]
        if flows:
            out.append("Where the water is heading (estimates):\n- " + "\n- ".join(
                f"From {f['src']} to {f['hotspot']} in about {f['lag'][0]} to {f['lag'][1]} min, "
                f"risk {f['risk']}; watch {', '.join(f['roads'])}" for f in flows))

    if _has(q, "route") or (_has(q, "traffic") and not zone and not road):
        rt = snap["route"]
        ahead = [h for h in rt["hurdles"] if h["upcoming"]]
        if ahead:
            out.append(f"On {rt['name']} (about {rt['eta_left']} min left at {rt['avg_speed']} km/h), "
                       "coming up:\n- " + "\n- ".join(
                           f"{h['kind']} at {h['where']}, {max(0, h['ahead_km'])} km ahead"
                           + ("" if h["verified"] else " (unverified)") for h in ahead))
        else:
            out.append(f"{rt['name']} looks clear ahead, about {rt['eta_left']} min left.")

    if _has(q, "traffic") and zone:
        rs = sorted((r for r in snap["roads"] if r["zone"] == zone), key=lambda r: r["speed"])
        out.append(f"Roads in {zone} Jaipur:\n- " + "\n- ".join(f"{r['name']}: {r['speed']} km/h" for r in rs))

    if _has(q, "incidents") and not road:
        rs = [r for r in active if not zone or r["zone"] == zone]
        out.append(("Active reports:\n- " + "\n- ".join(
            f"{r['type']} at {r['place']} ({r['ago']} min ago, "
            f"{'verified' if r['verified'] else 'unverified'}, via {r['source']})" for r in rs[:6]))
            if rs else "No active reports" + (f" in {zone} Jaipur." if zone else "."))

    if _has(q, "upcoming"):
        out.append("Known in advance:\n- " + "\n- ".join(
            f"{c['when']}: {c['what']} around {c['where']}" for c in snap["calendar"]))

    if _has(q, "unusual"):
        out.append(("Unusual right now:\n- " + "\n- ".join(a["message"] for a in snap["anomalies"]))
                   if snap["anomalies"] else "Nothing looks unusual compared with the last few hours.")

    if _has(q, "why"):
        if snap["chains"]:
            out.append("Possible links (not confirmed causes):\n- " + "\n- ".join(
                " then ".join(c["steps"]) + f" [{c['strength']} match]"
                + (f". {c['evidence']['text']}" if c.get("evidence") else "") for c in snap["chains"]))
        else:
            out.append("I don't see linked events in the feeds right now.")

    if not out and zone:
        z = zones[zone]
        n = sum(1 for r in active if r["zone"] == zone)
        out.append(f"{zone} Jaipur: {z['rain_text']}, {n} active reports, stress {int(z['stress'] * 100)}/100.")

    if not out:
        out.append(snap["summary"])
        out.append("Ask me about weather, your route, a road (like Tonk Road), traffic in an area, "
                   "incidents, anything unusual, upcoming events, or why something is happening. "
                   "Hindi words like baarish, raasta and kal work too.")

    out.append(f"Based only on the feeds as of {snap['meta']['clock']}. Links are possible, not proven.")
    return "\n\n".join(out)


def facts(snap):
    """Compact, LLM-friendly view of the snapshot."""
    return dict(
        time=snap["meta"]["clock"], mode=snap["meta"]["mode"], pulse=snap["pulse"], summary=snap["summary"],
        feeds=[{k: f.get(k) for k in ("name", "status", "age_min")} for f in snap["feeds"]],
        zones=[{k: z.get(k) for k in ("zone", "rain", "rain_text", "temp", "aqi", "forecast", "stress")}
               for z in snap["zones"]],
        roads=[{k: r[k] for k in ("name", "speed", "congestion", "zone", "source")} for r in snap["roads"]],
        water_flows=[{k: f[k] for k in ("src", "hotspot", "lag", "risk", "roads")} for f in snap["flows"]],
        reports=[{k: r.get(k) for k in ("type", "place", "road", "ago", "verified", "source")}
                 for r in snap["reports"] if r["status"] == "active"],
        possible_links=[dict(steps=c["steps"], strength=c["strength"],
                             evidence=(c.get("evidence") or {}).get("text")) for c in snap["chains"]],
        unusual=[a["message"] for a in snap["anomalies"]],
        route=dict(name=snap["route"]["name"], minutes_left=snap["route"]["eta_left"],
                   ahead=[dict(kind=h["kind"], where=h["where"], km_ahead=h["ahead_km"])
                          for h in snap["route"]["hurdles"] if h["upcoming"]]),
        known_in_advance=[{k: c[k] for k in ("when", "what", "where")} for c in snap["calendar"]],
    )


SYSTEM = (
    "You are Navi, the assistant inside CityPulse Jaipur. Answer ONLY from the FACTS JSON. "
    "If the facts don't cover the question, say so plainly. Describe links between events as "
    "possible links, never proven causes. Reply in the user's language; Hinglish is fine. "
    "Plain words, at most 120 words, short lines. No personal data about anyone."
)


def answer(question, snap):
    rules = answer_rules(question, snap)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return dict(answer=rules, engine="rules")
    try:
        import httpx
        r = httpx.post(
            "https://api.anthropic.com/v1/messages", timeout=20,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json=dict(model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5"), max_tokens=500, system=SYSTEM,
                      messages=[{"role": "user", "content":
                                 f"FACTS:\n{json.dumps(facts(snap), ensure_ascii=False)}\n\nQUESTION: {question}"}]))
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text").strip()
        if text:
            return dict(answer=text, engine="llm")
    except Exception:
        pass
    return dict(answer=rules, engine="rules")
