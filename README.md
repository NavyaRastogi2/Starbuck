# CityPulse Jaipur

**Read your city like a pulse.** CityPulse brings Jaipur's weather, traffic and resident reports onto one map and one clock, finds what looks unusual or connected, and explains it in plain Hindi, Hinglish or English.

> Hackathon prototype for **AmiHacks — Track B: Live Civic Health Dashboard**. Live mode uses live weather and resident reports with modelled traffic; replay mode runs a scripted monsoon evening through the same pipeline.

![CityPulse Jaipur city map](screenshots/1_city_map.png)

---

## The problem

Jaipur's civic information already exists, but it lives in separate places: weather apps, traffic maps, outage notices, complaint portals and word of mouth. Each source uses its own format, its own clock and its own idea of *where*.

- Residents find out about a flooded underpass or a dead traffic signal **after** they are stuck in it.
- Nobody sees that rain in one area, waterlogging in another and a slow road nearby may be **connected**.
- Existing dashboards are built for analysts, not for a resident who needs an answer in seconds.

The hard part is not collecting one feed. It is fusing feeds that arrive at different rates, in different formats and at different times into something trustworthy and easy to understand.

## What CityPulse does

```text
Weather + Air quality + Traffic + Resident reports   (live)
Scripted monsoon evening                             (replay)
                      ↓
Ingest + normalize  →  one clock (timestamps, freshness) + one map (zone, road, place)
                      ↓
Local store: observation history · reports · confirmations · accounts · points
                      ↓
Fusion: zone stress · city pulse · change vs each area's own baseline · possible links
                      ↓
CityPulse snapshot  →  API backend  →  Streamlit app + Dost
```

---

## Features

### City map — *What's happening around you?*

- One-line plain-language summary of the city (e.g. *"Dry across the city. Roads are moving normally."*) and an overall status badge such as **Calm city**.
- Feed status at a glance: **Weather live · Traffic estimated · Ground reports live**.
- **My pulse:** a personal summary of anything unusual near you (signed-in users get alerts for their own area, family and commute).
- Interactive Jaipur map with clustered incidents and a **Places & services** layer (e.g. hospitals), plus place search.
- **Time window:** Now, last 1 hour, last 6 hours or today. **Map styles:** Neutral, Detailed, Night.
- Area status panel that shows when any area has unusual activity in the selected window.
- **Route:** pick From and To, travel by drive, walk or cycle, and see how city events may affect the trip.

### My community

- Jaipur is split into **four communities: North, East, South and West**. Every member joins the community of the area they live in.
- **Community leaderboard** comparing points, members, confirmed reports, active reports, status and weather for each community.
- **"Why this area looks the way it does":** each signal (rainfall, resident reports, air quality) is compared with that area's own recent baseline, with notable changes marked, plus the evidence and confidence behind any possible connection.
- **Report something:** residents report what is happening (e.g. waterlogging), where, and how bad. Reports appear on the map immediately.
- Top contributors per community and the latest reports across Jaipur.

### Ask Dost

- **Dost** is a Jaipur *saathi* you can ask in **Hindi, Hinglish or English**, e.g. *"Tonk Road pe baarish ka kya haal hai?"*, *"वैशाली में क्या हुआ?"*, *"baarish kab rukegi"*.
- Quick questions: Weather · My route · Incidents · Why so slow? · Anything unusual?
- Dost only answers from the current feeds and shows what it can see and where each feed comes from. Guests get citywide answers; signed-in users get answers about their own area and commute.
- Connections are always described as **possible links, not proven causes**.

### Accounts and personalisation

- Guests can explore everything. Creating an account adds a leaderboard username, home area (which sets your community), household details such as children going to school, weather and travel interests, and how you usually get around, so alerts and Dost's answers fit your day.

### Live and replay modes

- **Live Jaipur now:** live weather, live resident reports and modelled traffic.
- **Replay: scripted monsoon evening (demo):** a repeatable storm scenario that runs through the same pipeline, so the full story can be shown at any time.
- **Test a delayed feed:** make one feed stale and see how CityPulse and Dost flag it.

---

## Citizen trust loop

Residents are both users and data contributors.

```text
Report  →  others confirm or dispute  →  verified  →  points & trust  →  back into fusion
```

| Action | Points |
|---|---|
| Your report is confirmed by 3 residents or an official feed | **+10** |
| You confirm someone else's report | **+3** |
| Most people who saw your report dispute it | **−5** |
| Reporting the same thing twice | counts as a confirmation, so spam doesn't pay |

The first ten leaderboard handles are sample contributors for the demo.

---

## System Architecture

![CityPulse System Architecture](architecture.png)

Feeds arrive in different formats and on different clocks. CityPulse normalizes every observation onto **one clock** (timestamp and freshness) and **one map** (latitude/longitude, zone, road, place), stores it with its history, and fuses the signals into zone stress and a city pulse. Each area is compared with its own baseline to flag notable changes, and rule-based checks surface **possible links** between events. The result is a single snapshot served by the API backend to the Streamlit app and to Dost, which explains the snapshot but never invents civic facts. Live and replay modes share the same pipeline.

---

## Data sources

| Signal | Source | Status |
|---|---|---|
| Weather | Open-Meteo | Live |
| Air quality (AQI) | Live reading, shown per area | Live |
| Traffic | CityPulse traffic model | Modelled / estimated |
| Ground reports | Residents via CityPulse | Live |
| Monsoon evening | Scripted scenario | Replay (demo) |

Optional connections can be configured from the **Data connections** panel in the app sidebar.

---

## Technology stack

| Layer | Technology |
|---|---|
| Language | Python |
| Frontend | Streamlit |
| Backend API | FastAPI (interactive docs at `http://127.0.0.1:8000/docs`) |
| Storage | Local database managed by the backend (`store.py`) |
| Weather | Open-Meteo |

---

## Project structure

```text
Starbuck/
├── app.py                      # Streamlit app
├── data.py                     # Scenario / demo data
├── backend/
│   └── BACKEND/back/
│       ├── main.py             # API entry point
│       ├── run.py              # Starts the backend
│       ├── requirements.txt    # Backend dependencies
│       ├── feeds.py, live.py   # Feed ingestion
│       ├── scenario.py         # Replay scenario
│       ├── store.py            # Persistence
│       ├── city.py             # Jaipur zones, roads and places
│       ├── fusion.py, analytics.py, snapshot.py   # Fusion, baselines, snapshot
│       ├── routing.py          # Routes
│       ├── trust.py            # Confirmations, disputes and points
│       ├── navi.py             # Dost
│       ├── service.py, client.py
├── architecture.png            # System architecture diagram
├── screenshots/                # Images used in this README
└── README.md
```

---

## Running locally

Requires Python 3.

**1. Start the backend**

```bash
git clone https://github.com/NavyaRastogi2/Starbuck.git
cd Starbuck/backend/BACKEND/back
pip install -r requirements.txt
python run.py
```

The API runs at `http://127.0.0.1:8000`; open `/docs` to explore it.

**2. Start the app** (in a second terminal, from the repository root)

```bash
cd Starbuck
streamlit run app.py
```

The sidebar shows **Backend connected** when the app can reach the API.

### Try this in the demo

1. On **City map**, read the city summary, then switch the time window between *Now* and *Last 6 hours*.
2. Switch **Data** to *Replay: scripted monsoon evening* and watch areas change as the storm moves through.
3. Open **My community** to see why an area looks the way it does, then submit a report.
4. Plan a route from Johari Bazaar to Hawa Mahal.
5. Set **Test a delayed feed**, then ask Dost *"Why so slow?"* or *"Anything unusual?"*

---

## Screenshots

### City map
![City map](screenshots/1_city_map.png)

### My community: four communities and leaderboard
![Community leaderboard](screenshots/2_community_leaderboard.png)

### My community: area view, points and reporting
![North Jaipur right now](screenshots/3_community_area.png)

### Ask Dost
![Ask Dost](screenshots/4_ask_dost.png)

### Create an account
![Create account](screenshots/5_create_account.png)

---

## Current limitations

- **Traffic is modelled**, not read from a live traffic feed.
- **Replay** covers one scripted monsoon evening.
- **Possible links are rule-based correlations,** not proven causes.
- **Baselines need history:** a newly started instance has little history to compare against.
- **Four zones** are a simplification, not administrative wards.
- **Runs locally**; the first ten leaderboard handles are sample data.

## Future scope

Possible future integrations (not implemented today):

- Live traffic and public-transit feeds
- 311 / municipal complaint systems
- Utility outage feeds and emergency alerts
- Noise complaints and other civic APIs
- Ward-level areas and hosted deployment

---

## Team contributions

| Team Member | GitHub | Contribution |
|---|---|---|
| **Navya Rastogi** | [@NavyaRastogi2](https://github.com/NavyaRastogi2) | Frontend & backend development, application implementation, core functionality |
| **Navya Sharma** | [@nvyshrm8](https://github.com/nvyshrm8) | Presentation, architecture diagram, documentation, demo preparation |

Both team members contributed to the overall product development and hackathon submission.

Built for **AmiHacks** (Track B: Live Civic Health Dashboard).

## License

No license has been added to this repository yet.
