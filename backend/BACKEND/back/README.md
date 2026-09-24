# CityPulse Jaipur

A live civic pulse for Jaipur. Weather, traffic and resident reports are fused
into one view, with possible links between events, anomaly detection, an AI
assistant (Navi) and a civic contributor leaderboard.

Inspired by the CityPulse City Dashboard (EU CityPulse project), rebuilt in Python.

## Run

    python3 -m pip install -r requirements.txt
    python3 run.py

- Dashboard: http://localhost:8501
- API docs:  http://127.0.0.1:8000/docs
- Stop: Ctrl+C in the terminal

If the backend isn't running, the dashboard still works with its built-in replay.

## Two data modes

- **Replay: monsoon evening** - a scripted 5-8 PM storm, for demos and historical replay.
- **Live Jaipur now** - real weather and air quality from Open-Meteo (free, no key),
  a traffic model (or real speeds if `TOMTOM_API_KEY` is set), and live resident reports.

## Architecture

    Open-Meteo weather ─┐
    Open-Meteo air ─────┤   ingest loop       SQLite store         fusion engine          FastAPI         Streamlit
    TomTom (optional) ──┼─> (every 1-5 min) -> streams +        -> water levels,       -> /api/...    ->  app.py
    Resident reports ───┘                      observations        road speeds, links,
                                               reports, votes      anomalies, pulse

| Original CityPulse component | Here |
|---|---|
| Resource management (stream registry + history) | `backend/store.py`, `/api/streams` |
| Geospatial data infrastructure | `backend/city.py`, `/api/streams?w=&s=&e=&n=`, `/api/city` |
| Data federation | `backend/snapshot.py`, `/api/snapshot` |
| Event detection | `backend/fusion.py`, `backend/analytics.py`, `/api/events` |

New for Jaipur: resident reports with confirm/dispute and anti-spam (`/api/reports`),
a trust-weighted leaderboard, alert rules with a live event stream (`/api/events/stream`),
and AI Navi (`/api/navi`), which answers only from feed data.

## Optional settings (environment variables)

- `TOMTOM_API_KEY` - use measured road speeds from TomTom Traffic Flow
- `ANTHROPIC_API_KEY` - let Navi phrase answers with Claude (still grounded in feed data)
- `CITYPULSE_OFFLINE=1` - don't call any external API
