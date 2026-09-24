"""
Trust layer: decides whether a ground report is verified, and scores
contributors. Points reward confirmed reports, not raw volume, so spamming
doesn't pay.

Verified if ANY of:
  - it came from an official feed
  - 3+ other residents confirmed it
  - sensors agree (e.g. rain upstream for waterlogging) AND the reporter
    has a decent trust score or someone confirmed it
  - a high-trust reporter + 1 confirmation
Disputed if 3+ disputes outnumber confirmations.
"""
from . import city as C


def leaderboard(contributors, ledger_sums=None):
    """contributors: iterable of (handle, area, verified, submitted, badge)."""
    ledger_sums = ledger_sums or {}
    rows = []
    for handle, area, ver, tot, badge in contributors:
        tot = max(tot, ver)
        accuracy = ver / tot if tot else 0.0
        points = ver * 10 + (tot - ver) + ledger_sums.get(handle, 0)
        trust = round(min(1.0, 0.5 * accuracy + 0.5 * min(1, ver / 50)), 2)
        rows.append(dict(handle=handle, area=area, verified=ver, submitted=tot,
                         accuracy=round(accuracy * 100), points=points, trust=trust, badge=badge))
    rows.sort(key=lambda r: -r["points"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def assess(report, all_reports, rain_at, trust_of):
    support = []
    official = report["source"] != "Citizen"
    if official:
        support.append(f"Official source: {report['source']}")
    conf, disp = report.get("corroborations", 0), report.get("disputes", 0)
    if conf:
        support.append(f"{conf} resident{'s' if conf != 1 else ''} confirmed")

    sensor = False
    if report["type"] == "Waterlogging":
        local = rain_at(report["zone"], 0)
        upstream = max((rain_at(f["src"], C.mid_lag(f)) for f in C.FLOWS if f["zone"] == report["zone"]),
                       default=0)
        recent = max(rain_at(report["zone"], m) for m in (0, 30, 60, 90))
        if max(local, upstream, recent) >= 3:
            sensor = True
            support.append("Rain sensors agree")
    if report["type"] == "Signal down":
        if any(o["type"] == "Power outage" and o["zone"] == report["zone"] for o in all_reports):
            sensor = True
            support.append("Matches a power outage in the area")

    trust = trust_of(report.get("reporter")) if report.get("reporter") else 0
    if trust >= 0.85:
        support.append("Reporter has a strong track record")

    disputed = disp >= 3 and disp > conf
    verified = not disputed and (
        official or conf >= 3 or (sensor and (trust >= 0.6 or conf >= 1)) or (trust >= 0.85 and conf >= 1))
    return dict(verified=verified, disputed=disputed, support=support,
                status="disputed" if disputed else report.get("status", "active"))
