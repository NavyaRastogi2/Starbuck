"""
CityPulse Jaipur - frontend (Streamlit + pydeck).
Start everything with:  python3 run.py
Frontend only:          python3 -m streamlit run app.py
"""
import html
import os
import sys
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client  # noqa: E402
from backend import city as C  # noqa: E402

st.set_page_config(page_title="CityPulse Jaipur", page_icon="💗", layout="wide")

INDIGO, RANI, POTTERY, SAFFRON = "#8C2451", "#E0457B", "#1C8FB0", "#F08A24"   # INDIGO = deep rose ink
SAND, LEAF, PURPLE = "#FFF8F0", "#4E9A6A", "#7B3FC4"
MODE_CLASS = {"Pulse": "pulse", "Weather": "weather", "Route": "route", "Ground reports": "reports"}
ZONE_COLORS = [POTTERY, RANI, SAFFRON, PURPLE]
STATUS_DOT = {"live": "#9BE3B5", "replay": "#9BE3B5", "modelled": "#BFE0FF",
              "delayed": SAFFRON, "unavailable": "#FF6B8B"}


def block_print(ink, leaf, ink_op, leaf_op, ring_op):
    """Sanganeri-style block print tile: half-drop floral butis, dot rosettes
    and a small green sprig, printed faintly so it sits behind the content."""
    petals = "".join(f"<ellipse cx='0' cy='-11' rx='4.5' ry='10' transform='rotate({k * 45})'/>" for k in range(8))
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240' viewBox='0 0 240 240'>"
        f"<defs><g id='b'>{petals}<circle r='4.5' fill='{ink}' fill-opacity='0' stroke='{ink}' "
        f"stroke-opacity='{ring_op}' stroke-width='1.5'/></g>"
        "<g id='r'><circle r='3'/><circle cy='-8' r='1.6'/><circle cx='8' r='1.6'/>"
        "<circle cy='8' r='1.6'/><circle cx='-8' r='1.6'/></g></defs>"
        f"<g fill='{ink}' fill-opacity='{ink_op}'>"
        "<use href='#b' x='60' y='60'/><use href='#b' x='180' y='180'/>"
        "<use href='#r' x='180' y='60'/><use href='#r' x='60' y='180'/></g>"
        f"<path d='M120 150 q10 -15 0 -30 q-10 -15 0 -30' fill='none' stroke='{leaf}' "
        f"stroke-opacity='{leaf_op}' stroke-width='1.3' stroke-linecap='round'/>"
        f"<g fill='{leaf}' fill-opacity='{leaf_op}'>"
        "<ellipse cx='128' cy='128' rx='5' ry='2.2' transform='rotate(-35 128 128)'/>"
        "<ellipse cx='112' cy='102' rx='5' ry='2.2' transform='rotate(35 112 102)'/></g></svg>")
    return "url(\"data:image/svg+xml," + quote(svg, safe="") + "\")"


PAGE_PRINT = block_print("#D94A78", "#4E9A6A", 0.13, 0.30, 0.18)
SIDEBAR_PRINT = block_print("#D94A78", "#4E9A6A", 0.09, 0.22, 0.12)
HERO_PRINT = block_print("#FFFFFF", "#CFEBD8", 0.13, 0.35, 0.2)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Hind:wght@400;500;600&display=swap');
.stApp { background-color: #FFF8F0; background-image: __PAGE__; background-size: 240px 240px; }
.block-container { padding-top: 1.4rem; max-width: 1440px; }
h1, h2, h3 { font-family: 'Baloo 2', sans-serif !important; color: #8C2451; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background-color: #FCE9EF; background-image: __SIDE__; background-size: 240px 240px;
  border-right: 2px solid #BFDCC7; }
.cp-brand { font-family: 'Baloo 2', sans-serif; font-weight: 800; font-size: 30px; color: #C73E6B; line-height: 1; }
.cp-brand-sub { font-family: 'Hind', sans-serif; color: #7A5A68; font-size: 14px; margin: 4px 0 10px;
  padding-bottom: 8px; border-bottom: 1px dashed #9CC9A9; }
.cp-conn { font-family: 'Hind', sans-serif; font-size: 13.5px; padding: 6px 10px; border-radius: 10px; margin-bottom: 12px; }

.cp-hero { display: grid; grid-template-columns: 210px 1fr; gap: 28px; align-items: center;
  background-color: #C73E6B; background-image: __HERO__; background-size: 240px 240px;
  color: #FFF8F0; border-radius: 22px; padding: 20px 28px 18px; margin: 0 0 22px;
  box-shadow: 0 5px 0 #F6E3C8, 0 8px 0 #7DB892; }
.cp-city { font-family: 'Hind', sans-serif; font-size: 15px; opacity: .9; }
.cp-score { font-family: 'Baloo 2', sans-serif; font-weight: 800; font-size: 88px; line-height: .95; }
.cp-state { display: inline-block; font-family: 'Baloo 2', sans-serif; font-weight: 700; font-size: 18px;
  margin-top: 4px; padding: 1px 12px; border-radius: 999px; color: #3B2331; }
.cp-beat { width: 100%; height: 64px; display: block; }
.cp-beat polyline { stroke-dasharray: 1700; stroke-dashoffset: 1700; animation: cp-draw 3.4s linear infinite; }
@keyframes cp-draw { to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { .cp-beat polyline { animation: none; stroke-dashoffset: 0; } }
.cp-summary { font-family: 'Hind', sans-serif; font-size: 18px; line-height: 1.45; margin: 6px 0 10px; max-width: 75ch; }
.cp-pill { display: inline-flex; align-items: center; gap: 7px; background: rgba(255,255,255,.18);
  border-radius: 999px; padding: 3px 12px; margin: 0 8px 4px 0; font-family: 'Hind', sans-serif; font-size: 13.5px; }
.cp-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
@media (max-width: 760px) { .cp-hero { grid-template-columns: 1fr; } .cp-score { font-size: 64px; } }

.cp-alertbar { background: #8C2451; border-left: 6px solid #7DB892; color: #fff; border-radius: 14px; padding: 10px 16px; margin-bottom: 12px;
  font-family: 'Hind', sans-serif; font-size: 15px; }
.cp-alertbar b { font-family: 'Baloo 2', sans-serif; font-size: 17px; }
.cp-notice { background: #FDEBD6; border-left: 6px solid #F08A24; border-radius: 10px; padding: 8px 14px;
  font-family: 'Hind', sans-serif; font-size: 14.5px; color: #3A2D55; margin-bottom: 12px; }

.cp-weather { --acc: #1C8FB0; --tint: #E1F2F7; }
.cp-route   { --acc: #F08A24; --tint: #FDEBD6; }
.cp-reports { --acc: #7B3FC4; --tint: #EEE4FA; }
.cp-pulse   { --acc: #E0457B; --tint: #FBE1EA; }

.cp-modebar { font-family: 'Hind', sans-serif; font-size: 15px; color: #3A2D55; padding: 8px 14px;
  border-left: 6px solid var(--acc); background: var(--tint); border-radius: 10px; margin: 2px 0 12px; }
.cp-h { font-family: 'Baloo 2', sans-serif; font-weight: 700; font-size: 22px; color: #8C2451; margin: 0 0 8px; }
.cp-h::after { content: ''; display: block; width: 38px; height: 2px; background: #7DB892; margin-top: 2px; border-radius: 2px; }
.cp-sub { font-family: 'Hind', sans-serif; font-size: 14px; color: #7A5A68; margin: -2px 0 10px; }

.cp-chain { background: #fff; border: 1px solid #F3E3D3; border-left: 6px solid var(--acc); border-radius: 14px; padding: 12px 14px; margin-bottom: 12px; }
.cp-chain-tag { font-family: 'Hind', sans-serif; font-weight: 600; font-size: 13px; color: var(--acc); margin-bottom: 6px; }
.cp-step { font-family: 'Hind', sans-serif; font-size: 15px; color: #2A1F3D; background: var(--tint); padding: 6px 10px; border-radius: 8px; }
.cp-arrow { text-align: center; color: var(--acc); font-size: 16px; line-height: 1.2; }
.cp-note { font-family: 'Hind', sans-serif; font-size: 13px; color: #6B5A7E; margin-top: 6px; }
.cp-evidence { font-family: 'Hind', sans-serif; font-size: 13px; color: #2F6B44; margin-top: 6px;
  border-top: 1px dashed #9CC9A9; padding-top: 6px; }

.cp-zones { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
.cp-zone { background: #fff; border: 1px solid #F3E3D3; border-radius: 14px; padding: 10px 12px; border-top: 5px solid var(--acc); font-family: 'Hind', sans-serif; }
.cp-zone b { font-family: 'Baloo 2', sans-serif; font-size: 30px; color: #8C2451; line-height: 1; }
.cp-zone span { color: #6B5A7E; font-size: 13.5px; }

.cp-item { display: flex; gap: 10px; background: #fff; border: 1px solid #F3E3D3; border-radius: 12px; padding: 9px 12px; margin-bottom: 8px; font-family: 'Hind', sans-serif; font-size: 14.5px; color: #2A1F3D; }
.cp-bar { width: 6px; border-radius: 4px; flex: none; }
.cp-item small { color: #6B5A7E; font-size: 13px; }
.cp-badge { display: inline-block; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 999px; margin-left: 6px; }
.cp-ok { background: #DDF3E7; color: #1E7A4E; }
.cp-un { background: #F3E6D6; color: #8A5A1E; }
.cp-bad { background: #FBE1EA; color: #A3284F; }
.cp-new { background: #E1F2F7; color: #145A7A; }
.cp-dim { opacity: .5; }

.cp-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-family: 'Hind', sans-serif; font-size: 13.5px; color: #3A2D55; margin-top: 6px; }
.cp-sw { width: 12px; height: 12px; border-radius: 3px; display: inline-block; margin-right: 6px; vertical-align: -1px; }

.cp-eta { display: flex; gap: 18px; background: #fff; border-radius: 14px; padding: 10px 14px; margin-bottom: 12px; font-family: 'Hind', sans-serif; }
.cp-eta b { font-family: 'Baloo 2', sans-serif; font-size: 34px; color: #8C2451; line-height: 1; display: block; }

.cp-podium { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 14px; }
.cp-pod { background: #fff; border-radius: 16px; padding: 14px 16px; font-family: 'Hind', sans-serif; border-bottom: 6px solid var(--acc); }
.cp-pod .rank { font-family: 'Baloo 2', sans-serif; font-weight: 800; font-size: 40px; color: var(--acc); line-height: 1; }
.cp-pod .who { font-family: 'Baloo 2', sans-serif; font-weight: 700; font-size: 20px; color: #8C2451; }
.cp-rules { background: #fff; border-radius: 14px; padding: 12px 16px; font-family: 'Hind', sans-serif; font-size: 14.5px; color: #2A1F3D; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 2px dashed #BFDCC7; }
.stTabs [data-baseweb="tab"] { font-family: 'Baloo 2', sans-serif; font-size: 17px; }
[data-testid="stDeckGlJsonChart"] { border-radius: 18px; overflow: hidden; border: 3px solid #fff;
  box-shadow: 0 0 0 1px #F3E3D3, 0 6px 18px rgba(140,36,81,.10); }
[data-testid="stChatMessage"] { background: rgba(255,255,255,.85); border: 1px solid #F3E3D3; border-radius: 14px; }
</style>
"""
st.markdown(CSS.replace("__PAGE__", PAGE_PRINT).replace("__SIDE__", SIDEBAR_PRINT)
            .replace("__HERO__", HERO_PRINT), unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s))


def md(s):
    st.markdown(s, unsafe_allow_html=True)


def stretch(fn, *args, **kwargs):
    """Full-width rendering across old and new Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except Exception:
        return fn(*args, use_container_width=True, **kwargs)


def item(bar, body, dim=False):
    md(f'<div class="cp-item{" cp-dim" if dim else ""}"><span class="cp-bar" style="background:{bar}"></span>'
       f'<div>{body}</div></div>')


def heartbeat_svg(stress, color):
    amp = 8 + stress * 30
    beat = [(0, 0), (40, 0), (48, -amp * .25), (56, 0), (64, 0), (70, amp * .35),
            (78, -amp), (86, amp * .5), (94, 0), (130, 0)]
    pts = " ".join(f"{k * 130 + dx},{44 + dy:.1f}" for k in range(5) for dx, dy in beat)
    return (f'<svg class="cp-beat" viewBox="0 0 650 88" preserveAspectRatio="none">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def stress_rgb(s):
    return [46, 158, 106] if s < 0.35 else [240, 138, 36] if s < 0.55 else [224, 69, 123]


def fmt(v, suffix="", none="n/a"):
    return none if v is None else f"{v}{suffix}"


# ---------------------------------------------------------------- sidebar
backend_up = client.get("/") is not None
with st.sidebar:
    md('<div class="cp-brand">CityPulse</div><div class="cp-brand-sub">Jaipur, one glance at a time</div>')
    if backend_up:
        md(f'<div class="cp-conn" style="background:#DDF3E7;color:#1E7A4E">Backend connected. '
           f'API docs at <a href="{client.API}/docs" target="_blank">{client.API}/docs</a></div>')
    else:
        md('<div class="cp-conn" style="background:#FDEBD6;color:#8A5A1E">Backend offline. Showing the built-in '
           'replay. Start everything with <code>python3 run.py</code></div>')

    data_mode = st.radio("Data", ["Replay: monsoon evening", "Live Jaipur now"])
    mode = "live" if data_mode.startswith("Live") else "replay"
    if mode == "replay":
        t = st.slider("Replay the evening (minutes after 5 PM)", 0, 180, 95, step=5)
    else:
        t = 95
        st.caption("Real weather and air quality from Open-Meteo, refreshed every 5 minutes.")
        if st.button("Refresh now"):
            st.rerun()
    area = st.selectbox("Zoom to area", ["All Jaipur"] + C.ZONES)
    route_name = st.selectbox("Your route", list(C.ROUTES))
    progress = st.slider("How far along your trip (%)", 0, 100, 20, step=5)
    delayed = st.selectbox("Test a delayed feed", ["None", "Weather", "Traffic", "Ground reports"])
    delayed = None if delayed == "None" else delayed
    handle = st.text_input("Your handle (for reports and votes)", value=st.session_state.get("handle", ""),
                           placeholder="e.g. pinkcity_rider", max_chars=20).strip().lower()
    st.session_state.handle = handle

    if backend_up:
        with st.expander("Alert me when..."):
            kind = st.selectbox("Watch", ["Rain in an area", "A road slows down", "City pulse drops",
                                          "A verified report appears"])
            if kind == "Rain in an area":
                metric, target = "rain", st.selectbox("Area", C.ZONES)
                thr = st.number_input("At or above (mm/hr)", 0.5, 100.0, 5.0, step=0.5)
            elif kind == "A road slows down":
                metric, target = "speed", st.selectbox("Road", list(C.ROADS))
                thr = st.number_input("At or below (km/h)", 1.0, 60.0, 15.0, step=1.0)
            elif kind == "City pulse drops":
                metric, target = "pulse", "Jaipur"
                thr = st.number_input("At or below (score)", 10.0, 99.0, 55.0, step=1.0)
            else:
                metric, target = "report", st.selectbox("Report type", C.REPORT_TYPES)
                thr = 1.0
            if st.button("Add alert"):
                ok, res = client.post("/api/alerts/rules", dict(metric=metric, target=target, threshold=thr))
                st.success("Alert added") if ok else st.error(res)
            for rule in client.get("/api/alerts/rules", default=[]) or []:
                c1, c2 = st.columns([4, 1])
                c1.caption(f"{rule['metric']}: {rule['target']} {'>=' if rule['metric'] in ('rain', 'report') else '<='} "
                           f"{rule['threshold']:g}")
                if c2.button("✕", key=f"del_rule_{rule['id']}"):
                    client.delete(f"/api/alerts/rules/{rule['id']}")
                    st.rerun()

snap = client.snapshot(mode, t, area, route_name, progress / 100, delayed)
meta, pulse = snap["meta"], snap["pulse"]
reports = snap["reports"]
active = [r for r in reports if r["status"] == "active"]
chip_color = {"Calm": "#CDEBD6", "Busy": "#FBE0B8", "Stressed": "#FFE3EC", "Critical": "#FFFFFF"}[pulse["state"]]

# ---------------------------------------------------------------- hero
pills = ""
for f in snap["feeds"]:
    label = {"live": "live", "replay": "replay", "modelled": "modelled", "delayed": f"{f.get('age_min')} min old",
             "unavailable": "unavailable"}.get(f["status"], f["status"])
    pills += (f'<span class="cp-pill" title="{esc(f.get("provider", ""))}"><span class="cp-dot" '
              f'style="background:{STATUS_DOT.get(f["status"], SAFFRON)}"></span>{esc(f["name"])}: {label}</span>')
where = "Replay" if meta["mode"] == "replay" else "Live"
md('<div class="cp-hero">'
   f'<div><div class="cp-city">{where}, Jaipur at {esc(meta["clock"])}</div>'
   f'<div class="cp-score">{pulse["score"]}</div>'
   f'<div class="cp-state" style="background:{chip_color}">{pulse["state"]}</div></div>'
   f'<div>{heartbeat_svg(pulse["stress"], "#FFF4E6")}'
   f'<p class="cp-summary">{esc(snap["summary"])}</p>{pills}</div></div>')
if meta.get("note"):
    md(f'<div class="cp-notice">{esc(meta["note"])}</div>')
if snap.get("alerts"):
    md('<div class="cp-alertbar"><b>Your alerts</b><br/>' + "<br/>".join(esc(a["message"]) for a in snap["alerts"])
       + "</div>")

tab_map, tab_navi, tab_board = st.tabs(["Live map", "AI Navi", "Civic contributors"])

# ================================================================ LIVE MAP
with tab_map:
    view_mode = st.radio("Mode", list(MODE_CLASS), horizontal=True, label_visibility="collapsed")
    mcls = MODE_CLASS[view_mode]
    blurbs = {
        "Pulse": "Everything at once. Areas are tinted by how stressed they are; cards on the right show events that may be connected.",
        "Weather": "Rain by direction. Blue lines show where runoff from each area is likely to flow and roughly how long it takes.",
        "Route": "Your trip. The orange line is still ahead of you; pink markers are hurdles coming up.",
        "Ground reports": "What people and official feeds are reporting. Bigger circles mean more serious reports.",
    }
    md(f'<div class="cp-modebar cp-{mcls}">{blurbs[view_mode]}</div>')

    # ---------------- layers
    layers, zone_rows, label_rows = [], [], []
    for z in snap["zones"]:
        if view_mode == "Weather":
            fill = [28, 143, 176, int(35 + min(1, z["rain"] / 22) * 150)]
            label = f"{z['zone']}\n{z['rain']} mm/hr"
        elif view_mode == "Pulse":
            fill = stress_rgb(z["stress"]) + [85]
            label = f"{z['zone']}\nstress {int(z['stress'] * 100)}"
        else:
            fill, label = [38, 24, 90, 14], z["zone"]
        zone_rows.append(dict(polygon=z["polygon"], fill=fill, name=f"{z['zone']} Jaipur",
                              info=f"{z['rain_text'].capitalize()}, {z['rain']} mm/hr<br/>"
                                   f"{fmt(z.get('temp'), ' C')}, AQI {fmt(z.get('aqi'))}<br/>"
                                   f"Stress {int(z['stress'] * 100)}/100"))
        label_rows.append(dict(pos=z["centroid"], label=label))
    layers.append(pdk.Layer("PolygonLayer", zone_rows, get_polygon="polygon", get_fill_color="fill",
                            get_line_color=[255, 255, 255, 230], line_width_min_pixels=2,
                            stroked=True, filled=True, pickable=True))

    alpha = 230 if view_mode in ("Pulse", "Route") else 110
    layers.append(pdk.Layer(
        "PathLayer",
        [dict(path=r["path"], color=r["color"] + [alpha], name=r["name"],
              info=f"{r['speed']} km/h, {int(r['congestion'] * 100)}% congested"
                   + (" (measured)" if r["source"] == "measured" else " (estimated)"))
         for r in snap["roads"]],
        get_path="path", get_color="color", get_width=6, width_units="pixels",
        cap_rounded=True, joint_rounded=True, pickable=True))

    if view_mode == "Weather":
        flows = snap["flows"]
        layers += [
            pdk.Layer("LineLayer",
                      [dict(src=f["src_pos"], dst=[f["lon"], f["lat"]], width=3 + f["level"] * 9,
                            name=f"Runoff: {f['src']} to {f['hotspot']}",
                            info=f"Estimated {f['lag'][0]} to {f['lag'][1]} min<br/>Roads: {', '.join(f['roads'])}")
                       for f in flows],
                      get_source_position="src", get_target_position="dst", get_color=[20, 90, 170, 220],
                      get_width="width", width_units="pixels", pickable=True),
            pdk.Layer("ScatterplotLayer",
                      [dict(pos=[f["lon"], f["lat"]], radius=250 + f["level"] * 700,
                            color=[28, 143, 176, int(90 + f["level"] * 140)], name=f["hotspot"],
                            info=f"Waterlogging risk: {f['risk']}") for f in flows],
                      get_position="pos", get_radius="radius", get_fill_color="color", stroked=True,
                      get_line_color=[255, 255, 255], line_width_min_pixels=2, pickable=True),
            pdk.Layer("TextLayer",
                      [dict(pos=[(f["src_pos"][0] + f["lon"]) / 2, (f["src_pos"][1] + f["lat"]) / 2],
                            label=f"~{f['lag'][0]}-{f['lag'][1]} min") for f in flows],
                      get_position="pos", get_text="label", get_size=13, get_color=[20, 70, 140],
                      background=True, get_background_color=[255, 255, 255, 220]),
        ]

    if view_mode in ("Pulse", "Ground reports"):
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            [dict(pos=[r["lon"], r["lat"]], radius=140 + 170 * r["severity"], color=r["color"] + [215],
                  name=r["type"],
                  info=f"{esc(r['place'])}<br/>{r['ago']} min ago via {esc(r['source'])}<br/>"
                       f"{'Verified' if r['verified'] else 'Disputed' if r['disputed'] else 'Unverified'}")
             for r in active],
            get_position="pos", get_radius="radius", get_fill_color="color", stroked=True,
            get_line_color=[255, 255, 255], line_width_min_pixels=2, radius_min_pixels=5, pickable=True))

    rt = snap["route"]
    if view_mode == "Route":
        hs = rt["hurdles"]
        layers += [
            pdk.Layer("PathLayer", [dict(path=rt["done"], name="Already travelled", info="")],
                      get_path="path", get_color=[150, 140, 165, 230], get_width=9, width_units="pixels",
                      cap_rounded=True, joint_rounded=True, pickable=True),
            pdk.Layer("PathLayer", [dict(path=rt["ahead"], name="Still ahead", info=rt["name"])],
                      get_path="path", get_color=[240, 138, 36, 245], get_width=10, width_units="pixels",
                      cap_rounded=True, joint_rounded=True, pickable=True),
            pdk.Layer("ScatterplotLayer",
                      [dict(pos=[h["lon"], h["lat"]], name=h["kind"],
                            info=f"{esc(h['where'])}<br/>" + (f"{max(0, h['ahead_km'])} km ahead"
                                                              if h["upcoming"] else "Already passed"),
                            color=[224, 69, 123, 240] if h["upcoming"] else [160, 150, 170, 150]) for h in hs],
                      get_position="pos", get_radius=260, get_fill_color="color", stroked=True,
                      get_line_color=[255, 255, 255], line_width_min_pixels=2, radius_min_pixels=6, pickable=True),
            pdk.Layer("TextLayer", [dict(pos=[h["lon"], h["lat"]], label=h["kind"]) for h in hs if h["upcoming"]],
                      get_position="pos", get_text="label", get_size=13, get_color=[110, 30, 70],
                      get_pixel_offset=[0, -20], background=True, get_background_color=[255, 255, 255, 230]),
            pdk.Layer("ScatterplotLayer", [dict(pos=rt["here"], name="You are here", info=rt["name"])],
                      get_position="pos", get_radius=200, get_fill_color=[110, 30, 70], stroked=True,
                      get_line_color=[255, 255, 255], line_width_min_pixels=3, radius_min_pixels=8, pickable=True),
        ]

    layers.append(pdk.Layer("TextLayer", label_rows, get_position="pos", get_text="label", get_size=16,
                            get_color=[110, 30, 70], font_weight=700, background=True,
                            get_background_color=[255, 255, 255, 200]))

    if area == "All Jaipur":
        view = pdk.ViewState(longitude=C.CENTER[0], latitude=C.CENTER[1], zoom=11.3, pitch=0)
    else:
        lon, lat = C.ZONE_CENTROIDS[area]
        view = pdk.ViewState(longitude=lon, latitude=lat, zoom=12.6, pitch=0)
    deck = pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto", map_style="light",
                    tooltip={"html": "<b>{name}</b><br/>{info}",
                             "style": {"backgroundColor": INDIGO, "color": SAND, "fontFamily": "Hind, sans-serif",
                                       "fontSize": "13px", "borderRadius": "8px", "padding": "8px 10px"}})

    col_map, col_side = st.columns([2.1, 1], gap="large")
    with col_map:
        stretch(st.pydeck_chart, deck)
        legend = {
            "Pulse": [(LEAF, "Calm area / free road"), (SAFFRON, "Busy"), (RANI, "Stressed / jammed"),
                      (PURPLE, "Reports (size = severity)")],
            "Weather": [(POTTERY, "Darker blue = more rain"), ("#145AAA", "Runoff direction"),
                        (POTTERY, "Circle = waterlogging risk")],
            "Route": [(SAFFRON, "Route ahead"), ("#968CA5", "Already travelled"), (RANI, "Upcoming hurdle"),
                      (INDIGO, "You")],
            "Ground reports": [(POTTERY, "Waterlogging"), (PURPLE, "Power / signal"), (RANI, "VIP movement"),
                               (SAFFRON, "Baraat / procession"), ("#D22832", "Accident")],
        }[view_mode]
        md('<div class="cp-legend">' + "".join(
            f'<span><span class="cp-sw" style="background:{c}"></span>{esc(l)}</span>' for c, l in legend) + "</div>")

    with col_side:
        if view_mode == "Pulse":
            md('<div class="cp-h">Possible links</div>'
               '<div class="cp-sub">Events that line up in time and place. Not confirmed causes.</div>')
            if not snap["chains"]:
                item(LEAF, "Nothing looks connected right now."
                     + (" Move the replay slider to watch the rain spread." if meta["mode"] == "replay" else ""))
            for c in snap["chains"][:3]:
                steps = '<div class="cp-arrow">&#8595;</div>'.join(
                    f'<div class="cp-step">{esc(s)}</div>' for s in c["steps"])
                ev = f'<div class="cp-evidence">{esc(c["evidence"]["text"])}</div>' if c.get("evidence") else ""
                md(f'<div class="cp-chain cp-{c["color"]}"><div class="cp-chain-tag">Possible link, '
                   f'{c["strength"]} match</div>{steps}<div class="cp-note">{esc(c["note"])}</div>{ev}</div>')
            if snap["anomalies"]:
                md('<div class="cp-h" style="margin-top:6px">Unusual right now</div>'
                   '<div class="cp-sub">Compared with the last few hours of the same feed.</div>')
                for a in snap["anomalies"][:3]:
                    item(RANI, esc(a["message"]))
            md('<div class="cp-h" style="margin-top:6px">Known in advance</div>')
            for c in snap["calendar"][:2]:
                item(SAFFRON, f'<b>{esc(c["what"])}</b><br/>{esc(c["when"])}, {esc(c["where"])}<br/>'
                              f'<small>{esc(c["why"])}</small>')

        elif view_mode == "Weather":
            md('<div class="cp-h">Rain by direction</div>')
            tiles = ""
            for z in snap["zones"]:
                fc = z.get("forecast") or {}
                nxt = f"<br/><span>Next hour: up to {fc['next_60']} mm/hr</span>" if fc else ""
                tiles += (f'<div class="cp-zone cp-weather"><span>{z["zone"]}</span><br/><b>{z["rain"]}</b> '
                          f'<span>mm/hr</span><br/><span>{fmt(z.get("temp"), " C")}, AQI {fmt(z.get("aqi"))}, '
                          f'{fmt(z.get("humidity"), "% humid")}</span>{nxt}</div>')
            md(f'<div class="cp-zones">{tiles}</div>')
            md('<div class="cp-h">Where the water goes</div>'
               '<div class="cp-sub">Travel times are estimates from slope and rainfall.</div>')
            for f in sorted(snap["flows"], key=lambda f: -f["level"]):
                bar = {"high": RANI, "medium": SAFFRON, "low": LEAF}[f["risk"]]
                item(bar, f'<b>{f["src"]} to {esc(f["hotspot"])}</b> ({f["zone"]})<br/>'
                          f'About {f["lag"][0]} to {f["lag"][1]} min, risk {f["risk"]}<br/>'
                          f'<small>Roads to watch: {esc(", ".join(f["roads"]))}</small>')

        elif view_mode == "Route":
            upcoming = [h for h in rt["hurdles"] if h["upcoming"]]
            md(f'<div class="cp-h">{esc(rt["name"])}</div>'
               f'<div class="cp-eta"><div><b>{rt["eta_left"]} min</b>left</div><div><b>{rt["avg_speed"]}</b>'
               f'km/h average</div><div><b>{len(upcoming)}</b>hurdles ahead</div></div>')
            if not upcoming:
                item(LEAF, "Clear road ahead. Nothing reported along the rest of this route.")
            for h in upcoming:
                badge = ('<span class="cp-badge cp-ok">verified</span>' if h["verified"]
                         else '<span class="cp-badge cp-un">unverified</span>')
                item(RANI, f'<b>{esc(h["kind"])}</b>{badge}<br/>{esc(h["where"])}<br/>'
                           f'<small>{max(0, h["ahead_km"])} km ahead</small>')
            for h in rt["hurdles"]:
                if not h["upcoming"]:
                    item("#968CA5", f'{esc(h["kind"])}, {esc(h["where"])}<br/><small>Already passed</small>', dim=True)
            md('<div class="cp-h" style="margin-top:6px">Plan ahead</div>')
            for c in rt["plan"]:
                item(SAFFRON, f'<b>{esc(c["what"])}</b>, {esc(c["when"])}<br/><small>{esc(c["where"])}</small>')

        else:  # Ground reports
            md('<div class="cp-h">Ground reports</div>'
               f'<div class="cp-sub">{len(active)} active, {sum(r["verified"] for r in active)} verified</div>')
            with st.expander("Report something", expanded=False):
                if not backend_up:
                    st.caption("Reporting needs the backend. Start it with python3 run.py")
                else:
                    with st.form("new_report", clear_on_submit=True):
                        rtype = st.selectbox("What's happening?", [x for x in C.REPORT_TYPES if x != "Rain alert"])
                        place = st.selectbox("Where?", list(C.PLACES))
                        sev = st.select_slider("How bad?", options=[1, 2, 3], value=2,
                                               format_func=lambda v: {1: "Minor", 2: "Slowing things", 3: "Serious"}[v])
                        note = st.text_input("Anything to add? (optional)", max_chars=200)
                        if st.form_submit_button("Send report"):
                            if not handle:
                                st.error("Add your handle in the sidebar first.")
                            else:
                                ok, res = client.post("/api/reports", dict(type=rtype, place=place, severity=sev,
                                                                            handle=handle, note=note))
                                if ok:
                                    st.session_state.flash = ("Thanks! Someone already reported this, so we counted "
                                                              "yours as a confirmation." if res.get("merged")
                                                              else "Report sent. It's on the map now.")
                                    st.rerun()
                                else:
                                    st.error(res)
            if st.session_state.get("flash"):
                st.success(st.session_state.pop("flash"))
            kinds = sorted({r["type"] for r in reports})
            pick = st.multiselect("Show", kinds, default=kinds, label_visibility="collapsed")
            shown = [r for r in reports if r["type"] in pick]
            if not shown:
                item(PURPLE, "No reports right now. Be the first: use Report something above.")
            for r in shown:
                rgb = r["color"]
                badge = ('<span class="cp-badge cp-bad">disputed</span>' if r["disputed"] else
                         '<span class="cp-badge cp-ok">verified</span>' if r["verified"] else
                         '<span class="cp-badge cp-un">unverified</span>')
                if r.get("live"):
                    badge += '<span class="cp-badge cp-new">live</span>'
                who = f"@{r['reporter']}, " if r["reporter"] else ""
                why = f'<br/><small>{esc("; ".join(r["support"]))}</small>' if r["support"] else ""
                item(f"rgb({rgb[0]},{rgb[1]},{rgb[2]})",
                     f'<b>{esc(r["type"])}</b>{badge}<br/>{esc(r["place"])}<br/>'
                     f'<small>{r["ago"]} min ago, {esc(who)}{esc(r["source"])}</small>{why}',
                     dim=r["disputed"])
                if r.get("live") and backend_up and r["status"] == "active":
                    b1, b2, _ = st.columns([1, 1, 1.2])
                    for col, action, label in [(b1, "confirm", "Still there"), (b2, "dispute", "Not true")]:
                        if col.button(label, key=f"{action}_{r['id']}"):
                            if not handle:
                                st.error("Add your handle in the sidebar first.")
                            else:
                                ok, res = client.post(f"/api/reports/{r['id']}/{action}", dict(handle=handle))
                                if ok:
                                    st.session_state.flash = "Thanks, vote counted."
                                    st.rerun()
                                else:
                                    st.error(res)

    # ---------------- trends (chart A / B / C, like the original dashboard)
    md(f'<div class="cp-h" style="margin-top:18px">'
       f'{"How the evening unfolded" if meta["mode"] == "replay" else "Last 3 hours"}, {esc(area)}</div>')
    if snap["timeseries"]:
        ts = pd.DataFrame(snap["timeseries"]).set_index("time")
        zones = C.ZONES if area == "All Jaipur" else [area]
        colors = ZONE_COLORS if area == "All Jaipur" else [ZONE_COLORS[C.ZONES.index(area)]]
        ca, cb, cc = st.columns(3)
        for col, key, title in [(ca, "rain", "Rain (mm/hr)"), (cb, "speed", "Average road speed (km/h)"),
                                (cc, "reports", "Active reports")]:
            with col:
                st.markdown(f"**{title}**")
                df = ts[[f"{key}_{z}" for z in zones]].rename(columns=lambda c: c.split("_", 1)[1])
                try:
                    st.line_chart(df, height=210, color=colors)
                except Exception:
                    st.line_chart(df, height=210)
    else:
        st.caption("History builds up while the backend runs. Check back in a few minutes.")

    if backend_up:
        with st.expander("Data sources behind this view"):
            rows = client.get("/api/streams", default=[]) or []
            if rows:
                df = pd.DataFrame(rows)[["name", "kind", "provider", "zone", "unit", "last_seen", "last_error"]]
                stretch(st.dataframe, df, hide_index=True)

# ================================================================ AI NAVI
with tab_navi:
    if "chat" not in st.session_state:
        st.session_state.chat = []
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        history = st.container()
        chips = {"Weather": "How is the weather and where is water going?",
                 "My route": "What's coming up on my route?",
                 "Incidents": "What incidents are reported right now?",
                 "Why is it slow?": "Why is traffic slow? Are things connected?",
                 "Anything unusual?": "Is anything unusual right now?"}
        asked = None
        for c, (label, q) in zip(st.columns(len(chips)), chips.items()):
            if c.button(label, key=f"chip_{label}"):
                asked = q
        with st.form("ask_navi", clear_on_submit=True):
            typed = st.text_input("Ask Navi anything", placeholder="e.g. Tonk Road pe baarish ka kya haal hai?")
            if st.form_submit_button("Ask Navi") and typed.strip():
                asked = typed.strip()
        if asked:
            res = client.ask_navi(asked, mode, t, route_name, progress / 100, area, delayed)
            st.session_state.chat.append(("user", asked, None))
            st.session_state.chat.append(("assistant", res["answer"], res.get("engine")))
        with history:
            with st.chat_message("assistant", avatar="💗"):
                st.markdown(f"Namaste! Here is Jaipur at {meta['clock']}: {snap['summary']}\n\n"
                            "Do you want to know more about **weather**, your **route**, **incidents**, "
                            "or ask your own question?")
            for role, text, engine in st.session_state.chat:
                with st.chat_message(role, avatar="💗" if role == "assistant" else "🧭"):
                    st.markdown(text)
                    if engine:
                        st.caption("Answered by Claude from the feed data" if engine == "llm"
                                   else "Answered directly from the feed data")
    with right:
        md('<div class="cp-h">What Navi can see</div>')
        for f in snap["feeds"]:
            item(STATUS_DOT.get(f["status"], SAFFRON), f'<b>{esc(f["name"])}</b><br/><small>{esc(f.get("provider", ""))}, '
                                                       f'{esc(f["status"])}</small>')
        md('<div class="cp-rules"><b>How Navi answers</b><br/>Only from the feeds on this page, never guesses. '
           'Connections between events are shown as possible links, not proven causes. Understands simple Hindi '
           'and Hinglish words like baarish, raasta, jam and kal.</div>')
        if st.button("Clear conversation"):
            st.session_state.chat = []
            st.rerun()

# ================================================================ LEADERBOARD
with tab_board:
    board = snap["leaderboard"]
    md('<div class="cp-h">Top civic contributors</div>'
       '<div class="cp-sub">Points come from reports that others or official feeds confirmed. '
       "Handles only; nobody's real name or location history is shown.</div>")
    accents = ["pulse", "route", "weather"]
    md('<div class="cp-podium">' + "".join(
        f'<div class="cp-pod cp-{accents[i]}"><div class="rank">#{i + 1}</div>'
        f'<div class="who">@{esc(r["handle"])}</div>{esc(r["area"])}<br/>'
        f'<small>{r["points"]} points, {r["verified"]} verified reports, {esc(r["badge"])}</small></div>'
        for i, r in enumerate(board[:3])) + "</div>")
    if handle:
        mine = next((r for r in board if r["handle"] == handle), None)
        if mine:
            st.info(f"You're #{mine['rank']} with {mine['points']} points and a trust score of {mine['trust']:.2f}.")
    c1, c2 = st.columns([2, 1], gap="large")
    with c1:
        pick_area = st.selectbox("Area", ["All areas"] + sorted({r["area"] for r in board}))
        rows = [r for r in board if pick_area == "All areas" or r["area"] == pick_area]
        df = pd.DataFrame(rows)[["rank", "handle", "area", "points", "verified", "submitted", "accuracy",
                                 "trust", "badge"]]
        config = {
            "rank": "#", "handle": "Contributor", "area": "Area", "points": "Points", "verified": "Verified",
            "submitted": "Submitted", "badge": "Badge",
            "accuracy": st.column_config.NumberColumn("Accuracy", format="%d%%"),
            "trust": st.column_config.ProgressColumn("Trust score", min_value=0.0, max_value=1.0, format="%.2f"),
        }
        stretch(st.dataframe, df, hide_index=True, column_config=config)
    with c2:
        md('<div class="cp-rules"><b>How points work</b><br/>'
           '+10 when your report is confirmed by 3 residents or an official feed.<br/>'
           "+3 for confirming someone else's report.<br/>"
           '-5 if your report is disputed by most people who saw it.<br/>'
           "Reporting the same thing twice counts as a confirmation, not a new report, so spam doesn't pay.<br/><br/>"
           '<b>Trust score</b> mixes accuracy and track record. High-trust reports get verified faster.</div>')
