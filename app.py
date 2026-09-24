"""
CityPulse Jaipur - Python frontend (Streamlit + pydeck).
Run:  streamlit run app.py
Inspired by the CityPulse City Dashboard (map markers sized by value,
selectable data sources, historical charts), rebuilt for Jaipur with
Pulse / Weather / Route / Ground-report modes, AI Navi and a leaderboard.
"""
import html

import pandas as pd
import pydeck as pdk
import streamlit as st

import data as D

st.set_page_config(page_title="CityPulse Jaipur", page_icon="💗", layout="wide")

# ---------------------------------------------------------------- palette
INDIGO, RANI, POTTERY, SAFFRON = "#26185A", "#E0457B", "#1C8FB0", "#F08A24"
SAND, LEAF, PURPLE = "#FBF1E6", "#2E9E6A", "#7B3FC4"
MODE_ACCENT = {"Pulse": RANI, "Weather": POTTERY, "Route": SAFFRON, "Ground reports": PURPLE}
MODE_CLASS = {"Pulse": "pulse", "Weather": "weather", "Route": "route", "Ground reports": "reports"}
ZONE_COLORS = [POTTERY, RANI, SAFFRON, PURPLE]   # North, East, South, West

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Hind:wght@400;500;600&display=swap');
.stApp { background: #FBF1E6; }
.block-container { padding-top: 1.4rem; max-width: 1440px; }
h1, h2, h3 { font-family: 'Baloo 2', sans-serif !important; color: #26185A; }
[data-testid="stSidebar"] { background: #F5DFCB; }
.cp-brand { font-family: 'Baloo 2', sans-serif; font-weight: 800; font-size: 30px; color: #26185A; line-height: 1; }
.cp-brand-sub { font-family: 'Hind', sans-serif; color: #6B5A7E; font-size: 14px; margin: 4px 0 14px; }

.cp-hero { display: grid; grid-template-columns: 210px 1fr; gap: 28px; align-items: center;
  background: #26185A; color: #FBF1E6; border-radius: 22px; padding: 20px 28px 18px;
  border-bottom: 6px solid #E0457B; margin-bottom: 12px; }
.cp-city { font-family: 'Hind', sans-serif; font-size: 15px; opacity: .8; }
.cp-score { font-family: 'Baloo 2', sans-serif; font-weight: 800; font-size: 88px; line-height: .95; }
.cp-state { font-family: 'Baloo 2', sans-serif; font-weight: 600; font-size: 24px; margin-top: -4px; }
.cp-beat { width: 100%; height: 64px; display: block; }
.cp-beat polyline { stroke-dasharray: 1700; stroke-dashoffset: 1700; animation: cp-draw 3.4s linear infinite; }
@keyframes cp-draw { to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { .cp-beat polyline { animation: none; stroke-dashoffset: 0; } }
.cp-summary { font-family: 'Hind', sans-serif; font-size: 18px; line-height: 1.45; margin: 6px 0 10px; max-width: 75ch; }
.cp-pill { display: inline-flex; align-items: center; gap: 7px; background: rgba(251,241,230,.13);
  border-radius: 999px; padding: 3px 12px; margin: 0 8px 4px 0; font-family: 'Hind', sans-serif; font-size: 13.5px; }
.cp-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
@media (max-width: 760px) { .cp-hero { grid-template-columns: 1fr; } .cp-score { font-size: 64px; } }

.cp-weather { --acc: #1C8FB0; --tint: #E1F2F7; }
.cp-route   { --acc: #F08A24; --tint: #FDEBD6; }
.cp-reports { --acc: #7B3FC4; --tint: #EEE4FA; }
.cp-pulse   { --acc: #E0457B; --tint: #FBE1EA; }

.cp-modebar { font-family: 'Hind', sans-serif; font-size: 15px; color: #3A2D55; padding: 8px 14px;
  border-left: 6px solid var(--acc); background: var(--tint); border-radius: 10px; margin: 2px 0 12px; }
.cp-h { font-family: 'Baloo 2', sans-serif; font-weight: 700; font-size: 22px; color: #26185A; margin: 0 0 8px; }
.cp-sub { font-family: 'Hind', sans-serif; font-size: 14px; color: #6B5A7E; margin: -4px 0 10px; }

.cp-chain { background: #fff; border-left: 6px solid var(--acc); border-radius: 14px; padding: 12px 14px; margin-bottom: 12px; }
.cp-chain-tag { font-family: 'Hind', sans-serif; font-weight: 600; font-size: 13px; color: var(--acc); margin-bottom: 6px; }
.cp-step { font-family: 'Hind', sans-serif; font-size: 15px; color: #2A1F3D; background: var(--tint); padding: 6px 10px; border-radius: 8px; }
.cp-arrow { text-align: center; color: var(--acc); font-size: 16px; line-height: 1.2; }
.cp-note { font-family: 'Hind', sans-serif; font-size: 13px; color: #6B5A7E; margin-top: 6px; }

.cp-zones { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
.cp-zone { background: #fff; border-radius: 14px; padding: 10px 12px; border-top: 5px solid var(--acc); font-family: 'Hind', sans-serif; }
.cp-zone b { font-family: 'Baloo 2', sans-serif; font-size: 30px; color: #26185A; line-height: 1; }
.cp-zone span { color: #6B5A7E; font-size: 13.5px; }

.cp-item { display: flex; gap: 10px; background: #fff; border-radius: 12px; padding: 9px 12px; margin-bottom: 8px; font-family: 'Hind', sans-serif; font-size: 14.5px; color: #2A1F3D; }
.cp-bar { width: 6px; border-radius: 4px; flex: none; }
.cp-item small { color: #6B5A7E; font-size: 13px; }
.cp-badge { display: inline-block; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 999px; margin-left: 6px; }
.cp-ok { background: #DDF3E7; color: #1E7A4E; }
.cp-un { background: #F3E6D6; color: #8A5A1E; }
.cp-dim { opacity: .5; }

.cp-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-family: 'Hind', sans-serif; font-size: 13.5px; color: #3A2D55; margin-top: 6px; }
.cp-sw { width: 12px; height: 12px; border-radius: 3px; display: inline-block; margin-right: 6px; vertical-align: -1px; }

.cp-eta { display: flex; gap: 18px; background: #fff; border-radius: 14px; padding: 10px 14px; margin-bottom: 12px; font-family: 'Hind', sans-serif; }
.cp-eta b { font-family: 'Baloo 2', sans-serif; font-size: 34px; color: #26185A; line-height: 1; display: block; }

.cp-podium { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 14px; }
.cp-pod { background: #fff; border-radius: 16px; padding: 14px 16px; font-family: 'Hind', sans-serif; border-bottom: 6px solid var(--acc); }
.cp-pod .rank { font-family: 'Baloo 2', sans-serif; font-weight: 800; font-size: 40px; color: var(--acc); line-height: 1; }
.cp-pod .who { font-family: 'Baloo 2', sans-serif; font-weight: 700; font-size: 20px; color: #26185A; }
.cp-rules { background: #fff; border-radius: 14px; padding: 12px 16px; font-family: 'Hind', sans-serif; font-size: 14.5px; color: #2A1F3D; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s))


def stretch(fn, *args, **kwargs):
    """Full-width rendering that works on both old and new Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except Exception:
        return fn(*args, use_container_width=True, **kwargs)


def heartbeat_svg(stress, color):
    amp = 8 + stress * 30
    beat = [(0, 0), (40, 0), (48, -amp * .25), (56, 0), (64, 0), (70, amp * .35),
            (78, -amp), (86, amp * .5), (94, 0), (130, 0)]
    pts = " ".join(f"{k * 130 + dx},{44 + dy:.1f}" for k in range(5) for dx, dy in beat)
    return (f'<svg class="cp-beat" viewBox="0 0 650 88" preserveAspectRatio="none">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def stress_rgb(s):
    if s < 0.35:
        return [46, 158, 106]
    if s < 0.55:
        return [240, 138, 36]
    return [224, 69, 123]


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown('<div class="cp-brand">CityPulse</div>'
                '<div class="cp-brand-sub">Jaipur, one glance at a time</div>', unsafe_allow_html=True)
    t = st.slider("Replay the evening (minutes after 5 PM)", 0, 180, 95, step=5)
    st.caption(f"Showing Jaipur at **{D.clock(t)}**, monsoon evening replay")
    area = st.selectbox("Zoom to area", ["All Jaipur"] + D.ZONES)
    route_name = st.selectbox("Your route", list(D.ROUTES))
    progress = st.slider("How far along your trip (%)", 0, 100, 20, step=5)
    delayed = st.selectbox("Test a delayed feed", ["None", "Weather", "Traffic", "Ground reports"])
    st.caption("Data is simulated for the demo. Each feed can be swapped for a live API in data.py.")

delayed = None if delayed == "None" else delayed
tw = max(0, t - 12) if delayed == "Weather" else t
tt = max(0, t - 12) if delayed == "Traffic" else t
tr = max(0, t - 12) if delayed == "Ground reports" else t
reports = D.active_reports(tr)
score, state, stress = D.pulse(tw, tt, tr)
score_color = {"Calm": "#7FD8A6", "Busy": "#F7B267", "Stressed": "#F58BAE", "Critical": "#FF6B8B"}[state]

# ---------------------------------------------------------------- hero
pills = ""
for feed in ["Weather", "Traffic", "Ground reports"]:
    late = feed == delayed
    dot = SAFFRON if late else "#7FD8A6"
    pills += (f'<span class="cp-pill"><span class="cp-dot" style="background:{dot}"></span>'
              f'{feed}: {"12 min old" if late else "live"}</span>')
st.markdown(
    '<div class="cp-hero">'
    f'<div><div class="cp-city">Jaipur pulse at {D.clock(t)}</div>'
    f'<div class="cp-score" style="color:{score_color}">{score}</div>'
    f'<div class="cp-state">{state}</div></div>'
    f'<div>{heartbeat_svg(stress, score_color)}'
    f'<p class="cp-summary">{esc(D.summary(tw, tt, tr, delayed))}</p>{pills}</div>'
    '</div>', unsafe_allow_html=True)

tab_map, tab_navi, tab_board = st.tabs(["Live map", "AI Navi", "Civic contributors"])

# ================================================================ LIVE MAP
with tab_map:
    mode = st.radio("Mode", list(MODE_ACCENT), horizontal=True, label_visibility="collapsed")
    mcls = MODE_CLASS[mode]
    blurbs = {
        "Pulse": "Everything at once. Areas are tinted by how stressed they are; cards on the right show events that may be connected.",
        "Weather": "Rain by direction. Blue lines show where runoff from each area is likely to flow and roughly how long it takes.",
        "Route": "Your trip. The orange line is still ahead of you; pink markers are hurdles coming up.",
        "Ground reports": "What people and official feeds are reporting. Bigger circles mean more serious reports.",
    }
    st.markdown(f'<div class="cp-modebar cp-{mcls}">{blurbs[mode]}</div>', unsafe_allow_html=True)

    # ---------------- layers
    layers = []
    zone_rows, label_rows = [], []
    for z in D.ZONES:
        w = D.weather(z, tw)
        s = D.zone_stress(z, tw, tt, tr)
        if mode == "Weather":
            fill = [28, 143, 176, int(35 + min(1, w["rain"] / 22) * 150)]
            label = f"{z}\n{w['rain']} mm/hr"
        elif mode == "Pulse":
            fill = stress_rgb(s) + [85]
            label = f"{z}\nstress {int(s * 100)}"
        else:
            fill = [38, 24, 90, 14]
            label = z
        zone_rows.append(dict(polygon=[list(p) for p in D.zone_polygon(z)], fill=fill,
                              name=f"{z} Jaipur",
                              info=f"{D.rain_label(w['rain']).capitalize()}, {w['rain']} mm/hr<br/>"
                                   f"{w['temp']} C, AQI {w['aqi']}<br/>Stress {int(s * 100)}/100"))
        label_rows.append(dict(pos=list(D.ZONE_CENTROIDS[z]), label=label))
    layers.append(pdk.Layer("PolygonLayer", zone_rows, get_polygon="polygon", get_fill_color="fill",
                            get_line_color=[255, 255, 255, 230], line_width_min_pixels=2,
                            stroked=True, filled=True, pickable=True))

    road_alpha = 230 if mode in ("Pulse", "Route") else 110
    road_rows = []
    for road, pts in D.ROADS.items():
        c = D.congestion(road, tt, reports)
        road_rows.append(dict(path=[list(p) for p in pts], color=D.traffic_color(c) + [road_alpha],
                              name=road, info=f"{D.speed(road, tt, reports)} km/h, {int(c * 100)}% congested"))
    layers.append(pdk.Layer("PathLayer", road_rows, get_path="path", get_color="color",
                            get_width=6, width_units="pixels", cap_rounded=True, joint_rounded=True,
                            pickable=True))

    if mode == "Weather":
        flow_rows, spot_rows, eta_rows = [], [], []
        for f in D.FLOWS:
            lvl = D.water_level(f, tw)
            src = list(D.ZONE_CENTROIDS[f["src"]])
            dst = [f["lon"], f["lat"]]
            flow_rows.append(dict(src=src, dst=dst, width=3 + lvl * 9,
                                  name=f"Runoff: {f['src']} to {f['hotspot']}",
                                  info=f"Estimated {f['lag'][0]} to {f['lag'][1]} min<br/>"
                                       f"Roads: {', '.join(f['roads'])}"))
            spot_rows.append(dict(pos=dst, radius=250 + lvl * 700,
                                  color=[28, 143, 176, int(90 + lvl * 140)],
                                  name=f['hotspot'], info=f"Waterlogging risk: {D.risk_label(lvl)}"))
            eta_rows.append(dict(pos=[(src[0] + dst[0]) / 2, (src[1] + dst[1]) / 2],
                                 label=f"~{f['lag'][0]}-{f['lag'][1]} min"))
        layers += [
            pdk.Layer("LineLayer", flow_rows, get_source_position="src", get_target_position="dst",
                      get_color=[20, 90, 170, 220], get_width="width", width_units="pixels", pickable=True),
            pdk.Layer("ScatterplotLayer", spot_rows, get_position="pos", get_radius="radius",
                      get_fill_color="color", stroked=True, get_line_color=[255, 255, 255],
                      line_width_min_pixels=2, pickable=True),
            pdk.Layer("TextLayer", eta_rows, get_position="pos", get_text="label", get_size=13,
                      get_color=[20, 70, 140], background=True, get_background_color=[255, 255, 255, 220]),
        ]

    if mode in ("Pulse", "Ground reports"):
        rep_rows = [dict(pos=[r["lon"], r["lat"]], radius=140 + 170 * r["severity"],
                         color=D.REPORT_COLORS.get(r["type"], [100, 100, 100]) + [215],
                         name=r["type"],
                         info=f"{esc(r['place'])}<br/>{r['ago']} min ago via {esc(r['source'])}<br/>"
                              f"{'Verified' if r['verified'] else 'Unverified'}")
                    for r in reports]
        layers.append(pdk.Layer("ScatterplotLayer", rep_rows, get_position="pos", get_radius="radius",
                                get_fill_color="color", stroked=True, get_line_color=[255, 255, 255],
                                line_width_min_pixels=2, radius_min_pixels=5, pickable=True))

    hurdles = D.route_hurdles(route_name, tt, progress / 100, reports)
    if mode == "Route":
        done, ahead = D.split_route(D.ROUTES[route_name], progress / 100)
        here = D.point_at(D.ROUTES[route_name], progress / 100)
        layers += [
            pdk.Layer("PathLayer", [dict(path=[list(p) for p in done], name="Already travelled", info="")],
                      get_path="path", get_color=[150, 140, 165, 230], get_width=9, width_units="pixels",
                      cap_rounded=True, joint_rounded=True, pickable=True),
            pdk.Layer("PathLayer", [dict(path=[list(p) for p in ahead], name="Still ahead", info=route_name)],
                      get_path="path", get_color=[240, 138, 36, 245], get_width=10, width_units="pixels",
                      cap_rounded=True, joint_rounded=True, pickable=True),
            pdk.Layer("ScatterplotLayer",
                      [dict(pos=[h["lon"], h["lat"]], name=h["kind"],
                            info=f"{esc(h['where'])}<br/>"
                                 + (f"{max(0, h['ahead_km'])} km ahead" if h["upcoming"] else "Already passed"),
                            color=[224, 69, 123, 240] if h["upcoming"] else [160, 150, 170, 150])
                       for h in hurdles],
                      get_position="pos", get_radius=260, get_fill_color="color", stroked=True,
                      get_line_color=[255, 255, 255], line_width_min_pixels=2, radius_min_pixels=6,
                      pickable=True),
            pdk.Layer("TextLayer", [dict(pos=[h["lon"], h["lat"]], label=h["kind"]) for h in hurdles if h["upcoming"]],
                      get_position="pos", get_text="label", get_size=13, get_color=[38, 24, 90],
                      get_pixel_offset=[0, -20], background=True, get_background_color=[255, 255, 255, 230]),
            pdk.Layer("ScatterplotLayer", [dict(pos=list(here), name="You are here", info=route_name)],
                      get_position="pos", get_radius=200, get_fill_color=[38, 24, 90],
                      stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=3,
                      radius_min_pixels=8, pickable=True),
        ]

    layers.append(pdk.Layer("TextLayer", label_rows, get_position="pos", get_text="label", get_size=16,
                            get_color=[38, 24, 90], font_weight=700, background=True,
                            get_background_color=[255, 255, 255, 200]))

    if area == "All Jaipur":
        view = pdk.ViewState(longitude=D.CENTER[0], latitude=D.CENTER[1], zoom=11.3, pitch=0)
    else:
        lon, lat = D.ZONE_CENTROIDS[area]
        view = pdk.ViewState(longitude=lon, latitude=lat, zoom=12.6, pitch=0)
    deck = pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto", map_style="light",
                    tooltip={"html": "<b>{name}</b><br/>{info}",
                             "style": {"backgroundColor": INDIGO, "color": SAND, "fontFamily": "Hind, sans-serif",
                                       "fontSize": "13px", "borderRadius": "8px", "padding": "8px 10px"}})

    col_map, col_side = st.columns([2.1, 1], gap="large")
    with col_map:
        stretch(st.pydeck_chart, deck)
        legend = {
            "Pulse": [("#2E9E6A", "Calm area / free road"), (SAFFRON, "Busy"), (RANI, "Stressed / jammed"),
                      (PURPLE, "Reports (size = severity)")],
            "Weather": [(POTTERY, "Darker blue = more rain"), ("#145AAA", "Runoff direction"),
                        (POTTERY, "Circle = waterlogging risk")],
            "Route": [(SAFFRON, "Route ahead"), ("#968CA5", "Already travelled"), (RANI, "Upcoming hurdle"),
                      (INDIGO, "You")],
            "Ground reports": [(POTTERY, "Waterlogging"), (PURPLE, "Power / signal"), (RANI, "VIP movement"),
                               (SAFFRON, "Baraat"), ("#D22832", "Accident")],
        }[mode]
        st.markdown('<div class="cp-legend">' + "".join(
            f'<span><span class="cp-sw" style="background:{c}"></span>{esc(l)}</span>' for c, l in legend)
            + "</div>", unsafe_allow_html=True)

    with col_side:
        if mode == "Pulse":
            chains = D.cause_chains(tw, tt, tr)
            st.markdown('<div class="cp-h">Possible links</div>'
                        '<div class="cp-sub">Events that line up in time and place. Not confirmed causes.</div>',
                        unsafe_allow_html=True)
            if not chains:
                st.markdown('<div class="cp-item">Nothing looks connected right now. '
                            'Move the replay slider to watch the rain spread.</div>', unsafe_allow_html=True)
            for c in chains[:3]:
                steps = '<div class="cp-arrow">&#8595;</div>'.join(
                    f'<div class="cp-step">{esc(s)}</div>' for s in c["steps"])
                st.markdown(f'<div class="cp-chain cp-{c["color"]}"><div class="cp-chain-tag">'
                            f'Possible link, {c["strength"]} match</div>{steps}'
                            f'<div class="cp-note">{esc(c["note"])}</div></div>', unsafe_allow_html=True)
            st.markdown('<div class="cp-h" style="margin-top:6px">Known in advance</div>', unsafe_allow_html=True)
            for c in D.CALENDAR[:2]:
                st.markdown(f'<div class="cp-item"><span class="cp-bar" style="background:{SAFFRON}"></span>'
                            f'<div><b>{esc(c["what"])}</b><br/>{esc(c["when"])}, {esc(c["where"])}<br/>'
                            f'<small>{esc(c["why"])}</small></div></div>', unsafe_allow_html=True)

        elif mode == "Weather":
            st.markdown('<div class="cp-h">Rain by direction</div>', unsafe_allow_html=True)
            tiles = ""
            for z in D.ZONES:
                w = D.weather(z, tw)
                tiles += (f'<div class="cp-zone cp-weather"><span>{z}</span><br/><b>{w["rain"]}</b> '
                          f'<span>mm/hr</span><br/><span>{w["temp"]} C, AQI {w["aqi"]}, '
                          f'{w["humidity"]}% humid</span></div>')
            st.markdown(f'<div class="cp-zones">{tiles}</div>', unsafe_allow_html=True)
            st.markdown('<div class="cp-h">Where the water goes</div>'
                        '<div class="cp-sub">Travel times are estimates from slope and rainfall.</div>',
                        unsafe_allow_html=True)
            for f in sorted(D.FLOWS, key=lambda f: -D.water_level(f, tw)):
                lvl = D.water_level(f, tw)
                bar = {"high": RANI, "medium": SAFFRON, "low": LEAF}[D.risk_label(lvl)]
                st.markdown(f'<div class="cp-item"><span class="cp-bar" style="background:{bar}"></span><div>'
                            f'<b>{f["src"]} to {esc(f["hotspot"])}</b> ({f["zone"]})<br/>'
                            f'About {f["lag"][0]} to {f["lag"][1]} min, risk {D.risk_label(lvl)}<br/>'
                            f'<small>Roads to watch: {esc(", ".join(f["roads"]))}</small></div></div>',
                            unsafe_allow_html=True)

        elif mode == "Route":
            eta, v = D.route_eta(route_name, tt, reports)
            left = int(eta * (1 - progress / 100))
            st.markdown(f'<div class="cp-h">{esc(route_name)}</div>'
                        f'<div class="cp-eta"><div><b>{left} min</b>left</div><div><b>{v}</b>km/h average</div>'
                        f'<div><b>{sum(h["upcoming"] for h in hurdles)}</b>hurdles ahead</div></div>',
                        unsafe_allow_html=True)
            upcoming = [h for h in hurdles if h["upcoming"]]
            passed = [h for h in hurdles if not h["upcoming"]]
            if not upcoming:
                st.markdown('<div class="cp-item">Clear road ahead. Nothing reported along the rest of this route.</div>',
                            unsafe_allow_html=True)
            for h in upcoming:
                badge = ('<span class="cp-badge cp-ok">verified</span>' if h["verified"]
                         else '<span class="cp-badge cp-un">unverified</span>')
                st.markdown(f'<div class="cp-item"><span class="cp-bar" style="background:{RANI}"></span><div>'
                            f'<b>{esc(h["kind"])}</b>{badge}<br/>{esc(h["where"])}<br/>'
                            f'<small>{max(0, h["ahead_km"])} km ahead</small></div></div>', unsafe_allow_html=True)
            for h in passed:
                st.markdown(f'<div class="cp-item cp-dim"><span class="cp-bar" style="background:#968CA5"></span>'
                            f'<div>{esc(h["kind"])}, {esc(h["where"])}<br/><small>Already passed</small></div></div>',
                            unsafe_allow_html=True)
            near = D.route_roads(route_name)
            on_route = [c for c in D.CALENDAR if set(c["roads"]) & near][:2] or D.CALENDAR[:1]
            st.markdown('<div class="cp-h" style="margin-top:6px">Plan ahead</div>', unsafe_allow_html=True)
            for c in on_route:
                st.markdown(f'<div class="cp-item"><span class="cp-bar" style="background:{SAFFRON}"></span>'
                            f'<div><b>{esc(c["what"])}</b>, {esc(c["when"])}<br/>'
                            f'<small>{esc(c["where"])}</small></div></div>', unsafe_allow_html=True)

        else:  # Ground reports
            st.markdown('<div class="cp-h">Ground reports</div>'
                        f'<div class="cp-sub">{len(reports)} active, '
                        f'{sum(r["verified"] for r in reports)} verified</div>', unsafe_allow_html=True)
            kinds = sorted({r["type"] for r in reports})
            pick = st.multiselect("Show", kinds, default=kinds, label_visibility="collapsed")
            shown = [r for r in reports if r["type"] in pick]
            if not shown:
                st.markdown('<div class="cp-item">No reports match. Pick a type above or move the replay time.</div>',
                            unsafe_allow_html=True)
            for r in shown:
                rgb = D.REPORT_COLORS.get(r["type"], [100, 100, 100])
                badge = ('<span class="cp-badge cp-ok">verified</span>' if r["verified"]
                         else '<span class="cp-badge cp-un">unverified</span>')
                who = f"@{r['reporter']}, " if r["reporter"] else ""
                st.markdown(f'<div class="cp-item"><span class="cp-bar" style="background:rgb({rgb[0]},{rgb[1]},{rgb[2]})">'
                            f'</span><div><b>{esc(r["type"])}</b>{badge}<br/>{esc(r["place"])}<br/>'
                            f'<small>{r["ago"]} min ago, {esc(who)}{esc(r["source"])}, '
                            f'{r["corroborations"]} people confirmed</small></div></div>', unsafe_allow_html=True)

    # ---------------- trends (chart A / B / C, like the original dashboard)
    st.markdown(f'<div class="cp-h" style="margin-top:18px">How the evening unfolded, {esc(area)}</div>',
                unsafe_allow_html=True)
    ts = pd.DataFrame(D.timeseries(area, t)).set_index("time")
    zones = D.ZONES if area == "All Jaipur" else [area]
    colors = ZONE_COLORS if area == "All Jaipur" else [ZONE_COLORS[D.ZONES.index(area)]]
    ca, cb, cc = st.columns(3)
    for col, key, title in [(ca, "rain", "Rain (mm/hr)"), (cb, "speed", "Average road speed (km/h)"),
                            (cc, "reports", "Active reports")]:
        with col:
            st.markdown(f"**{title}**")
            df = ts[[f"{key}_{z}" for z in zones]].rename(columns=lambda c: c.split("_")[1])
            try:
                st.line_chart(df, height=210, color=colors)
            except Exception:
                st.line_chart(df, height=210)

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
                 "Why is it slow?": "Why is traffic slow? Are things connected?"}
        asked = None
        cols = st.columns(len(chips))
        for c, (label, q) in zip(cols, chips.items()):
            if c.button(label, key=f"chip_{label}"):
                asked = q
        with st.form("ask_navi", clear_on_submit=True):
            typed = st.text_input("Ask Navi anything",
                                  placeholder="e.g. Tonk Road pe baarish ka kya haal hai?")
            if st.form_submit_button("Ask Navi") and typed.strip():
                asked = typed.strip()
        if asked:
            st.session_state.chat.append(("user", asked))
            st.session_state.chat.append(
                ("assistant", D.answer(asked, tw, tt, tr, route_name, progress)))
        with history:
            with st.chat_message("assistant", avatar="💗"):
                st.markdown(f"Namaste! Here is Jaipur at {D.clock(t)}: {D.summary(tw, tt, tr, delayed)}\n\n"
                            "Do you want to know more about **weather**, your **route**, **incidents**, "
                            "or ask your own question?")
            for role, text in st.session_state.chat:
                with st.chat_message(role, avatar="💗" if role == "assistant" else "🧭"):
                    st.markdown(text)
    with right:
        st.markdown('<div class="cp-h">What Navi can see</div>', unsafe_allow_html=True)
        for feed in ["Weather", "Traffic", "Ground reports"]:
            late = feed == delayed
            st.markdown(f'<div class="cp-item"><span class="cp-bar" style="background:{SAFFRON if late else LEAF}">'
                        f'</span><div><b>{feed}</b><br/><small>{"12 min old, answers flag this" if late else "Live"}'
                        f'</small></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="cp-rules"><b>How Navi answers</b><br/>'
                    'Only from the feeds on this page, never guesses. Connections between events are shown as '
                    'possible links, not proven causes. Understands simple Hindi and Hinglish words like '
                    'baarish, raasta, jam and kal.</div>', unsafe_allow_html=True)
        if st.button("Clear conversation"):
            st.session_state.chat = []
            st.rerun()

# ================================================================ LEADERBOARD
with tab_board:
    board = D.leaderboard()
    st.markdown('<div class="cp-h">Top civic contributors this month</div>'
                '<div class="cp-sub">People whose reports were confirmed by others or by official feeds. '
                'Handles only; nobody\'s real name or location history is shown.</div>', unsafe_allow_html=True)
    accents = ["pulse", "route", "weather"]
    pods = "".join(
        f'<div class="cp-pod cp-{accents[i]}"><div class="rank">#{i + 1}</div>'
        f'<div class="who">@{esc(r["handle"])}</div>{esc(r["area"])}<br/>'
        f'<small>{r["points"]} points, {r["verified"]} verified reports, {esc(r["badge"])}</small></div>'
        for i, r in enumerate(board[:3]))
    st.markdown(f'<div class="cp-podium">{pods}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1], gap="large")
    with c1:
        areas = ["All areas"] + sorted({r["area"] for r in board})
        pick_area = st.selectbox("Area", areas)
        rows = [r for r in board if pick_area == "All areas" or r["area"] == pick_area]
        df = pd.DataFrame(rows)[["handle", "area", "points", "verified", "submitted", "accuracy", "trust", "badge"]]
        df.insert(0, "rank", range(1, len(df) + 1))
        config = {
            "handle": st.column_config.TextColumn("Contributor"),
            "area": "Area", "points": "Points", "verified": "Verified", "submitted": "Submitted",
            "accuracy": st.column_config.NumberColumn("Accuracy", format="%d%%"),
            "trust": st.column_config.ProgressColumn("Trust score", min_value=0.0, max_value=1.0, format="%.2f"),
            "badge": "Badge", "rank": "#",
        }
        stretch(st.dataframe, df, hide_index=True, column_config=config)
    with c2:
        st.markdown('<div class="cp-rules"><b>How points work</b><br/>'
                    '+10 when your report is confirmed by others or an official feed.<br/>'
                    '+3 for confirming someone else\'s report.<br/>'
                    '-5 if a report turns out to be false.<br/>'
                    'Reports sent while moving fast only count as voice reports, so nobody types while driving.<br/><br/>'
                    '<b>Trust score</b> mixes accuracy and track record. High-trust reports appear on the map faster.'
                    '</div>', unsafe_allow_html=True)
