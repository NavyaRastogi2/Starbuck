"""
Persistence (SQLite, one file, zero setup).

Mirrors CityPulse's "Resource Management" (stream registry + history) and
adds the civic layer: reports, votes, points ledger, alert rules, events.
"""
import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone

from . import city as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS streams (
  id TEXT PRIMARY KEY, uuid TEXT, name TEXT, kind TEXT, provider TEXT, zone TEXT, road TEXT,
  lon REAL, lat REAL, unit TEXT, cadence_s INTEGER, simulated INTEGER DEFAULT 0,
  last_seen TEXT, last_error TEXT);
CREATE TABLE IF NOT EXISTS observations (
  stream_id TEXT, ts TEXT, value REAL, extra TEXT, PRIMARY KEY (stream_id, ts));
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY, type TEXT, place TEXT, lon REAL, lat REAL, road TEXT, zone TEXT,
  severity INTEGER, source TEXT, reporter TEXT, note TEXT, created_at TEXT, status TEXT DEFAULT 'active');
CREATE TABLE IF NOT EXISTS votes (
  report_id TEXT, handle TEXT, kind TEXT, ts TEXT, PRIMARY KEY (report_id, handle));
CREATE TABLE IF NOT EXISTS contributors (
  handle TEXT PRIMARY KEY, area TEXT, verified INTEGER, submitted INTEGER, badge TEXT);
CREATE TABLE IF NOT EXISTS ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, handle TEXT, delta INTEGER, reason TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS alert_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT, metric TEXT, target TEXT, threshold REAL, label TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, title TEXT, payload TEXT);
"""
HANDLE_RE = re.compile(r"^[a-z0-9_]{3,20}$")


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


class StoreError(ValueError):
    pass


class Store:
    def __init__(self, path="citypulse.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript(SCHEMA)
            self.db.commit()
        self._seed()

    # ------------------------------------------------------------ helpers
    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur.lastrowid

    def _seed(self):
        if not self.q("SELECT 1 FROM contributors LIMIT 1"):
            for h, area, ver, tot, badge in C.CONTRIBUTORS_SEED:
                self.x("INSERT INTO contributors VALUES (?,?,?,?,?)", (h, area, ver, tot, badge))
        for z in C.ZONES:
            lon, lat = C.ZONE_CENTROIDS[z]
            self.register(f"weather:{z}", f"Rainfall {z}", "weather", "Open-Meteo", z, None, lon, lat, "mm/hr", 300)
            self.register(f"air:{z}", f"Air quality {z}", "air", "Open-Meteo Air Quality", z, None, lon, lat, "US AQI", 900)
            self.register(f"forecast:{z}", f"Rain forecast {z}", "forecast", "Open-Meteo", z, None, lon, lat, "mm/hr", 300)
        for road in C.ROADS:
            lon, lat = C.road_mid(road)
            self.register(f"traffic:{road}", f"Speed {road}", "traffic", "CityPulse traffic model",
                          C.road_zone(road), road, lon, lat, "km/h", 60, simulated=1)
        self.register("reports:citizen", "Resident reports", "reports", "CityPulse app", None, None,
                      C.CENTER[0], C.CENTER[1], "reports", 0)

    # ------------------------------------------------------------ registry
    def register(self, sid, name, kind, provider, zone, road, lon, lat, unit, cadence, simulated=0):
        self.x("""INSERT INTO streams (id, uuid, name, kind, provider, zone, road, lon, lat, unit, cadence_s, simulated)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                  ON CONFLICT(id) DO UPDATE SET provider=excluded.provider, simulated=excluded.simulated""",
               (sid, str(uuid.uuid5(uuid.NAMESPACE_URL, "citypulse-jaipur/" + sid)), name, kind, provider,
                zone, road, lon, lat, unit, cadence, simulated))

    def set_provider(self, sid, provider, simulated):
        self.x("UPDATE streams SET provider=?, simulated=? WHERE id=?", (provider, int(simulated), sid))

    def streams(self, kind=None, zone=None, bbox=None):
        rows = self.q("SELECT * FROM streams ORDER BY kind, id")
        if kind:
            rows = [r for r in rows if r["kind"] == kind]
        if zone:
            rows = [r for r in rows if r["zone"] == zone]
        if bbox:
            rows = [r for r in rows if C.in_bbox(r["lon"], r["lat"], *bbox)]
        return rows

    def stream(self, sid):
        rows = self.q("SELECT * FROM streams WHERE id=? OR uuid=?", (sid, sid))
        return rows[0] if rows else None

    def mark_error(self, sid, err):
        self.x("UPDATE streams SET last_error=? WHERE id=?", (str(err)[:200], sid))

    # ------------------------------------------------------------ observations
    def observe(self, sid, value, extra=None, ts=None):
        ts = iso(ts or now())
        self.x("INSERT OR REPLACE INTO observations VALUES (?,?,?,?)",
               (sid, ts, float(value), json.dumps(extra) if extra is not None else None))
        self.x("UPDATE streams SET last_seen=?, last_error=NULL WHERE id=? AND (last_seen IS NULL OR last_seen<?)",
               (ts, sid, ts))

    def observe_if_new(self, sid, value, ts):
        self.x("INSERT OR IGNORE INTO observations VALUES (?,?,?,NULL)", (sid, iso(ts), float(value)))

    def latest(self, sid):
        rows = self.q("SELECT * FROM observations WHERE stream_id=? ORDER BY ts DESC LIMIT 1", (sid,))
        if not rows:
            return None
        r = rows[0]
        r["extra"] = json.loads(r["extra"]) if r["extra"] else {}
        return r

    def history(self, sid, minutes=180):
        since = iso(now() - timedelta(minutes=minutes))
        rows = self.q("SELECT ts, value, extra FROM observations WHERE stream_id=? AND ts>=? ORDER BY ts",
                      (sid, since))
        for r in rows:
            r["extra"] = json.loads(r["extra"]) if r["extra"] else {}
        return rows

    def value_at(self, sid, when, tolerance_min=25):
        """Closest observation at or before `when` (within tolerance)."""
        rows = self.q("SELECT ts, value FROM observations WHERE stream_id=? AND ts<=? ORDER BY ts DESC LIMIT 1",
                      (sid, iso(when)))
        if rows and (when - parse(rows[0]["ts"])) <= timedelta(minutes=tolerance_min):
            return rows[0]["value"]
        return None

    def purge(self, days=2):
        self.x("DELETE FROM observations WHERE ts<?", (iso(now() - timedelta(days=days)),))

    # ------------------------------------------------------------ reports
    def _contributor(self, handle, area="Jaipur"):
        if not self.q("SELECT 1 FROM contributors WHERE handle=?", (handle,)):
            self.x("INSERT INTO contributors VALUES (?,?,0,0,'New reporter')", (handle, area))

    def create_report(self, rtype, place, severity, handle, note=""):
        handle = (handle or "").strip().lower()
        if rtype not in C.REPORT_TYPES:
            raise StoreError(f"Unknown report type. Use one of: {', '.join(C.REPORT_TYPES)}")
        if place not in C.PLACES:
            raise StoreError("Unknown place. Pick one from the list.")
        if not HANDLE_RE.match(handle):
            raise StoreError("Handle must be 3-20 characters: lowercase letters, numbers or _")
        severity = max(1, min(3, int(severity)))
        t = now()
        recent = self.q("SELECT COUNT(*) n FROM reports WHERE reporter=? AND created_at>=?",
                        (handle, iso(t - timedelta(minutes=10))))[0]["n"]
        if recent >= 5:
            raise StoreError("Too many reports in 10 minutes. Try again shortly.")
        # Same thing, same place, recently? Count it as a confirmation instead of a duplicate.
        dup = self.q("""SELECT id, reporter FROM reports WHERE type=? AND place=? AND status='active'
                        AND created_at>=? ORDER BY created_at DESC LIMIT 1""",
                     (rtype, place, iso(t - timedelta(minutes=20))))
        if dup:
            if dup[0]["reporter"] != handle:
                self.vote(dup[0]["id"], handle, "confirm")
            return dict(id=dup[0]["id"], merged=True)
        lon, lat, road = C.PLACES[place]
        rid = "r-" + uuid.uuid4().hex[:10]
        self._contributor(handle, place)
        self.x("INSERT INTO reports VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'active')",
               (rid, rtype, place, lon, lat, road, C.zone_of(lon, lat), severity, "Citizen", handle,
                note[:200], iso(t)))
        self.x("UPDATE contributors SET submitted=submitted+1 WHERE handle=?", (handle,))
        self.event("report_created", f"{rtype} reported at {place}", dict(id=rid, reporter=handle))
        return dict(id=rid, merged=False)

    def vote(self, rid, handle, kind):
        handle = (handle or "").strip().lower()
        if not HANDLE_RE.match(handle):
            raise StoreError("Handle must be 3-20 characters: lowercase letters, numbers or _")
        rep = self.q("SELECT * FROM reports WHERE id=?", (rid,))
        if not rep:
            raise StoreError("Report not found")
        rep = rep[0]
        if rep["reporter"] == handle:
            raise StoreError("You can't vote on your own report")
        if self.q("SELECT 1 FROM votes WHERE report_id=? AND handle=?", (rid, handle)):
            raise StoreError("You already voted on this report")
        self._contributor(handle)
        self.x("INSERT INTO votes VALUES (?,?,?,?)", (rid, handle, kind, iso(now())))
        counts = self.vote_counts(rid)
        if kind == "confirm":
            self.x("INSERT INTO ledger (handle, delta, reason, ts) VALUES (?,?,?,?)",
                   (handle, 3, f"Confirmed report {rid}", iso(now())))
            if counts["confirm"] == 3 and rep["reporter"]:
                self.x("UPDATE contributors SET verified=verified+1 WHERE handle=?", (rep["reporter"],))
                self.event("report_verified", f"{rep['type']} at {rep['place']} verified by residents", dict(id=rid))
        else:
            if counts["dispute"] >= 3 and counts["dispute"] > counts["confirm"] and rep["status"] == "active":
                self.x("UPDATE reports SET status='disputed' WHERE id=?", (rid,))
                if rep["reporter"]:
                    self.x("INSERT INTO ledger (handle, delta, reason, ts) VALUES (?,?,?,?)",
                           (rep["reporter"], -5, f"Report {rid} disputed", iso(now())))
                self.event("report_disputed", f"{rep['type']} at {rep['place']} marked as disputed", dict(id=rid))
        return counts

    def vote_counts(self, rid):
        rows = self.q("SELECT kind, COUNT(*) n FROM votes WHERE report_id=? GROUP BY kind", (rid,))
        c = {"confirm": 0, "dispute": 0}
        c.update({r["kind"]: r["n"] for r in rows})
        return c

    def resolve(self, rid):
        self.x("UPDATE reports SET status='resolved' WHERE id=?", (rid,))

    def active_reports(self, window_min=240):
        """Reports still within their lifetime (and created in the last `window_min`)."""
        t = now()
        rows = self.q("SELECT * FROM reports WHERE status IN ('active','disputed') AND created_at>=?",
                      (iso(t - timedelta(minutes=window_min)),))
        out = []
        for r in rows:
            age = int((t - parse(r["created_at"])).total_seconds() // 60)
            if age >= C.DURATION_MIN.get(r["type"], 60):
                continue
            c = self.vote_counts(r["id"])
            out.append(dict(id=r["id"], type=r["type"], place=r["place"], lon=r["lon"], lat=r["lat"],
                            road=r["road"], zone=r["zone"], severity=r["severity"], source=r["source"],
                            reporter=r["reporter"], corroborations=c["confirm"], disputes=c["dispute"],
                            status=r["status"], ago=age, note=r["note"],
                            created=r["created_at"], live=True))
        return out

    def report_counts_at(self, when):
        """Active report count per zone at a past moment (for charts)."""
        rows = self.q("SELECT type, zone, created_at FROM reports WHERE created_at<=? AND created_at>=?",
                      (iso(when), iso(when - timedelta(hours=4))))
        counts = {z: 0 for z in C.ZONES}
        for r in rows:
            age = (when - parse(r["created_at"])).total_seconds() / 60
            if age < C.DURATION_MIN.get(r["type"], 60):
                counts[r["zone"]] = counts.get(r["zone"], 0) + 1
        return counts

    # ------------------------------------------------------------ contributors
    def contributors(self):
        return [(r["handle"], r["area"], r["verified"], r["submitted"], r["badge"])
                for r in self.q("SELECT * FROM contributors")]

    def ledger_sums(self):
        return {r["handle"]: r["s"] for r in self.q("SELECT handle, SUM(delta) s FROM ledger GROUP BY handle")}

    # ------------------------------------------------------------ alerts + events
    def rules(self):
        return self.q("SELECT * FROM alert_rules ORDER BY id")

    def add_rule(self, metric, target, threshold, label=""):
        if metric not in ("rain", "speed", "pulse", "report"):
            raise StoreError("metric must be rain, speed, pulse or report")
        valid = {"rain": C.ZONES, "speed": list(C.ROADS), "pulse": ["Jaipur"], "report": C.REPORT_TYPES}[metric]
        if target not in valid:
            raise StoreError(f"target must be one of: {', '.join(valid)}")
        rid = self.x("INSERT INTO alert_rules (metric, target, threshold, label, created_at) VALUES (?,?,?,?,?)",
                     (metric, target, float(threshold), label[:80], iso(now())))
        return self.q("SELECT * FROM alert_rules WHERE id=?", (rid,))[0]

    def delete_rule(self, rid):
        self.x("DELETE FROM alert_rules WHERE id=?", (rid,))

    def event(self, kind, title, payload=None):
        return self.x("INSERT INTO events (ts, kind, title, payload) VALUES (?,?,?,?)",
                      (iso(now()), kind, title, json.dumps(payload or {})))

    def events(self, since_id=0, limit=50):
        rows = self.q("SELECT * FROM events WHERE id>? ORDER BY id DESC LIMIT ?", (since_id, limit))
        for r in rows:
            r["payload"] = json.loads(r["payload"] or "{}")
        return list(reversed(rows))

    def recent_alert_event(self, rule_id, minutes=30):
        since = iso(now() - timedelta(minutes=minutes))
        return any(e["payload"].get("rule_id") == rule_id
                   for e in self.events(0, 200) if e["kind"] == "alert" and e["ts"] >= since)
