from __future__ import annotations

import json
import textwrap
from html import escape as esc
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components


# APP CONFIG

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

st.set_page_config(
    page_title="Mahalnya Membangun Indonesia",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

css_path = ROOT / "style.css"
if css_path.exists():
    st.html(f"<style>{css_path.read_text(encoding='utf-8')}</style>")


# DESIGN TOKENS

INK = "#18242D"
BLUE = "#2D6FB7"
ORANGE = "#D88724"
GREEN = "#2B8A70"
PINK = "#C7678C"
SKY = "#63A6D8"
BROWN = "#A75D2A"

PULAU = ["Sumatera", "Jawa", "Bali & Nusa Tenggara", "Kalimantan", "Sulawesi", "Maluku & Papua"]
CMAP = dict(zip(PULAU, [BLUE, ORANGE, GREEN, PINK, SKY, BROWN]))

LOG_VARS = ["PDRB Konstruksi", "Jml Perusahaan", "Belanja Modal"]

# Tahun data. Hierarki tertinggal satu tahun karena keterbatasan rilis BPS.
YEAR_MAIN = 2025
YEAR_HIER = 2024

IKK_SCALE = [
    [0.00, "#F1F4F2"],
    [0.25, "#D4E4DD"],
    [0.50, "#91C2B4"],
    [0.75, "#4B988B"],
    [1.00, "#21626A"],
]

PLOTLY_CONFIG = {"displaylogo": False, "responsive": True, "scrollZoom": False}

MAP_CONFIG = {
    **PLOTLY_CONFIG,
    "scrollZoom": True,
    "doubleClick": "reset",
    "modeBarButtonsToRemove": ["select2d", "lasso2d"],
}

HAS_MAPLIBRE = hasattr(go, "Choroplethmap") and hasattr(go, "Scattermap")
ChoroplethMap = go.Choroplethmap if HAS_MAPLIBRE else go.Choroplethmapbox
ScatterMap = go.Scattermap if HAS_MAPLIBRE else go.Scattermapbox

DEFAULT_CENTER = dict(lat=-2.5, lon=118)
DEFAULT_ZOOM = 3.15
ALL_PROV = "Semua provinsi"


# HELPERS

def html(content: str) -> None:
    st.html(textwrap.dedent(content).strip())


def run_js(script: str) -> None:
    components.html(f"<script>{textwrap.dedent(script)}</script>", height=0, width=0)


def fmt_id(value, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def pct_text(value, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 100:.{decimals}f}%".replace(".", ",")


def rp_miliar(v) -> str:
    return "—" if v is None or pd.isna(v) else f"Rp{fmt_id(v, 0)} miliar"


def wrap_label(text: str, width: int = 13) -> str:
    return "<br>".join(textwrap.wrap(str(text), width)) or str(text)


SOURCE_BPS = "Badan Pusat Statistik (BPS)"
SOURCE_SIKD = "Kementerian Keuangan RI — SIKD"

SOURCE_LINES = {
    "geo": f"{SOURCE_BPS} · Data {YEAR_MAIN} · Diakses & Diolah 01-10-2026",
    "hier": f"{SOURCE_BPS} · Data {YEAR_HIER}* · Diakses & Diolah 01-10-2026",
    "multi": f"{SOURCE_BPS} · {SOURCE_SIKD} · Data {YEAR_MAIN} · Diakses & Diolah 01-10-2026",
}


def source_note(group: str = "geo") -> None:
    flag = (
        f'<span class="year-flag">* Data hierarki memakai tahun {YEAR_HIER}, bukan '
        f"{YEAR_MAIN} seperti data lain, karena keterbatasan data BPS.</span>"
        if group == "hier"
        else ""
    )
    html(f'<div class="source-note">Sumber: {esc(SOURCE_LINES.get(group, SOURCE_BPS))} {flag}</div>')


def base_layout(fig: go.Figure, height: int = 500, margin: dict | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        title=None,
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", color=INK, size=12),
        margin=margin or dict(l=24, r=24, t=24, b=24),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color=INK, bordercolor="#D9E0E4"),
    )
    return fig


def apply_map_layout(fig, height=520, center=None, zoom=DEFAULT_ZOOM, revision="map") -> None:
    key = "map" if HAS_MAPLIBRE else "mapbox"
    fig.update_layout(
        **{key: dict(style="carto-positron", center=center or DEFAULT_CENTER, zoom=zoom)},
        height=height,
        autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        dragmode="pan",
        hovermode="closest",
        uirevision=revision,
    )


def view_for(df: pd.DataFrame, min_span: float = 0.6) -> tuple[dict, float]:
    d = df.dropna(subset=["lon", "lat"])
    if d.empty:
        return DEFAULT_CENTER, DEFAULT_ZOOM

    lon0, lon1 = float(d["lon"].min()), float(d["lon"].max())
    lat0, lat1 = float(d["lat"].min()), float(d["lat"].max())
    span_lon = max(lon1 - lon0, min_span) * 1.5
    span_lat = max(lat1 - lat0, min_span) * 1.5

    z_lon = np.log2(700 * 360 / (512 * span_lon))
    z_lat = np.log2(520 * 360 / (512 * span_lat))
    zoom = float(np.clip(min(z_lon, z_lat), 3.0, 8.0))
    return dict(lat=(lat0 + lat1) / 2, lon=(lon0 + lon1) / 2), zoom


def toolbar(kicker: str, title: str, hint: str = ""):
    try:
        head, ctrl = st.columns([1, 0.46], gap="small", vertical_alignment="center")
    except TypeError:
        head, ctrl = st.columns([1, 0.46], gap="small")

    hint_html = f"<small>{hint}</small>" if hint else ""
    with head:
        html(
            f"""
            <div class="visual-intro">
                <span>{kicker}</span>
                <strong>{title}</strong>
                {hint_html}
            </div>
            """
        )
    return ctrl


def pop_label(base: str, n: int = 0) -> str:
    return f"{base} · {n}" if n else base


def tip_card(title: str, subtitle: str = "", rows: list[tuple[str, str]] | None = None) -> str:
    sub = f'<div class="tip-sub">{esc(str(subtitle))}</div>' if subtitle else ""
    body = "".join(
        f'<div class="tip-row"><span>{esc(str(k))}</span><b>{v}</b></div>' for k, v in (rows or [])
    )
    return f'<div class="tip-name">{esc(str(title))}</div>{sub}{body}'


def attach_hierarchy_tooltips(fig: go.Figure) -> go.Figure:
    for trace in fig.data:
        labels = list(trace.labels) if trace.labels is not None else []
        parents = list(trace.parents) if trace.parents is not None else []
        values = list(trace.values) if trace.values is not None else []
        marker = getattr(trace, "marker", None)
        colors = list(marker.colors) if marker is not None and marker.colors is not None else []

        tips = []
        for i, label in enumerate(labels):
            parent = parents[i] if i < len(parents) else ""
            value = values[i] if i < len(values) else np.nan
            color = colors[i] if i < len(colors) else np.nan
            path = str(parent).replace("/", " → ") if parent else "Indonesia"

            rows = [("Nilai", f"Rp{fmt_id(value, 1)} T")]
            if color is not None and not pd.isna(color):
                rows.append(("Porsi sipil", f"{fmt_id(color, 1)}%"))
            tips.append(tip_card(str(label), path, rows))

        trace.customdata = np.asarray(tips, dtype=object)
        trace.hoverinfo = "none"
        trace.hovertemplate = None
    return fig


def get_main_ring(geometry: dict) -> np.ndarray | None:
    if not geometry:
        return None
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    try:
        if geom_type == "Polygon":
            rings = [ring for ring in coords if ring]
        elif geom_type == "MultiPolygon":
            rings = [poly[0] for poly in coords if poly and poly[0]]
        else:
            return None
        if not rings:
            return None
        arr = np.asarray(max(rings, key=len), dtype=float)
        return arr if arr.ndim == 2 and arr.shape[1] >= 2 else None
    except Exception:
        return None


# DATA

@st.cache_data(show_spinner=False)
def load_data():
    required = [DATA / "kabkota.geojson", DATA / "hierarki.json", DATA / "multivariat.json"]
    missing = [p.name for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("File data tidak ditemukan: " + ", ".join(missing))

    with open(DATA / "kabkota.geojson", encoding="utf-8") as f:
        geojson = json.load(f)

    geo_rows = []
    for feature in geojson.get("features", []):
        props = dict(feature.get("properties", {}))
        ring = get_main_ring(feature.get("geometry", {}))
        props["lon"] = float(np.nanmean(ring[:, 0])) if ring is not None else np.nan
        props["lat"] = float(np.nanmean(ring[:, 1])) if ring is not None else np.nan
        geo_rows.append(props)

    with open(DATA / "hierarki.json", encoding="utf-8") as f:
        hierarchy = pd.DataFrame(json.load(f))

    with open(DATA / "multivariat.json", encoding="utf-8") as f:
        raw = json.load(f)

    multi = pd.DataFrame(
        [
            {"provinsi": r["provinsi"], "pulau": r["pulau"], **dict(zip(raw["vars"], r["v"]))}
            for r in raw["rows"]
        ]
    )
    return geojson, pd.DataFrame(geo_rows), hierarchy, multi, list(raw["vars"]), list(raw.get("dropped", []))


try:
    GEOJSON, GEO, HIER, MULTI, VARS, DROPPED = load_data()
except Exception as exc:
    st.error("Aplikasi gagal membaca data.")
    st.code(str(exc))
    st.stop()

missing_geo = {"id", "nama", "prov", "ikk", "pdrb_f", "share"} - set(GEO.columns)
missing_hier = {"pulau", "provinsi", "Gedung", "Sipil", "Khusus"} - set(HIER.columns)
if missing_geo:
    st.error("Kolom GeoJSON kurang: " + ", ".join(sorted(missing_geo)))
    st.stop()
if missing_hier:
    st.error("Kolom hierarki kurang: " + ", ".join(sorted(missing_hier)))
    st.stop()


def make_tip(r) -> str:
    return tip_card(
        r["nama"],
        r["prov"],
        [
            ("IKK", fmt_id(r["ikk"], 1)),
            ("PDRB konstruksi", rp_miliar(r["pdrb_f"])),
            ("Porsi konstruksi", f"{fmt_id(r['share'], 2)}%"),
        ],
    )


GEO = GEO.assign(
    tip=GEO.apply(make_tip, axis=1),
    rank_ikk=GEO["ikk"].rank(ascending=False, method="min"),
    rank_pdrb=GEO["pdrb_f"].rank(ascending=False, method="min"),
    rank_share=GEO["share"].rank(ascending=False, method="min"),
)
N_IKK = int(GEO["ikk"].notna().sum())
N_PDRB = int(GEO["pdrb_f"].notna().sum())
N_SHARE = int(GEO["share"].notna().sum())
MED_IKK = float(GEO["ikk"].median())
MED_SHARE = float(GEO["share"].median())


# ANGKA KUNCI

N_WILAYAH = 514

valid_ikk = GEO.dropna(subset=["ikk"])
highest = valid_ikk.loc[valid_ikk["ikk"].idxmax()]
lowest = valid_ikk.loc[valid_ikk["ikk"].idxmin()]

valid_market = GEO.dropna(subset=["pdrb_f"])
top_market = valid_market.loc[valid_market["pdrb_f"].idxmax()]
same_place = highest["id"] == top_market["id"]

ikk_ratio = float(highest["ikk"]) / float(lowest["ikk"]) if float(lowest["ikk"]) > 0 else np.nan

pair = GEO.dropna(subset=["ikk", "pdrb_f"])
rho = float(pair["ikk"].rank().corr(pair["pdrb_f"].rank()))

rank_highest = (
    int((valid_market["pdrb_f"] > highest["pdrb_f"]).sum() + 1) if pd.notna(highest["pdrb_f"]) else None
)

top10 = valid_market.nlargest(10, "pdrb_f")
share10 = float(top10["pdrb_f"].sum() / valid_market["pdrb_f"].sum())
share_regions10 = 10 / max(len(valid_market), 1)
top3_names = [esc(str(n)) for n in top10["nama"].head(3)]

hi_name, hi_prov = esc(str(highest["nama"])), esc(str(highest["prov"]))
lo_name, lo_prov = esc(str(lowest["nama"])), esc(str(lowest["prov"]))
tm_name, tm_prov = esc(str(top_market["nama"])), esc(str(top_market["prov"]))

hi_text = fmt_id(highest["ikk"], 1)
lo_text = fmt_id(lowest["ikk"], 1)
tm_text = "Rp" + fmt_id(float(top_market["pdrb_f"]) / 1000, 1) + " T"


# HERO

hero_second = (
    "Yang termahal bukan yang terbesar, dan yang terbesar belum tentu yang paling khas."
    if not same_place
    else "Dan di beberapa tempat, ketiganya memang bertemu."
)

NAV_LINKS = """
    <a href="#opening">Gambaran awal</a>
    <a href="#chapter-1">Biaya</a>
    <a href="#chapter-2">Struktur pasar</a>
    <a href="#chapter-3">Profil provinsi</a>
    <a href="#methodology">Data &amp; metode</a>
"""

html(
    f"""
    <section id="top" class="hero-cover">
        <div class="hero-overlay"></div>
        <div class="hero-spot"></div>

        <div class="hero-content">
            <div class="eyebrow">KONSTRUKSI INDONESIA · DATA BPS &amp; KEMENKEU</div>

            <h1>
                Wajah konstruksi Indonesia
                <span><i>tidak pernah seragam.</i></span>
            </h1>

            <p class="hero-lead">
                Di <strong>{N_WILAYAH} kabupaten/kota</strong>, biaya membangun,
                besarnya pasar, dan karakter industri tidak bergerak bersama.
                {hero_second}
            </p>

            <div class="hero-actions">
                <a class="hero-btn primary" href="#opening">Mulai membaca <span>↓</span></a>
                <a class="hero-btn secondary" href="#chapter-1">Langsung ke peta <span>↗</span></a>
            </div>
        </div>

        <div class="hero-nav-dock">
            <nav class="story-nav story-nav--hero">{NAV_LINKS}</nav>
        </div>
    </section>
    """
)


# NAV STICKY + INTERAKSI (nav, progres, tooltip visual)

html(
    f"""
    <div class="story-progress"><i></i></div>

    <div id="story-nav-sticky" class="story-nav-zone">
        <nav class="story-nav story-nav--top">{NAV_LINKS}</nav>
    </div>

    <a class="to-top-fab" href="#top" aria-label="Kembali ke atas">↑</a>
    """
)

run_js(
    """
    (function () {
      const win = window.parent;
      const doc = win.document;

      /* ---------- tooltip visual: modern + mengikuti kursor ---------- */
      if (!win.__storyTip) {
        win.__storyTip = (function () {
          let tip = doc.querySelector(".map-tip");
          if (!tip) {
            tip = doc.createElement("div");
            tip.className = "map-tip";
            tip.setAttribute("role", "tooltip");
            doc.body.appendChild(tip);
          }

          let mx = 0, my = 0, on = false, activePlot = null;

          function place() {
            const w = tip.offsetWidth, h = tip.offsetHeight;
            let x = mx + 16, y = my + 18;
            if (x + w > win.innerWidth - 8) { x = mx - w - 16; }
            if (y + h > win.innerHeight - 8) { y = my - h - 14; }
            tip.style.transform =
              "translate3d(" + Math.max(8, x) + "px," + Math.max(8, y) + "px,0)";
          }

          function show(h, gd) {
            if (!h || typeof h !== "string") { return; }
            if (tip.innerHTML !== h) { tip.innerHTML = h; }
            activePlot = gd || null;
            on = true;
            tip.classList.add("is-on");
            place();
          }

          function hide() {
            on = false;
            activePlot = null;
            tip.classList.remove("is-on");
          }

          // HTML tooltip bisa datang dari customdata (string / array) atau text.
          function htmlFromPoint(p) {
            if (!p) { return ""; }
            if (typeof p.customdata === "string") { return p.customdata; }
            if (Array.isArray(p.customdata)) {
              for (let i = p.customdata.length - 1; i >= 0; i--) {
                const c = p.customdata[i];
                if (typeof c === "string" && c.includes("tip-")) { return c; }
              }
            }
            if (typeof p.text === "string" && p.text) { return p.text; }
            if (p.data && p.data.text) {
              const t = Array.isArray(p.data.text) ? p.data.text[p.pointNumber] : p.data.text;
              if (typeof t === "string") { return t; }
            }
            return "";
          }

          doc.addEventListener("mousemove", function (e) {
            mx = e.clientX; my = e.clientY;
            if (!on) { return; }
            if (!activePlot || !activePlot.contains(e.target)) { hide(); return; }
            if (e.target.closest && e.target.closest(".modebar")) { hide(); return; }
            place();
          }, true);

          function bind() {
            doc.querySelectorAll(".js-plotly-plot").forEach(function (gd) {
              if (gd.__tipBound || typeof gd.on !== "function") { return; }
              gd.__tipBound = true;

              gd.on("plotly_hover", function (ev) {
                const h = htmlFromPoint(ev && ev.points && ev.points[0]);
                if (h) { show(h, gd); }
              });
              ["plotly_unhover", "plotly_relayouting", "plotly_relayout", "plotly_doubleclick"]
                .forEach(function (name) { gd.on(name, hide); });

              ["mouseleave", "pointerleave", "pointerdown"].forEach(function (name) {
                gd.addEventListener(name, hide, true);
              });
              gd.addEventListener("wheel", hide, { passive: true, capture: true });
            });
          }

          return { bind: bind, hide: hide };
        })();
      }

      /* ---------- nav, progres, spotlight ---------- */
      if (win.__storyCleanup) {
        try { win.__storyCleanup(); } catch (e) {}
      }

      const IDS = ["opening", "chapter-1", "chapter-2", "chapter-3", "methodology"];
      const reduce = win.matchMedia && win.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const behavior = reduce ? "auto" : "smooth";
      const q = function (s) { return doc.querySelector(s); };

      // Streamlit men-scroll <section data-testid="stMain">, bukan window
      function scroller() {
        return q('[data-testid="stMain"]') || q("section.main") || doc.scrollingElement;
      }

      function update() {
        const hero = q(".hero-cover");
        const zone = q("#story-nav-sticky");
        const fab = q(".to-top-fab");
        const bar = q(".story-progress > i");
        const sc = scroller();
        if (!hero || !zone || !sc) { return; }

        const past = hero.getBoundingClientRect().bottom <= 90;
        zone.classList.toggle("is-visible", past);
        if (fab) { fab.classList.toggle("is-visible", past); }

        if (bar) {
          const max = sc.scrollHeight - sc.clientHeight;
          bar.style.width = (max > 0 ? Math.min(100, Math.max(0, sc.scrollTop / max * 100)) : 0) + "%";
        }

        let active = null;
        IDS.forEach(function (id) {
          const el = doc.getElementById(id);
          if (el && el.getBoundingClientRect().top <= 170) { active = id; }
        });
        if (sc.scrollHeight - sc.clientHeight - sc.scrollTop < 4 && sc.scrollTop > 0) {
          active = "methodology";
        }

        doc.querySelectorAll(".story-nav a").forEach(function (a) {
          const isOn = active && a.getAttribute("href") === "#" + active;
          a.classList.toggle("is-active", !!isOn);
          if (isOn) { a.setAttribute("aria-current", "true"); }
          else { a.removeAttribute("aria-current"); }
        });

        const act = q(".story-nav--top a.is-active");
        if (act && past) {
          const nav = act.parentElement;
          nav.scrollTo({ left: act.offsetLeft - (nav.clientWidth - act.clientWidth) / 2, behavior: "auto" });
        }

        if (win.__storyTip) { win.__storyTip.bind(); }
      }

      function onClick(e) {
        const a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
        if (!a) { return; }
        const id = (a.getAttribute("href") || "").slice(1);
        if (!id) { return; }

        const sc = scroller();
        if (id === "top") {
          e.preventDefault(); e.stopPropagation();
          sc.scrollTo({ top: 0, behavior: behavior });
          return;
        }
        const target = doc.getElementById(id);
        if (!target) { return; }
        e.preventDefault(); e.stopPropagation();
        target.scrollIntoView({ behavior: behavior, block: "start" });

        if (id === "methodology") {
          setTimeout(function () {
            const first = q("details.method-acc");
            if (first && !q("details.method-acc[open]")) { first.open = true; }
          }, 650);
        }
      }

      function onMove(e) {
        const hero = q(".hero-cover");
        if (!hero) { return; }
        const r = hero.getBoundingClientRect();
        if (e.clientY < r.top || e.clientY > r.bottom) { return; }
        hero.style.setProperty("--mx", (e.clientX - r.left) + "px");
        hero.style.setProperty("--my", (e.clientY - r.top) + "px");
        hero.classList.add("is-hovered");
      }

      doc.addEventListener("scroll", update, true);
      doc.addEventListener("click", onClick, true);
      doc.addEventListener("mousemove", onMove, { passive: true });
      win.addEventListener("resize", update);
      const timer = win.setInterval(update, 500);

      win.__storyCleanup = function () {
        doc.removeEventListener("scroll", update, true);
        doc.removeEventListener("click", onClick, true);
        doc.removeEventListener("mousemove", onMove);
        win.removeEventListener("resize", update);
        win.clearInterval(timer);
      };

      update();
      setTimeout(update, 300);
      setTimeout(update, 1200);
    })();
    """
)


# OPENING CARDS

html(
    f"""
    <section id="opening" class="opening-editorial">
        <div class="opening-editorial-grid">

            <div class="opening-numbers">
                <div class="opening-numbers-label">TIGA ANGKA PEMBUKA</div>

                <div class="opening-number-item">
                    <span class="stat-context">IKK tertinggi</span>
                    <strong class="stat-number">{hi_text}</strong>
                    <span class="stat-location">{hi_name} · {hi_prov}</span>
                </div>

                <div class="opening-number-item">
                    <span class="stat-context">IKK terendah</span>
                    <strong class="stat-number">{lo_text}</strong>
                    <span class="stat-location">{lo_name} · {lo_prov}</span>
                </div>

                <div class="opening-number-item">
                    <span class="stat-context">PDRB konstruksi terbesar</span>
                    <strong class="stat-number">{tm_text}</strong>
                    <span class="stat-location">{tm_name} · {tm_prov}</span>
                </div>
            </div>

            <div class="opening-copy-side">
                <div class="opening-copy-kicker">GAMBARAN AWAL</div>

                <p>
                    Jika hanya melihat satu angka nasional, industri konstruksi tampak
                    seperti satu pasar besar. Tetapi ketika kita turun ke tingkat
                    wilayah, gambarnya mulai berubah.
                </p>

                <p>
                    <strong>
                        Tempat yang mahal, tempat dengan pasar terbesar, dan tempat
                        dengan profil industri paling kuat tidak selalu sama.
                    </strong>
                </p>
            </div>
        </div>

        <div class="opening-big-question">
            <span>ARGUMEN</span>
            <h2>Mahal, besar, dan kuat belum tentu berada di tempat yang sama.</h2>
        </div>
    </section>
    """
)


# BAB I — BIAYA

ch1_title = (
    "Biaya dan skala pasar berjalan beriringan."
    if abs(rho) >= 0.5
    else "Termahal belum tentu terbesar."
)


def metric_item(label: str, value: str, sub: str = "") -> str:
    sub_html = f"<small>{sub}</small>" if sub else ""
    return f'<div class="rc-item"><span>{label}</span><strong>{value}</strong>{sub_html}</div>'


def region_panel(prov: str, kab: str | None) -> None:
    if prov == ALL_PROV:
        html(
            f"""
            <div class="rc-hint">
                <b>Jelajahi {N_WILAYAH} kabupaten/kota.</b>
                Pilih provinsi di atas, lalu pilih kabupaten/kota untuk melihat
                peringkat IKK dan PDRB konstruksinya secara nasional.
            </div>
            """
        )
        return

    pg = GEO[GEO["prov"] == prov]

    if kab is None:
        by_ikk = pg.dropna(subset=["ikk"])
        by_pdrb = pg.dropna(subset=["pdrb_f"])
        items = [metric_item("Kabupaten/kota", fmt_id(len(pg)), f"di {esc(prov)}")]

        if not by_ikk.empty:
            top = by_ikk.loc[by_ikk["ikk"].idxmax()]
            items.append(
                metric_item(
                    "IKK rata-rata",
                    fmt_id(by_ikk["ikk"].mean(), 1),
                    f"median nasional {fmt_id(MED_IKK, 1)}",
                )
            )
            items.append(
                metric_item("Termahal", esc(str(top["nama"])), f"IKK {fmt_id(top['ikk'], 1)}")
            )
        if not by_pdrb.empty:
            big = by_pdrb.loc[by_pdrb["pdrb_f"].idxmax()]
            share_nat = by_pdrb["pdrb_f"].sum() / valid_market["pdrb_f"].sum()
            items.append(
                metric_item(
                    "PDRB konstruksi",
                    "Rp" + fmt_id(by_pdrb["pdrb_f"].sum() / 1000, 1) + " T",
                    f"{pct_text(share_nat, 1)} dari nasional",
                )
            )
            items.append(
                metric_item("Terbesar", esc(str(big["nama"])), rp_miliar(big["pdrb_f"]))
            )

        html(
            f"""
            <div class="region-card">
                <div class="rc-head"><span>PROFIL PROVINSI</span><strong>{esc(prov)}</strong></div>
                <div class="rc-grid">{''.join(items)}</div>
            </div>
            """
        )
        return

    r = pg[pg["nama"] == kab].iloc[0]
    prov_mean = pg["ikk"].mean()
    delta = r["ikk"] - prov_mean if pd.notna(r["ikk"]) and pd.notna(prov_mean) else np.nan
    delta_txt = (
        f" · {'+' if delta >= 0 else '−'}{fmt_id(abs(delta), 1)} dari rata-rata provinsi"
        if pd.notna(delta)
        else ""
    )

    def rank_txt(rank, n):
        return "tanpa data" if pd.isna(rank) else f"peringkat {int(rank)} dari {n}"

    items = [
        metric_item("IKK", fmt_id(r["ikk"], 1), rank_txt(r["rank_ikk"], N_IKK) + delta_txt),
        metric_item("PDRB konstruksi", rp_miliar(r["pdrb_f"]), rank_txt(r["rank_pdrb"], N_PDRB)),
        metric_item(
            "Porsi konstruksi",
            f"{fmt_id(r['share'], 2)}%",
            rank_txt(r["rank_share"], N_SHARE) + f" · median {fmt_id(MED_SHARE, 2)}%",
        ),
    ]
    html(
        f"""
        <div class="region-card is-focus">
            <div class="rc-head"><span>PROFIL KABUPATEN/KOTA · {esc(prov).upper()}</span><strong>{esc(str(kab))}</strong></div>
            <div class="rc-grid">{''.join(items)}</div>
        </div>
        """
    )


c1_text, c1_vis = st.columns([0.82, 1.38], gap="large")

with c1_text:
    html(
        f"""
        <section id="chapter-1" class="chapter-split-copy chapter-accent-warm">
            <div class="chapter-mini-kicker">BAB I · BIAYA</div>

            <h2 class="chapter-mini-title">{ch1_title}</h2>

            <p class="chapter-mini-deck">
                IKK mengukur seberapa berat biaya membangun di suatu wilayah
                dibanding wilayah lain. PDRB konstruksi mengukur nilai usaha
                konstruksi yang tercipta di dalamnya. Yang satu soal harga,
                yang lain soal volume.
            </p>
        </section>
        """
    )

with c1_vis:
    with toolbar(
        "PETA",
        f"Biaya × skala pasar, {N_WILAYAH} kabupaten/kota",
        "Warna = IKK · Lingkaran = PDRB konstruksi · Scroll untuk zoom, seret untuk geser",
    ):
        with st.popover("Lapisan peta", use_container_width=True):
            show_ikk = st.toggle("Warna: IKK", value=True, key="map-ikk")
            show_pdrb = st.toggle("Lingkaran: PDRB konstruksi", value=True, key="map-pdrb")

    if not (show_ikk or show_pdrb):
        show_ikk = True

# FOKUS WILAYAH

    prov_options = (
        [ALL_PROV]
        + sorted(
            GEO["prov"]
            .dropna()
            .astype(str)
            .unique()
        )
    )

    current_prov = st.session_state.get(
        "map-prov",
        ALL_PROV,
    )

    html(
        """
        <div class="geo-filter-kicker">
            FOKUS WILAYAH
        </div>
        """
    )


    # Pill: "Semua provinsi"

    if current_prov == ALL_PROV:

        with st.popover(
            current_prov,
            use_container_width=True,
        ):

            sel_prov = st.selectbox(
                "Provinsi",
                prov_options,
                key="map-prov",
                help=(
                    "Pilih provinsi untuk memperbesar peta "
                    "dan membuka pilihan kabupaten/kota."
                ),
            )

        sel_kab = None


    # Pill Provinsi + Kabupaten/kota

    else:

        f_prov, f_kab = st.columns(
            2,
            gap="small",
        )


        # PROVINSI

        with f_prov:

            with st.popover(
                current_prov,
                use_container_width=True,
            ):

                sel_prov = st.selectbox(
                    "Provinsi",
                    prov_options,
                    key="map-prov",
                    help=(
                        "Ganti provinsi atau pilih "
                        "'Semua provinsi' untuk kembali "
                        "ke tampilan nasional."
                    ),
                )


        # KABUPATEN / KOTA 

        kab_names = sorted(

            GEO.loc[
                GEO["prov"] == current_prov,
                "nama",
            ]
            .dropna()
            .astype(str)
            .unique()

        )


        all_label = (
            f"Semua kab/kota "
            f"({len(kab_names)})"
        )


        kab_key = (
            f"map-kab::{current_prov}"
        )


        current_kab = (
            st.session_state.get(
                kab_key,
                all_label,
            )
        )


        with f_kab:

            with st.popover(
                current_kab,
                use_container_width=True,
            ):

                picked = st.selectbox(
                    "Kabupaten/kota",
                    [all_label] + kab_names,
                    key=kab_key,
                )


        sel_kab = (
            None
            if picked == all_label
            else picked
        )


    map_data = (
        GEO
        if sel_prov == ALL_PROV
        else GEO[
            GEO["prov"] == sel_prov
        ]
    )

    focus_one = (
        map_data[
            map_data["nama"] == sel_kab
        ]
        if sel_kab
        else map_data.iloc[0:0]
    )

    if sel_kab and not focus_one.empty:
        center, zoom = view_for(focus_one)
        zoom = max(zoom, 7.6)
    elif sel_prov != ALL_PROV:
        center, zoom = view_for(map_data)
    else:
        center, zoom = DEFAULT_CENTER, DEFAULT_ZOOM

    fig_map = go.Figure()

    if show_ikk:
        d = map_data.dropna(subset=["ikk"])
        fig_map.add_trace(
            ChoroplethMap(
                geojson=GEOJSON,
                locations=d["id"],
                featureidkey="properties.id",
                z=d["ikk"],
                colorscale=IKK_SCALE,
                marker_opacity=0.9,
                marker_line_width=0.35,
                marker_line_color="rgba(255,255,255,.78)",
                text=d["tip"].tolist(),
                hoverinfo="none",

                colorbar=dict(
                    title=dict(text="IKK", side="top"),
                    orientation="h",
                    thickness=10,
                    len=0.36,
                    x=0.015,
                    xanchor="left",
                    y=0.035,
                    yanchor="bottom",
                    bgcolor="rgba(255,255,255,.88)",
                    xpad=12,
                    ypad=8,
                    tickfont=dict(size=10),
                ),
                name="IKK",
            )
        )

    if show_pdrb:
        s = map_data.dropna(subset=["pdrb_f", "lon", "lat"])
        if not s.empty:
            max_pdrb = max(float(GEO["pdrb_f"].dropna().max()), 1.0)
            fig_map.add_trace(
                ScatterMap(
                    lon=s["lon"],
                    lat=s["lat"],
                    mode="markers",
                    text=s["tip"].tolist(),
                    hoverinfo="none",
                    marker=dict(
                        size=s["pdrb_f"],
                        sizemode="area",
                        sizeref=2 * max_pdrb / (34 ** 2),
                        sizemin=3,
                        color=ORANGE,
                        opacity=0.58,
                    ),
                    name="PDRB konstruksi",
                )
            )

    if not focus_one.empty: 
        fig_map.add_trace(
            ChoroplethMap(
                geojson=GEOJSON,
                locations=focus_one["id"],
                featureidkey="properties.id",
                z=[1] * len(focus_one),
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                showscale=False,
                marker_line_width=3,
                marker_line_color=INK,
                hoverinfo="skip",
            )
        )

    apply_map_layout(
        fig_map,
        height=540,
        center=center,
        zoom=zoom,
        revision=f"main|{sel_prov}|{sel_kab}",
    )

    st.plotly_chart(fig_map, use_container_width=True, config=MAP_CONFIG, key="map-main")
    source_note("geo")
    region_panel(sel_prov, sel_kab)


# temuan IKK & PDRB

if same_place:
    find_title = f"{hi_name} unggul di dua sisi sekaligus."
    find_p1 = (
        f"IKK tertinggi ({hi_text}) dan PDRB konstruksi terbesar "
        f"({tm_text}) sama-sama tercatat di <strong>{hi_name}</strong>, {hi_prov}."
    )
    find_p2 = "Di sini biaya dan skala pasar justru berjalan beriringan."
else:
    find_title = f"{hi_name} termahal, {tm_name} terbesar."
    rank_txt_h = (
        f"menempati peringkat <strong>{rank_highest}</strong> dari 514 wilayah"
        if rank_highest
        else "tidak memiliki data PDRB konstruksi"
    )
    find_p1 = (
        f"IKK tertinggi ({hi_text}) tercatat di <strong>{hi_name}</strong>, {hi_prov}, "
        f"tetapi PDRB konstruksinya {rank_txt_h}. Nilai terbesar ada di "
        f"<strong>{tm_name}</strong>, {tm_prov.upper()} ({tm_text})."
    )
    find_p2 = (
        "Biaya setinggi itu lebih mungkin mencerminkan jarak dan logistik daripada ramainya proyek."
        if rank_highest and rank_highest > len(valid_market) / 2
        else "Biaya tinggi dan pasar besar tidak harus datang dari tempat yang sama."
    )

html(
    f"""
    <section class="story-reveal story-reveal-compact">
        <div class="reveal-kicker">TEMUAN</div>
        <h3>{find_title}</h3>
        <p>{find_p1}</p>
        <p>{find_p2}</p>
    </section>
    """
)


# konsentrasi pasar 

all_symbols = GEO.dropna(subset=["pdrb_f", "lon", "lat"])
max_pdrb_all = max(float(all_symbols["pdrb_f"].max()), 1.0)

fig_symbol = go.Figure(
    ScatterMap(
        lon=all_symbols["lon"],
        lat=all_symbols["lat"],
        mode="markers",
        text=all_symbols["tip"].tolist(),
        hoverinfo="none",
        marker=dict(
            size=all_symbols["pdrb_f"],
            sizemode="area",
            sizeref=2 * max_pdrb_all / (42 ** 2),
            sizemin=3,
            color=BLUE,
            opacity=0.62,
        ),
    )
)
apply_map_layout(fig_symbol, height=460, revision="symbol")

mk_text, mk_vis = st.columns([0.72, 1.48], gap="large")

with mk_text:
    html(
        f"""
        <div class="side-story">
            <div class="chapter-mini-kicker">KONSENTRASI</div>
            <h3>{pct_text(share10)} nilai pasar ada di sepuluh wilayah.</h3>
            <p>
                Sepuluh kabupaten/kota teratas menyumbang
                <strong>{pct_text(share10)}</strong> PDRB konstruksi, padahal
                jumlahnya hanya {pct_text(share_regions10, 1)} dari seluruh wilayah.
                Tiga terbesar: {", ".join(top3_names)}.
            </p>
        </div>
        """
    )

with mk_vis:
    html(
        """
        <div class="visual-intro">
            <span>SKALA PASAR</span>
            <strong>PDRB konstruksi per kabupaten/kota</strong>
            <small>Luas lingkaran sebanding dengan PDRB · Scroll untuk zoom</small>
        </div>
        """
    )
    st.plotly_chart(fig_symbol, use_container_width=True, config=MAP_CONFIG, key="map-symbol")
    source_note("geo")


# BAB II — STRUKTUR PASAR  (data hierarki: tahun YEAR_HIER)

long_h = HIER.melt(
    id_vars=["pulau", "provinsi"],
    value_vars=["Gedung", "Sipil", "Khusus"],
    var_name="jenis",
    value_name="nilai_raw",
)
long_h["nilai"] = pd.to_numeric(long_h["nilai_raw"], errors="coerce") / 1_000_000

prov_total = HIER[["Gedung", "Sipil", "Khusus"]].sum(axis=1).replace(0, np.nan)
long_h["porsi_sipil"] = long_h["provinsi"].map(
    dict(zip(HIER["provinsi"], HIER["Sipil"] / prov_total * 100))
)

island_all = long_h.groupby("pulau", observed=True)["nilai"].sum().sort_values(ascending=False)
total_all = float(island_all.sum())
dom_all = esc(str(island_all.index[0]))
dom_all_share = float(island_all.iloc[0] / total_all) if total_all > 0 else 0.0

province_share_df = HIER.copy()
province_share_df["porsi_sipil"] = province_share_df["Sipil"] / prov_total
ranked_civil = province_share_df.dropna(subset=["porsi_sipil"]).sort_values("porsi_sipil", ascending=False)
max_civil = ranked_civil.iloc[0]
min_civil = ranked_civil.iloc[-1]

c2_text, c2_vis = st.columns([0.78, 1.42], gap="large")

with c2_text:
    html(
        f"""
        <section id="chapter-2" class="chapter-split-copy chapter-accent-blue">
            <div class="chapter-mini-kicker">BAB II · STRUKTUR PASAR</div>

            <h2 class="chapter-mini-title">
                {dom_all} menyerap {pct_text(dom_all_share)} nilai konstruksi.
            </h2>

            <p class="chapter-mini-deck">
                Di tiap provinsi, nilai itu terbagi ke gedung, sipil, dan
                konstruksi khusus. Warna petak menunjukkan seberapa besar
                porsi sipilnya.
            </p>

            <div class="data-note">
                <b>Catatan data</b>
                Struktur pasar pada bab ini menggunakan data
                <strong>{YEAR_HIER}</strong>.
                Rincian nilai konstruksi menurut jenis untuk
                <strong>{YEAR_MAIN}</strong> belum tersedia di BPS,
                sehingga bagian ini dibaca sebagai gambaran struktur
                dan tidak dibandingkan langsung dengan angka pada Bab I.
            </div>
        </section>
        """
    )

with c2_vis:
    n_sel_prev = len(st.session_state.get("island-filter", PULAU))
    n_off = len(PULAU) - n_sel_prev

    with toolbar(
        "TREEMAP",
        f"Pulau → Provinsi → Jenis Konstruksi · Data {YEAR_HIER}",
        "Luas petak = nilai (triliun Rp) · Warna = porsi sipil provinsi · Klik petak untuk masuk",
    ):
        with st.popover(pop_label("Pilih pulau", n_off and n_sel_prev), use_container_width=True):
            selected_islands = st.multiselect(
                "Kelompok pulau", PULAU, default=PULAU, key="island-filter"
            )

    LH = long_h[long_h["pulau"].isin(selected_islands)].copy()

    hierarchy_args = dict(
        path=[px.Constant("Indonesia"), "pulau", "provinsi", "jenis"],
        values="nilai",
        color="porsi_sipil",
        color_continuous_scale="Cividis",
        labels={"nilai": "Nilai konstruksi (triliun Rp)", "porsi_sipil": "Porsi sipil (%)"},
    )

    def style_hierarchy(fig: go.Figure, height: int, margin: dict, font_size: int) -> go.Figure:
        fig.update_traces(
            marker_line_width=1.2,
            marker_line_color="rgba(255,255,255,0.55)",
            texttemplate="<b>%{label}</b>",
            textfont=dict(size=font_size),
            maxdepth=3,  
        )
        attach_hierarchy_tooltips(fig)
        base_layout(fig, height=height, margin=margin)
        fig.update_layout(
            uniformtext=dict(minsize=12, mode="hide"),

            coloraxis_colorbar=dict(thickness=10, len=0.7, title=dict(text="Porsi sipil (%)", side="right")),
        )
        return fig

    if LH.empty:
        st.warning("Pilih minimal satu kelompok pulau.")
    else:
        treemap = px.treemap(LH, **hierarchy_args)
        treemap.update_traces(root_color="#EFF2F3")
        style_hierarchy(treemap, 580, dict(l=10, r=10, t=10, b=10), 16)
        st.plotly_chart(treemap, use_container_width=True, config=PLOTLY_CONFIG, key="treemap")
        source_note("hier")

if not LH.empty:
    island_sel = LH.groupby("pulau", observed=True)["nilai"].sum().sort_values(ascending=False)
    total_h = float(LH["nilai"].sum())
    dom_sel = esc(str(island_sel.index[0]))
    dom_sel_share = float(island_sel.iloc[0] / total_h) if total_h > 0 else 0.0
    sipil_share = float(LH.loc[LH["jenis"] == "Sipil", "nilai"].sum() / total_h) if total_h > 0 else 0.0

    scope_label = "Indonesia" if len(selected_islands) == len(PULAU) else "wilayah terpilih"
    type_view = LH.groupby("jenis", observed=True)["nilai"].sum().sort_values(ascending=False)
    type_view_total = float(type_view.sum())
    dom_type_view = esc(str(type_view.index[0]))
    dom_type_view_share = float(type_view.iloc[0] / type_view_total) if type_view_total > 0 else 0.0

    selected_provinces = set(LH["provinsi"].dropna().astype(str))
    civil_view = ranked_civil[ranked_civil["provinsi"].astype(str).isin(selected_provinces)]
    max_civil_view = civil_view.iloc[0] if not civil_view.empty else max_civil
    min_civil_view = civil_view.iloc[-1] if not civil_view.empty else min_civil
    civil_gap_view_pp = float(
        (max_civil_view["porsi_sipil"] - min_civil_view["porsi_sipil"]) * 100
    )

    prov_view = (
        LH.groupby(["pulau", "provinsi", "jenis"], observed=True)["nilai"]
        .sum()
        .reset_index()
    )
    prov_totals_view = prov_view.groupby("provinsi", observed=True)["nilai"].sum().sort_values(ascending=False)
    top_prov_view_name = esc(str(prov_totals_view.index[0]))
    top_prov_view_total = float(prov_totals_view.iloc[0])
    top_prov_view_types = (
        prov_view[prov_view["provinsi"].astype(str) == str(prov_totals_view.index[0])]
        .groupby("jenis", observed=True)["nilai"]
        .sum()
        .sort_values(ascending=False)
    )
    top_prov_view_dom_type = esc(str(top_prov_view_types.index[0]))
    top_prov_view_dom_share = (
        float(top_prov_view_types.iloc[0] / top_prov_view_types.sum())
        if float(top_prov_view_types.sum()) > 0
        else 0.0
    )

    html(
        f"""
        <section class="insight-strip">
            <div>
                <span>Kontributor terbesar</span>
                <strong>{dom_sel}</strong>
                <small>{pct_text(dom_sel_share)} dari nilai terpilih</small>
            </div>
            <div>
                <span>Porsi konstruksi sipil</span>
                <strong>{pct_text(sipil_share)}</strong>
                <small>dari total nilai terpilih</small>
            </div>
            <div>
                <span>Porsi sipil tertinggi</span>
                <strong>{esc(str(max_civil["provinsi"]))}</strong>
                <small>{pct_text(float(max_civil["porsi_sipil"]))} dari struktur provinsinya</small>
            </div>
        </section>
        """
    )

    html(
        f"""
        <section class="story-reveal story-reveal-compact chapter2-finding">
            <div class="reveal-kicker">TEMUAN BAB II</div>
            <h3>{dom_type_view} paling besar di {scope_label}, tetapi komposisi proyek tidak seragam.</h3>
            <p>
                Pada pilihan saat ini, <strong>{dom_type_view}</strong> menyerap
                <strong>{pct_text(dom_type_view_share)}</strong> nilai konstruksi. Namun porsi sipil
                antarprovinsi membentang dari
                <strong>{pct_text(float(min_civil_view["porsi_sipil"]))}</strong> di
                <strong>{esc(str(min_civil_view["provinsi"]))}</strong> hingga
                <strong>{pct_text(float(max_civil_view["porsi_sipil"]))}</strong> di
                <strong>{esc(str(max_civil_view["provinsi"]))}</strong> — selisih sekitar
                <strong>{fmt_id(civil_gap_view_pp, 0)} poin persentase</strong>.
            </p>
            <p>
                Provinsi dengan nilai konstruksi terbesar pada cakupan ini,
                <strong>{top_prov_view_name}</strong> (Rp{fmt_id(top_prov_view_total, 1)} T),
                paling banyak tersusun dari <strong>{top_prov_view_dom_type}</strong>
                sebesar <strong>{pct_text(top_prov_view_dom_share)}</strong>.
                Jadi, besarnya pasar belum cukup untuk menjelaskan jenis proyek
                yang menggerakkan pasar tersebut.
            </p>
        </section>
        """
    )

    sunburst = px.sunburst(LH, **hierarchy_args)
    sunburst.update_traces(insidetextorientation="auto")
    style_hierarchy(sunburst, 640, dict(l=36, r=36, t=36, b=36), 15)

    sb_text, sb_vis = st.columns([0.72, 1.48], gap="large")

    with sb_text:
        html(
            f"""
            <div class="side-story">
                <div class="chapter-mini-kicker">KOMPOSISI</div>
                <h3>
                    Porsi sipil berkisar {pct_text(float(min_civil["porsi_sipil"]))}
                    sampai {pct_text(float(max_civil["porsi_sipil"]))}.
                </h3>
                <p>
                    Tertinggi di <strong>{esc(str(max_civil["provinsi"]))}</strong>,
                    terendah di <strong>{esc(str(min_civil["provinsi"]))}</strong>.
                    Dua provinsi dengan nilai konstruksi serupa bisa menyerap
                    jenis proyek yang sangat berbeda.
                </p>
            </div>
            """
        )

    with sb_vis:
        html(
            f"""
            <div class="visual-intro">
                <span>SUNBURST</span>
                <strong>Jalur hierarki yang sama, dibaca melingkar · data {YEAR_HIER}</strong>
                <small>Klik sektor untuk masuk · Klik pusat untuk kembali</small>
            </div>
            """
        )
        st.plotly_chart(sunburst, use_container_width=True, config=PLOTLY_CONFIG, key="sunburst")
        source_note("hier")


# BAB III — PROFIL PROVINSI

X = MULTI[VARS].astype(float).copy()
for variable in LOG_VARS:
    if variable in X.columns:
        X[variable] = np.log10(X[variable].clip(lower=1e-12))

Zdf = (X - X.mean()) / X.std(ddof=1).replace(0, 1)
Z = Zdf.to_numpy(dtype=float)
C = np.corrcoef(Z, rowvar=False)

eigval, eigvec = np.linalg.eigh(C)
order = np.argsort(eigval)[::-1]
eigval, eigvec = eigval[order], eigvec[:, order]
eigvec = eigvec * np.where(eigvec.sum(axis=0) < 0, -1, 1)

score = Z @ eigvec[:, :2]
variance = eigval / eigval.sum()

pc1_text = pct_text(float(variance[0]))
pc2_text = pct_text(float(variance[1]))
explained_2pc_text = pct_text(float(variance[0] + variance[1]))

M = MULTI.copy()
M["PC1"] = score[:, 0]
M["PC2"] = score[:, 1]

TIP_EXTRA = [  
    ("IKK", "IKK", 1),
    ("PDRB Konstruksi", "PDRB konstruksi", 0),
    ("Jml Perusahaan", "Jumlah perusahaan", 0),
    ("Belanja Modal", "Belanja modal", 0),
]


def make_multi_tip(r) -> str:
    rows = [("PC1", fmt_id(r["PC1"], 2)), ("PC2", fmt_id(r["PC2"], 2))]
    for col, label, dec in TIP_EXTRA:
        if col in M.columns:
            value = f"Rp{fmt_id(r[col], dec)} miliar" if col == "PDRB Konstruksi" else fmt_id(r[col], dec)
            rows.append((label, value))
    return tip_card(r["provinsi"], r["pulau"], rows)


M["tip"] = M.apply(make_multi_tip, axis=1)
PULAU_COUNT = M["pulau"].value_counts().to_dict()
PROVINCES = sorted(M["provinsi"].tolist())

upper = np.triu_indices(len(VARS), 1)
corr_upper = C[upper]
strongest = int(np.nanargmax(np.abs(corr_upper)))
corr_a = esc(VARS[upper[0][strongest]])
corr_b = esc(VARS[upper[1][strongest]])
corr_value_text = fmt_id(float(corr_upper[strongest]), 2)

distance = np.hypot(score[:, 0], score[:, 1])
farthest_province = esc(str(M.iloc[int(np.nanargmax(distance))]["provinsi"]))

top_idx = np.argsort(-np.abs(eigvec[:, 0]))[:2]
top_load = [esc(VARS[i]) for i in top_idx]


def axis_title(k: int, pct: str) -> str:
    load = eigvec[:, k]
    pos = [VARS[i] for i in np.argsort(-load)[:2] if load[i] > 0.15]
    neg = [VARS[i] for i in np.argsort(load)[:2] if load[i] < -0.15]
    hint = []
    if pos:
        hint.append("makin besar: " + ", ".join(pos))
    if neg:
        hint.append("makin kecil: " + ", ".join(neg))
    sub = f"<br><sup>{' · '.join(hint)}</sup>" if hint else ""
    return f"PC{k + 1} · {pct} varians{sub}"


def build_pca(highlight: list[str]) -> go.Figure:
    fig = px.scatter(
        M,
        x="PC1",
        y="PC2",
        color="pulau",
        color_discrete_map=CMAP,
        category_orders={"pulau": PULAU},
        custom_data=["provinsi", "tip"],
        labels={"pulau": "Pulau"},
    )
    fig.for_each_trace(lambda t: t.update(name=f"{t.name} ({PULAU_COUNT.get(t.name, 0)})"))
    fig.update_traces(
        marker=dict(size=10, line=dict(width=1, color="white")),
        hoverinfo="none",
        hovertemplate=None,
    )

    load_scale = min(
        float(np.abs(score[:, 0]).max()) / max(float(np.abs(eigvec[:, 0]).max()), 1e-9),
        float(np.abs(score[:, 1]).max()) / max(float(np.abs(eigvec[:, 1]).max()), 1e-9),
    ) * 0.85

    tips_x, tips_y, tips_html = [], [], []
    for idx, variable in enumerate(VARS):
        tx = float(eigvec[idx, 0] * load_scale)
        ty = float(eigvec[idx, 1] * load_scale)
        tips_x.append(tx)
        tips_y.append(ty)
        tips_html.append(
            tip_card(
                variable,
                "Muatan indikator (arah panah)",
                [("PC1", fmt_id(eigvec[idx, 0], 2)), ("PC2", fmt_id(eigvec[idx, 1], 2))],
            )
        )
        fig.add_annotation(
            x=tx, y=ty, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.6, arrowcolor=INK, text="",
        )
        fig.add_annotation(
            x=tx, y=ty, xref="x", yref="y", showarrow=False,
            text=f"<b>{esc(variable)}</b>",
            xanchor="left" if tx >= 0 else "right",
            yanchor="bottom" if ty >= 0 else "top",
            xshift=5 if tx >= 0 else -5,
            yshift=3 if ty >= 0 else -3,
            font=dict(size=11, color=INK),
            bgcolor="rgba(255,255,255,.72)",
        )

    fig.add_trace(
        go.Scatter(
            x=tips_x, y=tips_y, mode="markers",
            marker=dict(size=18, color="rgba(24,36,45,0.01)"),
            customdata=tips_html, hoverinfo="none", showlegend=False,
        )
    )

    if highlight:  
        sel = M[M["provinsi"].isin(highlight)]
        fig.add_trace(
            go.Scatter(
                x=sel["PC1"], y=sel["PC2"], mode="markers+text",
                text=sel["provinsi"], textposition="top center",
                textfont=dict(size=11, color=INK),
                marker=dict(size=20, color="rgba(0,0,0,0)", line=dict(width=2, color=INK)),
                hoverinfo="skip", showlegend=False,
            )
        )

    fig.update_layout(
        dragmode="lasso",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
    )
    axis_style = dict(zeroline=True, zerolinecolor="#C9D1D5", gridcolor="#EDF1F3")
    fig.update_xaxes(title_text=axis_title(0, pc1_text), **axis_style)
    fig.update_yaxes(title_text=axis_title(1, pc2_text), **axis_style)
    return base_layout(fig, height=540, margin=dict(l=24, r=24, t=64, b=24))


c3_text, c3_vis = st.columns([0.78, 1.42], gap="large")

with c3_text:
    html(
        f"""
        <section id="chapter-3" class="chapter-split-copy chapter-accent-green">
            <div class="chapter-mini-kicker">BAB III · PROFIL PROVINSI</div>

            <h2 class="chapter-mini-title">Besar tidak berarti sama.</h2>

            <p class="chapter-mini-deck">
                <strong>{len(VARS)} indikator</strong>, dari jumlah perusahaan
                sampai belanja modal, diringkas dengan PCA menjadi dua sumbu.
                Provinsi yang berdekatan di grafik punya struktur industri
                yang mirip.
            </p>
        </section>
        """
    )

with c3_vis:
    n_pick = len(st.session_state.get("pca-pick", []))

    with toolbar(
        "PCA BIPLOT",
        "Sidik jari konstruksi tiap provinsi",
        f"Titik = provinsi · Panah = {len(VARS)} Indikator · Arahkan kursor ke ujung panah",
    ):
        with st.popover(pop_label("Sorot provinsi", n_pick), use_container_width=True):
            pca_pick = st.multiselect(
                "Provinsi yang ingin disorot",
                PROVINCES,
                key="pca-pick",
                placeholder="Pilih provinsi",
            )

    pca = build_pca(pca_pick)

    try:
        pca_event = st.plotly_chart(
            pca,
            use_container_width=True,
            config=PLOTLY_CONFIG,
            on_select="rerun",
            selection_mode=["box", "lasso"],
            key="pca-linked",
        )
        brushed = sorted(
            {
                p["customdata"][0]
                for p in getattr(getattr(pca_event, "selection", None), "points", [])
                if isinstance(p, dict) and isinstance(p.get("customdata"), (list, tuple)) and p["customdata"]
            }
            & set(PROVINCES)  
        )
        if brushed:  
            st.caption(f"Terpilih di grafik ({len(brushed)}): " + ", ".join(brushed))
    except (TypeError, AttributeError):
        st.plotly_chart(pca, use_container_width=True, config=PLOTLY_CONFIG, key="pca-fallback")

    source_note("multi")

# heatmap profil z-score

profile_z = pd.DataFrame(Z, columns=VARS)
profile_z["provinsi"] = M["provinsi"].values
profile_z["pulau"] = M["pulau"].values
profile_z["PC1"] = M["PC1"].values
profile_z["pulau_order"] = pd.Categorical(
    profile_z["pulau"],
    categories=PULAU,
    ordered=True,
)

profile_z = (
    profile_z
    .sort_values(["pulau_order", "PC1"], ascending=[True, False])
    .reset_index(drop=True)
)

raw_multi = M.set_index("provinsi")

profile_strength = profile_z[VARS].abs().mean(axis=1)
most_distinct_i = int(profile_strength.idxmax())
most_distinct_row = profile_z.loc[most_distinct_i]
most_distinct_prov = esc(str(most_distinct_row["provinsi"]))
most_distinct_var = max(VARS, key=lambda v: abs(float(most_distinct_row[v])))
most_distinct_z = float(most_distinct_row[most_distinct_var])
most_distinct_dir = "di atas" if most_distinct_z > 0 else "di bawah"


def profile_value_text(variable: str, value) -> str:
    if pd.isna(value):
        return "—"
    if variable == "IKK":
        return fmt_id(value, 1)
    if variable == "Jml Perusahaan":
        return fmt_id(value, 0)
    if variable == "PDRB Konstruksi":
        return f"Rp{fmt_id(value, 0)} miliar"
    return fmt_id(value, 2)


def categorical_colorscale(colors: list[str]) -> list[list[float | str]]:
    n = len(colors)
    scale = []
    for i, color in enumerate(colors):
        left = i / n
        right = (i + 1) / n
        scale.append([left, color])
        scale.append([max(left, right - 1e-6), color])
    return scale


ph_text, ph_vis = st.columns([0.62, 1.58], gap="large")

with ph_text:
    html(
        f"""
        <section class="side-story">
            <div class="chapter-mini-kicker">SIDIK JARI INDIKATOR</div>
            <h3>PCA merangkum. Heatmap ini membuka angkanya lagi.</h3>
            <p>
                Setiap baris adalah provinsi dan setiap kolom adalah indikator.
                Warna menunjukkan <strong>z-score</strong>: biru berarti di bawah
                rerata provinsi, sedangkan jingga berarti di atas rerata.
            </p>
            <p>
                <strong>{most_distinct_prov}</strong> punya profil paling jauh dari
                rerata keseluruhan. Perbedaan terbesarnya muncul pada
                <strong>{esc(most_distinct_var)}</strong>, sekitar
                <strong>{fmt_id(abs(most_distinct_z), 2)} simpangan baku</strong>
                {most_distinct_dir} rerata.
            </p>
        </section>
        """
    )

with ph_vis:
    with toolbar(
        "HEATMAP PROFIL",
        "Provinsi × indikator terstandarisasi",
        "Biru = di bawah rerata · Jingga = di atas rerata · strip kiri = kelompok pulau",
    ):
        st.empty()

    province_order = profile_z["provinsi"].tolist()
    display_vars = ["<br>".join(textwrap.wrap(str(v), width=15)) for v in VARS]

    profile_tips = np.empty((len(profile_z), len(VARS)), dtype=object)
    for i, row in profile_z.iterrows():
        prov = str(row["provinsi"])
        island = str(row["pulau"])
        raw_row = raw_multi.loc[prov]
        for j, variable in enumerate(VARS):
            z_value = float(row[variable])
            raw_value = raw_row[variable] if variable in raw_row.index else np.nan
            profile_tips[i, j] = tip_card(
                prov,
                f"{island} · {variable}",
                [
                    ("Z-score", fmt_id(z_value, 2)),
                    ("Posisi", "Di atas rerata" if z_value > 0 else "Di bawah rerata" if z_value < 0 else "Setara rerata"),
                    ("Nilai asli", profile_value_text(variable, raw_value)),
                ],
            )

    island_codes = np.array(
        [[PULAU.index(str(p))] for p in profile_z["pulau"]],
        dtype=float,
    )
    island_tips = np.array(
        [[tip_card(str(row["provinsi"]), str(row["pulau"]), [("Kelompok", "Pulau")])] for _, row in profile_z.iterrows()],
        dtype=object,
    )

    profile_heatmap = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        column_widths=[0.035, 0.965],
        horizontal_spacing=0.012,
    )

    profile_heatmap.add_trace(
        go.Heatmap(
            z=island_codes,
            x=[""],
            y=province_order,
            zmin=-0.5,
            zmax=len(PULAU) - 0.5,
            colorscale=categorical_colorscale([CMAP[p] for p in PULAU]),
            showscale=False,
            customdata=island_tips,
            hoverinfo="none",
            hovertemplate=None,
            xgap=0,
            ygap=1,
        ),
        row=1,
        col=1,
    )

    profile_heatmap.add_trace(
        go.Heatmap(
            z=profile_z[VARS].to_numpy(dtype=float),
            x=display_vars,
            y=province_order,
            zmin=-3,
            zmax=3,
            zmid=0,
            colorscale=[
                [0.00, "#2D79BF"],
                [0.22, "#7FB5E6"],
                [0.50, "#F4F1EA"],
                [0.78, "#F1A36A"],
                [1.00, "#C85A1A"],
            ],
            customdata=profile_tips,
            hoverinfo="none",
            hovertemplate=None,
            xgap=1,
            ygap=1,
            colorbar=dict(
                title=dict(text="z-score", side="right"),
                thickness=11,
                len=0.76,
                tickvals=[-3, -1.5, 0, 1.5, 3],
                ticktext=["≤ -3", "-1,5", "0", "1,5", "≥ 3"],
            ),
        ),
        row=1,
        col=2,
    )

    profile_heatmap.update_layout(
        height=760,
        margin=dict(l=10, r=20, t=78, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", color=INK, size=11),
        showlegend=False,
    )

    profile_heatmap.update_xaxes(
        side="top",
        tickangle=-32,
        tickfont=dict(size=10, color="#687680"),
        showgrid=False,
        zeroline=False,
        row=1,
        col=2,
    )
    profile_heatmap.update_xaxes(showticklabels=False, row=1, col=1)

    profile_heatmap.update_yaxes(
        autorange="reversed",
        tickfont=dict(size=9, color="#687680"),
        showgrid=False,
        zeroline=False,
        row=1,
        col=1,
    )
    profile_heatmap.update_yaxes(
        autorange="reversed",
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        row=1,
        col=2,
    )

    st.plotly_chart(
        profile_heatmap,
        use_container_width=True,
        config=PLOTLY_CONFIG,
        key="profile-z-heatmap",
    )
    source_note("multi")

# heatmap korelasi

pf_text, pf_vis = st.columns([0.72, 1.48], gap="large")

with pf_text:
    html(
        f"""
        <section class="side-story">
            <div class="chapter-mini-kicker">MEMBACA SUMBU</div>
            <h3>Dua sumbu menangkap {explained_2pc_text} variasi.</h3>
            <p>
                Sumbu pertama paling ditentukan oleh <strong>{top_load[0]}</strong>
                dan <strong>{top_load[1]}</strong>. Pasangan indikator yang paling
                berkaitan: <strong>{corr_a}</strong> dan <strong>{corr_b}</strong>
                (r = {corr_value_text}).
            </p>
            <p>
                <strong>{farthest_province}</strong> berada paling jauh dari pusat,
                artinya profilnya paling menyimpang dari provinsi lain.
            </p>
        </section>
        """
    )

MIN_HEAT = 5

with pf_vis:
    n_heat = len(st.session_state.get("heat-pick", []))

    with toolbar(
        "HEATMAP",
        "Korelasi antarindikator",
        "Nilai mendekati ±1 berarti hubungan makin kuat",
    ):
        with st.popover(pop_label("Atur heatmap", n_heat), use_container_width=True):
            heat_pick = st.multiselect(
                "Hitung korelasi dari provinsi",
                PROVINCES,
                key="heat-pick",
                placeholder=f"Semua {len(PROVINCES)} provinsi",
                help=f"Kosongkan untuk memakai semua provinsi. Minimal {MIN_HEAT} provinsi.",
            )

    use_subset = len(heat_pick) >= MIN_HEAT
    if heat_pick and not use_subset:
        st.warning(f"Pilih minimal {MIN_HEAT} provinsi; sementara memakai semua provinsi.")

    mask = M["provinsi"].isin(heat_pick).to_numpy() if use_subset else np.ones(len(M), dtype=bool)
    C_view = np.nan_to_num(np.corrcoef(Z[mask], rowvar=False), nan=0.0)
    np.fill_diagonal(C_view, 1.0)

    heatmap = px.imshow(
        C_view,
        x=VARS,
        y=VARS,
        zmin=-1,
        zmax=1,
        color_continuous_scale="PuOr",
        text_auto=".2f",
        aspect="auto",
    )

    heat_tips = np.empty(C_view.shape, dtype=object)
    for i, row_name in enumerate(VARS):
        for j, col_name in enumerate(VARS):
            r_value = float(C_view[i, j])
            direction = "Searah" if r_value > 0 else "Berlawanan arah" if r_value < 0 else "Netral"
            heat_tips[i, j] = tip_card(
                f"{row_name} × {col_name}",
                f"Korelasi Pearson · {int(mask.sum())} provinsi",
                [("Koefisien r", fmt_id(r_value, 2)), ("Arah", direction)],
            )

    heatmap.update_traces(customdata=heat_tips, hoverinfo="none", hovertemplate=None)
    base_layout(heatmap, height=500, margin=dict(l=24, r=24, t=24, b=24))
    heatmap.update_xaxes(tickangle=-35, automargin=True)
    heatmap.update_yaxes(automargin=True)
    heatmap.update_layout(coloraxis_colorbar=dict(thickness=10, len=0.8, title=dict(text="r", side="right")))

    st.plotly_chart(heatmap, use_container_width=True, config=PLOTLY_CONFIG, key="heatmap")
    source_note("multi")


# scatterplot matrix

html(
    """
    <div class="transition-question compact">
        <span>DETAIL</span>
        <h3>Pasangan indikator mana yang bergerak bersama?</h3>
    </div>
    """
)


D = X.copy()
D["provinsi"] = M["provinsi"].values
D["pulau"] = M["pulau"].values

SPL_VAR_CODES = {var: f"V{i + 1}" for i, var in enumerate(VARS)}
splom_key_html = "".join(
    f'<div><b>{SPL_VAR_CODES[var]}</b><span>{esc(var)}</span></div>'
    for var in VARS
)

html(
    f"""
    <div class="splom-var-key">
        <div class="splom-key-title">KODE INDIKATOR</div>
        <div class="splom-key-grid">{splom_key_html}</div>
    </div>
    """
)

n_sp = len(st.session_state.get("splom-pick", []))
with toolbar(
    "SCATTERPLOT MATRIX",
    "Setiap kotak membandingkan dua indikator",
    "V1–Vn mengikuti daftar indikator di atas · Warna = pulau · Klik legenda untuk menyaring pulau",
):
    with st.popover(pop_label("Sorot provinsi", n_sp), use_container_width=True):
        splom_pick = st.multiselect(
            "Provinsi yang ingin disorot",
            PROVINCES,
            key="splom-pick",
            placeholder="Pilih provinsi",
        )

splom = px.scatter_matrix(
    D,
    dimensions=VARS,
    color="pulau",
    color_discrete_map=CMAP,
    category_orders={"pulau": PULAU},
    labels=SPL_VAR_CODES,
)

splom.update_traces(
    diagonal_visible=False,
    showupperhalf=False,
    marker=dict(size=6, opacity=0.82, line=dict(width=0.45, color="white")),
    hoverinfo="none",
    hovertemplate=None,
)

for trace in splom.data:
    rows_for_trace = M[M["pulau"] == trace.name]
    trace.customdata = np.array(
        [[prov, tip] for prov, tip in zip(rows_for_trace["provinsi"], rows_for_trace["tip"])],
        dtype=object,
    )

if splom_pick:
    picked_idx = set(D.index[D["provinsi"].isin(splom_pick)])
    for trace in splom.data:
        source_idx = D.index[D["pulau"] == trace.name].tolist()
        trace.selectedpoints = [i for i, idx in enumerate(source_idx) if idx in picked_idx]
        trace.selected = dict(
            marker=dict(size=9, opacity=1, line=dict(width=1.2, color=INK))
        )
        trace.unselected = dict(marker=dict(opacity=0.10))

base_layout(splom, height=770, margin=dict(l=96, r=18, t=70, b=82))

row_labels = []
for yax in splom.select_yaxes():
    title = yax.title.text if yax.title is not None else None
    if title and yax.domain:
        row_labels.append((str(title), (yax.domain[0] + yax.domain[1]) / 2))
    yax.title.text = None
    yax.title.standoff = 0

col_labels = []
for xax in splom.select_xaxes():
    title = xax.title.text if xax.title is not None else None
    if title and xax.domain:
        col_labels.append((str(title), (xax.domain[0] + xax.domain[1]) / 2))
    xax.title.text = None
    xax.title.standoff = 0

for code, y_mid in row_labels:
    splom.add_annotation(
        xref="paper",
        yref="paper",
        x=-0.072,
        y=y_mid,
        text=f"<b>{code}</b>",
        showarrow=False,
        xanchor="right",
        yanchor="middle",
        font=dict(size=10, color="#66747D"),
    )

for code, x_mid in col_labels:
    splom.add_annotation(
        xref="paper",
        yref="paper",
        x=x_mid,
        y=-0.072,
        text=f"<b>{code}</b>",
        showarrow=False,
        xanchor="center",
        yanchor="top",
        font=dict(size=10, color="#66747D"),
    )

splom.update_layout(
    hovermode="closest",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.015,
        xanchor="left",
        x=0,
        title_text="",
        itemsizing="constant",
        font=dict(size=11),
        tracegroupgap=3,
    ),
)
splom.update_xaxes(
    tickfont=dict(size=8),
    nticks=3,
    automargin=False,
    showgrid=True,
    gridcolor="#EEF1F2",
    zeroline=False,
    ticks="outside",
    ticklen=3,
    tickcolor="#C7D0D4",
)
splom.update_yaxes(
    tickfont=dict(size=8),
    nticks=3,
    automargin=False,
    showgrid=True,
    gridcolor="#EEF1F2",
    zeroline=False,
    ticks="outside",
    ticklen=3,
    tickcolor="#C7D0D4",
)

st.plotly_chart(splom, use_container_width=True, config=PLOTLY_CONFIG, key="splom")

if splom_pick:
    st.caption("Disorot: " + ", ".join(sorted(splom_pick)))

source_note("multi")


# PENUTUP

if same_place:
    cost_summary = (
        f"IKK berkisar {lo_text} sampai {hi_text}; <strong>{hi_name}</strong> "
        f"menjadi wilayah termahal sekaligus pasar konstruksi terbesar."
    )
    closing = (
        f"Biaya dan skala bertemu di <strong>{hi_name}</strong>, tetapi karakter "
        "industri tetap perlu dibaca terpisah karena ukuran pasar tidak menjelaskan "
        "komposisi proyek maupun profil provinsinya."
    )
else:
    cost_summary = (
        f"IKK berkisar {lo_text} sampai {hi_text}. <strong>{hi_name}</strong> yang "
        f"termahal, tetapi pasar konstruksi terbesar justru berada di "
        f"<strong>{tm_name}</strong>."
    )
    closing = (
        f"Tekanan biaya mengarah ke <strong>{hi_name}</strong>, sedangkan skala pasar "
        f"mengarah ke <strong>{tm_name}</strong>. Karena itu, wilayah prioritas akan "
        "berbeda tergantung apakah pertanyaannya tentang biaya, besarnya pasar, atau "
        "karakter industrinya."
    )

structure_summary = (
    f"{dom_all} memegang {pct_text(dom_all_share)} nilai konstruksi pada {YEAR_HIER}. "
    f"Di tingkat provinsi, porsi sipil berkisar "
    f"{pct_text(float(min_civil['porsi_sipil']))}–{pct_text(float(max_civil['porsi_sipil']))}."
)

html(
    f"""
    <section id="epilogue" class="epilogue">
        <div class="chapter-kicker">RINGKASAN</div>
        <h2>Tiga lapisan, tiga jawaban.</h2>

        <div class="epilogue-grid">
            <article>
                <span>01</span>
                <h3>Biaya</h3>
                <p>{cost_summary}</p>
            </article>

            <article>
                <span>02</span>
                <h3>Struktur</h3>
                <p>{structure_summary}</p>
            </article>

            <article>
                <span>03</span>
                <h3>Karakter</h3>
                <p>Dua sumbu PCA merangkum {explained_2pc_text} variasi; {farthest_province} paling menyimpang.</p>
            </article>
        </div>

        <p class="closing-line">{closing}</p>
    </section>
    """
)


# DATA & METODE

vars_li = "".join(f"<li>{esc(v)}</li>" for v in VARS)
log_li = "".join(f"<li>{esc(v)}</li>" for v in LOG_VARS if v in VARS)

html(
    f"""
    <section id="methodology" class="method-section">
        <div class="chapter-kicker">DATA &amp; METODE</div>
        <h2 class="method-title">Dari mana angka ini datang.</h2>

        <details class="method-acc" open>
            <summary><span class="acc-num">01</span><span class="acc-title">Sumber dan tahun data</span><i class="acc-icon"></i></summary>
            <div class="acc-body">
                <div class="table-wrap">
                    <table class="method-table">
                        <thead><tr><th>Lapisan</th><th>Isi</th><th>Sumber</th><th>Tahun</th></tr></thead>
                        <tbody>
                            <tr><td>Geospasial</td><td>IKK dan PDRB konstruksi, {N_WILAYAH} kabupaten/kota</td><td>BPS</td><td>{YEAR_MAIN}</td></tr>
                            <tr><td>Hierarki</td><td>Nilai konstruksi menurut jenis: gedung, sipil, khusus</td><td>BPS</td><td><b>{YEAR_HIER}</b></td></tr>
                            <tr><td>Multivariat</td><td>{len(VARS)} indikator per provinsi</td><td>BPS · Kemenkeu SIKD</td><td>{YEAR_MAIN}</td></tr>
                        </tbody>
                    </table>
                </div>
                <p class="acc-note"><b>Mengapa hierarki memakai {YEAR_HIER}?</b>
                Rincian nilai konstruksi menurut jenis belum dirilis BPS untuk {YEAR_MAIN},
                sehingga data hierarki satu tahun lebih lama dari data lain. Bab II
                dibaca sebagai <em>struktur</em> pasar, bukan perbandingan angka
                langsung dengan peta.</p>
            </div>
        </details>

        <details class="method-acc">
            <summary><span class="acc-num">02</span><span class="acc-title">Cara membaca grafik</span><i class="acc-icon"></i></summary>
            <div class="acc-body">
                <ul class="acc-list">
                    <li><b>Peta:</b> warna (choropleth) = IKK; Luas Lingkaran = PDRB konstruksi. Garis tebal menandai kabupaten/kota yang dipilih lewat dropdown.</li>
                    <li><b>Treemap &amp; Sunburst:</b> Luas = nilai (triliun Rp); Warna = porsi sipil provinsi. Dua variabel berbeda, dua saluran visual berbeda.</li>
                    <li><b>PCA biplot:</b> Titik = provinsi, Warna = pulau; Panah = arah {len(VARS)} indikator. Provinsi di arah sebuah panah bernilai tinggi pada indikator itu.</li>
                    <li><b>Heatmap &amp; Scatterplot matrix:</b> korelasi antarindikator. Tiap grafik punya dropdown provinsi sendiri dan tidak saling memengaruhi.</li>
                    <li>Palet dipilih agar tetap terbaca bagi buta warna (Cividis, PuOr, skala hijau-biru).</li>
                </ul>
            </div>
        </details>

        <details class="method-acc">
            <summary><span class="acc-num">03</span><span class="acc-title">Pengolahan dan analisis</span><i class="acc-icon"></i></summary>
            <div class="acc-body">
                <ul class="acc-list">
                    <li>Transformasi <code>log10</code> pada indikator berskala besar:
                        <ul>{log_li}</ul>
                    </li>
                    <li>Setelah transformasi, data distandardisasi (z-score) dan PCA dihitung dari matriks korelasi.</li>
                    <li>Indikator fiskal dari SIKD yang masuk PCA saat ini: <b>Belanja Modal</b>.</li>
                </ul>
            </div>
        </details>

        <details class="method-acc">
            <summary><span class="acc-num">04</span><span class="acc-title">{len(VARS)} indikator multivariat</span><i class="acc-icon"></i></summary>
            <div class="acc-body"><ul class="acc-list acc-cols">{vars_li}</ul></div>
        </details>

        <details class="method-acc">
            <summary><span class="acc-num">05</span><span class="acc-title">Keterbatasan</span><i class="acc-icon"></i></summary>
            <div class="acc-body">
                <ul class="acc-list">
                    <li>Data hierarki memakai tahun {YEAR_HIER}, sedangkan lapisan lain {YEAR_MAIN}.</li>
                    <li>Titik lingkaran pada peta memakai titik representatif dari ring geometri utama.</li>
                    <li>PCA dua dimensi adalah ringkasan; tidak menggantikan seluruh informasi {len(VARS)} indikator.</li>
                    <li>Korelasi tidak membuktikan sebab-akibat.</li>
                </ul>
            </div>
        </details>
    </section>
    """
)

run_js(
    """
    (function () {
      const win = window.parent;
      const doc = win.document;

      if (win.__methodAccCleanup) {
        try { win.__methodAccCleanup(); } catch (e) {}
      }

      function bindExclusiveAccordion() {
        const items = Array.from(doc.querySelectorAll('.method-section details.method-acc'));
        items.forEach(function (item) {
          if (item.__exclusiveAccBound) { return; }
          item.__exclusiveAccBound = true;
          item.addEventListener('toggle', function () {
            if (!item.open) { return; }
            items.forEach(function (other) {
              if (other !== item && other.open) { other.open = false; }
            });
          });
        });
      }

      bindExclusiveAccordion();
      const observer = new MutationObserver(bindExclusiveAccordion);
      observer.observe(doc.body, { childList: true, subtree: true });
      const timer = win.setInterval(bindExclusiveAccordion, 700);

      win.__methodAccCleanup = function () {
        observer.disconnect();
        win.clearInterval(timer);
      };
    })();
    """
)


# FOOTER

html(
    f"""
    <footer class="story-footer">
        <div>
            <b>SUMBER</b><br>
            Badan Pusat Statistik (BPS) · Kementerian Keuangan RI — SIKD.<br>
            Data hierarki {YEAR_HIER}; Data lain {YEAR_MAIN}.
        </div>

        <div>
            <b>METODE</b><br>
            Geospasial · Hierarki · Multivariat<br>
            Streamlit + Plotly
        </div>

        <div>
            <b>OLEH</b><br>
            Annisa Raihana M<br>
            222312986
        </div>

        <a href="#top">Kembali ke atas ↑</a>
    </footer>
    """
)
