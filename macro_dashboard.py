import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests, base64, json
from datetime import datetime

# ── GitHub commentary persistence ─────────────────────────────────────────────
GITHUB_TOKEN    = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO     = st.secrets.get("GITHUB_REPO", "")
COMMENTARY_PATH = "commentary.json"

def load_commentary():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return []
    url     = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{COMMENTARY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r       = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"]).decode()
        return json.loads(content)
    return []

def save_commentary(entries):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url     = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{COMMENTARY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = base64.b64encode(json.dumps(entries, indent=2).encode()).decode()
    r       = requests.get(url, headers=headers)
    sha     = r.json().get("sha", "") if r.status_code == 200 else ""
    payload = {"message": "Update commentary", "content": content}
    if sha:
        payload["sha"] = sha
    r2 = requests.put(url, headers=headers, json=payload)
    return r2.status_code in [200, 201]

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Macro Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background-color: #0d0f14; color: #e2e8f0; }
    .stApp { background-color: #0d0f14; }
    .metric-card { background: #151820; border: 1px solid #1e2330; border-radius: 8px; padding: 16px 20px; margin-bottom: 8px; }
    .metric-label { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: #6b7280; font-family: 'IBM Plex Mono', monospace; margin-bottom: 4px; }
    .metric-value { font-size: 22px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; color: #f1f5f9; }
    .metric-change-pos { color: #34d399; font-size: 13px; }
    .metric-change-neg { color: #f87171; font-size: 13px; }
    .signal-bull { background: #052e16; border: 1px solid #166534; color: #4ade80; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
    .signal-bear { background: #2d0a0a; border: 1px solid #7f1d1d; color: #f87171; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
    .signal-neutral { background: #1c1f2b; border: 1px solid #374151; color: #9ca3af; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
    .section-header { font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: #4b5563; font-family: 'IBM Plex Mono', monospace; border-bottom: 1px solid #1e2330; padding-bottom: 8px; margin-bottom: 16px; margin-top: 24px; }
    .inversion-alert { background: #2d1a00; border: 1px solid #92400e; border-radius: 8px; padding: 14px 18px; margin: 12px 0; color: #fbbf24; font-size: 13px; }
    .normal-curve { background: #052e16; border: 1px solid #166534; border-radius: 8px; padding: 14px 18px; margin: 12px 0; color: #4ade80; font-size: 13px; }
    .commentary-entry { background: #151820; border: 1px solid #1e2330; border-left: 3px solid #3b82f6; border-radius: 8px; padding: 16px 20px; margin-bottom: 12px; font-size: 14px; line-height: 1.7; color: #cbd5e1; }
    .commentary-date { font-size: 11px; font-family: 'IBM Plex Mono', monospace; color: #4b5563; margin-bottom: 8px; }
    .stTextArea textarea { background: #151820 !important; border: 1px solid #1e2330 !important; color: #e2e8f0 !important; font-family: 'IBM Plex Sans', sans-serif !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ── Tickers ───────────────────────────────────────────────────────────────────
TICKERS = {
    "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow Jones": "^DJI",
    "2Y Yield": "^IRX", "10Y Yield": "^TNX", "30Y Yield": "^TYX",
    "VIX": "^VIX",
    "EUR/USD": "EURUSD=X", "USD/JPY": "JPY=X", "USD/INR": "INR=X",
    "Gold": "GC=F", "WTI Oil": "CL=F",
}
PERIOD_OPTIONS = {"1 Week": "5d", "1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y"}

# ── Data fetch ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_data(period="3mo"):
    data = {}
    for name, ticker in TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if not hist.empty:
                data[name] = hist
        except Exception:
            pass
    return data

@st.cache_data(ttl=300)
def fetch_latest():
    prices = {}
    for name, ticker in TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if len(hist) >= 2:
                latest = hist["Close"].iloc[-1]
                prev   = hist["Close"].iloc[-2]
                prices[name] = {"price": latest, "change": ((latest - prev) / prev) * 100}
        except Exception:
            pass
    return prices

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_price(name, val):
    if "Yield" in name or "VIX" in name: return f"{val:.2f}%"
    if "/" in name: return f"{val:.4f}"
    if val > 1000: return f"{val:,.0f}"
    return f"{val:.2f}"

def price_color(chg): return "metric-change-pos" if chg >= 0 else "metric-change-neg"
def price_arrow(chg): return "▲" if chg >= 0 else "▼"

def ma_signal(series):
    if len(series) < 50: return "neutral"
    ma50  = series.rolling(50).mean().iloc[-1]
    ma200 = series.rolling(200).mean().iloc[-1] if len(series) >= 200 else None
    price = series.iloc[-1]
    if ma200:
        return "bull" if price > ma50 > ma200 else ("bear" if price < ma50 < ma200 else "neutral")
    return "bull" if price > ma50 else "bear"

def signal_badge(sig):
    labels = {"bull": "BULLISH", "bear": "BEARISH", "neutral": "NEUTRAL"}
    return f'<span class="signal-{sig}">{labels[sig]}</span>'

def hex_to_rgba(hex_color, alpha=0.07):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{alpha})"

def make_chart(hist, name, color="#3b82f6"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"], mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor=hex_to_rgba(color),
        name=name, hovertemplate="%{y:.2f}<extra></extra>"
    ))
    if hist["Close"].iloc[-1] > 100:
        if len(hist) >= 50:
            fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(50).mean(),
                mode="lines", line=dict(color="#f59e0b", width=1, dash="dot"), name="50 MA"))
        if len(hist) >= 200:
            fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(200).mean(),
                mode="lines", line=dict(color="#a78bfa", width=1, dash="dot"), name="200 MA"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=8,b=0), height=180, showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=10,color="#4b5563"), tickformat="%b %d", nticks=4),
        yaxis=dict(showgrid=True, gridcolor="#1e2330", tickfont=dict(size=10,color="#4b5563"), nticks=4),
        hovermode="x unified"
    )
    return fig

def yield_curve_chart(latest_prices):
    tenors = ["2Y Yield","10Y Yield","30Y Yield"]
    values = [latest_prices.get(t,{}).get("price", None) for t in tenors]
    if any(v is None for v in values): return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=["2Y","10Y","30Y"], y=values, mode="lines+markers",
        line=dict(color="#3b82f6", width=2), marker=dict(size=8, color="#3b82f6"),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=8,b=0), height=200,
        xaxis=dict(showgrid=False, tickfont=dict(size=11,color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="#1e2330", tickfont=dict(size=10,color="#4b5563"), ticksuffix="%"),
        hovermode="x"
    )
    return fig

# ── Layout ─────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Macro Dashboard")
st.markdown(f"<span style='font-family:IBM Plex Mono;font-size:12px;color:#4b5563;'>Last refreshed · {datetime.now().strftime('%b %d, %Y  %H:%M')}</span>", unsafe_allow_html=True)

period_label = st.selectbox("Chart period", list(PERIOD_OPTIONS.keys()), index=2, label_visibility="collapsed")
period = PERIOD_OPTIONS[period_label]

with st.spinner("Fetching market data…"):
    all_data  = fetch_data(period)
    latest_px = fetch_latest()

# Equities
st.markdown('<div class="section-header">Equities</div>', unsafe_allow_html=True)
eq_cols = st.columns(3)
for i, (name, color) in enumerate(zip(["S&P 500","Nasdaq","Dow Jones"], ["#3b82f6","#8b5cf6","#06b6d4"])):
    with eq_cols[i]:
        px   = latest_px.get(name, {})
        price, chg = px.get("price",0), px.get("change",0)
        hist = all_data.get(name)
        sig  = ma_signal(hist["Close"]) if hist is not None else "neutral"
        st.markdown(f'<div class="metric-card"><div class="metric-label">{name}</div><div class="metric-value">{fmt_price(name,price)}</div><div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D &nbsp;&nbsp; {signal_badge(sig)}</div></div>', unsafe_allow_html=True)
        if hist is not None:
            st.plotly_chart(make_chart(hist, name, color), use_container_width=True, config={"displayModeBar": False})

# Rates
st.markdown('<div class="section-header">Rates & Yield Curve</div>', unsafe_allow_html=True)
rc1, rc2 = st.columns([1,1])
with rc1:
    for name, color in zip(["2Y Yield","10Y Yield","30Y Yield"], ["#f59e0b","#3b82f6","#a78bfa"]):
        px = latest_px.get(name, {})
        price, chg = px.get("price",0), px.get("change",0)
        st.markdown(f'<div class="metric-card"><div class="metric-label">{name}</div><div class="metric-value">{fmt_price(name,price)}</div><div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D</div></div>', unsafe_allow_html=True)
with rc2:
    y2  = latest_px.get("2Y Yield",  {}).get("price", None)
    y10 = latest_px.get("10Y Yield", {}).get("price", None)
    if y2 and y10:
        spread = y10 - y2
        if spread < 0:
            st.markdown(f'<div class="inversion-alert">⚠️ <strong>Yield Curve Inverted</strong><br>10Y–2Y spread: <strong>{spread:.2f}%</strong> — historically a recession leading indicator.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="normal-curve">✓ <strong>Curve Normal</strong><br>10Y–2Y spread: <strong>+{spread:.2f}%</strong> — positive term premium, accommodative for risk assets.</div>', unsafe_allow_html=True)
    yc_fig = yield_curve_chart(latest_px)
    if yc_fig:
        st.plotly_chart(yc_fig, use_container_width=True, config={"displayModeBar": False})

# VIX
st.markdown('<div class="section-header">Volatility</div>', unsafe_allow_html=True)
vix_px  = latest_px.get("VIX", {})
vix_val, vix_chg = vix_px.get("price",0), vix_px.get("change",0)
vix_hist = all_data.get("VIX")
vc1, vc2 = st.columns([1,2])
with vc1:
    regime, regime_color = ("LOW VOLATILITY","#4ade80") if vix_val < 15 else ("MODERATE VOLATILITY","#fbbf24") if vix_val < 25 else ("HIGH VOLATILITY","#f87171") if vix_val < 35 else ("EXTREME VOLATILITY","#ef4444")
    st.markdown(f'<div class="metric-card"><div class="metric-label">VIX — Fear Index</div><div class="metric-value">{vix_val:.2f}</div><div class="{price_color(vix_chg)}">{price_arrow(vix_chg)} {abs(vix_chg):.2f}% 1D</div><div style="margin-top:8px;font-size:12px;font-family:IBM Plex Mono;color:{regime_color};">{regime}</div></div>', unsafe_allow_html=True)
with vc2:
    if vix_hist is not None:
        st.plotly_chart(make_chart(vix_hist, "VIX", "#f59e0b"), use_container_width=True, config={"displayModeBar": False})

# FX
st.markdown('<div class="section-header">FX</div>', unsafe_allow_html=True)
fx_cols = st.columns(3)
for i, (name, color) in enumerate(zip(["EUR/USD","USD/JPY","USD/INR"], ["#3b82f6","#f59e0b","#10b981"])):
    with fx_cols[i]:
        px = latest_px.get(name, {})
        price, chg = px.get("price",0), px.get("change",0)
        hist = all_data.get(name)
        st.markdown(f'<div class="metric-card"><div class="metric-label">{name}</div><div class="metric-value">{fmt_price(name,price)}</div><div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D</div></div>', unsafe_allow_html=True)
        if hist is not None:
            st.plotly_chart(make_chart(hist, name, color), use_container_width=True, config={"displayModeBar": False})

# Commodities
st.markdown('<div class="section-header">Commodities</div>', unsafe_allow_html=True)
cm_cols = st.columns(2)
for i, (name, color) in enumerate(zip(["Gold","WTI Oil"], ["#f59e0b","#6b7280"])):
    with cm_cols[i]:
        px = latest_px.get(name, {})
        price, chg = px.get("price",0), px.get("change",0)
        hist = all_data.get(name)
        st.markdown(f'<div class="metric-card"><div class="metric-label">{name}</div><div class="metric-value">${fmt_price(name,price)}</div><div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D</div></div>', unsafe_allow_html=True)
        if hist is not None:
            st.plotly_chart(make_chart(hist, name, color), use_container_width=True, config={"displayModeBar": False})

# ── MACRO COMMENTARY ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Weekly Macro Commentary</div>', unsafe_allow_html=True)

if "entries" not in st.session_state:
    with st.spinner("Loading saved commentary…"):
        st.session_state.entries = load_commentary()

if "new_note" not in st.session_state:
    st.session_state.new_note = ""

new_note = st.text_area(
    "Your macro view",
    value=st.session_state.new_note,
    height=140,
    placeholder="e.g. Fed held rates this week as CPI came in hotter than expected...",
    label_visibility="collapsed"
)

col_save, col_clear = st.columns([1, 5])
with col_save:
    if st.button("💾 Save Entry"):
        if new_note.strip():
            entry = {
                "date": datetime.now().strftime("%B %d, %Y"),
                "text": new_note.strip()
            }
            st.session_state.entries.insert(0, entry)
            if save_commentary(st.session_state.entries):
                st.success("Saved!")
            else:
                st.warning("Saved locally only — check your GitHub token in secrets.")
            st.session_state.new_note = ""
            st.rerun()

# Display past entries
if st.session_state.entries:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    for entry in st.session_state.entries:
        st.markdown(f'<div class="commentary-entry"><div class="commentary-date">{entry["date"]}</div>{entry["text"]}</div>', unsafe_allow_html=True)

st.markdown("""
---
<div style='font-family:IBM Plex Mono;font-size:11px;color:#374151;text-align:center;padding:8px 0;'>
Data via Yahoo Finance · Refreshes every 5 min · Built with Python + Streamlit
</div>
""", unsafe_allow_html=True)
