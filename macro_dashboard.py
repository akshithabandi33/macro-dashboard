import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ── Page config ──────────────────────────────────────────────────────────────
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

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
        background-color: #0d0f14;
        color: #e2e8f0;
    }
    .stApp { background-color: #0d0f14; }

    .metric-card {
        background: #151820;
        border: 1px solid #1e2330;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 8px;
    }
    .metric-label {
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6b7280;
        font-family: 'IBM Plex Mono', monospace;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 600;
        font-family: 'IBM Plex Mono', monospace;
        color: #f1f5f9;
    }
    .metric-change-pos { color: #34d399; font-size: 13px; }
    .metric-change-neg { color: #f87171; font-size: 13px; }

    .signal-bull {
        background: #052e16;
        border: 1px solid #166534;
        color: #4ade80;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 500;
    }
    .signal-bear {
        background: #2d0a0a;
        border: 1px solid #7f1d1d;
        color: #f87171;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 500;
    }
    .signal-neutral {
        background: #1c1f2b;
        border: 1px solid #374151;
        color: #9ca3af;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 500;
    }
    .section-header {
        font-size: 11px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #4b5563;
        font-family: 'IBM Plex Mono', monospace;
        border-bottom: 1px solid #1e2330;
        padding-bottom: 8px;
        margin-bottom: 16px;
        margin-top: 24px;
    }
    .inversion-alert {
        background: #2d1a00;
        border: 1px solid #92400e;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 12px 0;
        color: #fbbf24;
        font-size: 13px;
    }
    .normal-curve {
        background: #052e16;
        border: 1px solid #166534;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 12px 0;
        color: #4ade80;
        font-size: 13px;
    }
    .commentary-box {
        background: #151820;
        border: 1px solid #1e2330;
        border-left: 3px solid #3b82f6;
        border-radius: 8px;
        padding: 16px 20px;
        margin-top: 8px;
        font-size: 14px;
        line-height: 1.7;
        color: #cbd5e1;
    }
    h1 { font-family: 'IBM Plex Sans', sans-serif !important; font-weight: 600 !important; }
    .stTextArea textarea {
        background: #151820 !important;
        border: 1px solid #1e2330 !important;
        color: #e2e8f0 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 14px !important;
    }
    div[data-testid="stSelectbox"] { margin-bottom: 0; }
    .stSelectbox > div > div {
        background: #151820 !important;
        border-color: #1e2330 !important;
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Tickers ───────────────────────────────────────────────────────────────────
TICKERS = {
    # Equities
    "S&P 500":   "^GSPC",
    "Nasdaq":    "^IXIC",
    "Dow Jones": "^DJI",
    # Rates
    "2Y Yield":  "^IRX",
    "10Y Yield": "^TNX",
    "30Y Yield": "^TYX",
    # Vol
    "VIX":       "^VIX",
    # FX
    "EUR/USD":   "EURUSD=X",
    "USD/JPY":   "JPY=X",
    "USD/INR":   "INR=X",
    # Commodities
    "Gold":      "GC=F",
    "WTI Oil":   "CL=F",
}

PERIOD_OPTIONS = {"1 Week": "5d", "1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y"}

# ── Data fetch ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_data(period="3mo"):
    data = {}
    for name, ticker in TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=period)
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
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                latest = hist["Close"].iloc[-1]
                prev   = hist["Close"].iloc[-2]
                chg    = ((latest - prev) / prev) * 100
                prices[name] = {"price": latest, "change": chg}
        except Exception:
            pass
    return prices

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_price(name, val):
    if "Yield" in name or "VIX" in name:
        return f"{val:.2f}%"
    if "/" in name:
        return f"{val:.4f}"
    if val > 1000:
        return f"{val:,.0f}"
    return f"{val:.2f}"

def price_color(chg):
    return "metric-change-pos" if chg >= 0 else "metric-change-neg"

def price_arrow(chg):
    return "▲" if chg >= 0 else "▼"

def ma_signal(series):
    if len(series) < 50:
        return "neutral"
    ma50  = series.rolling(50).mean().iloc[-1]
    ma200 = series.rolling(200).mean().iloc[-1] if len(series) >= 200 else None
    price = series.iloc[-1]
    if ma200:
        return "bull" if price > ma50 > ma200 else ("bear" if price < ma50 < ma200 else "neutral")
    return "bull" if price > ma50 else "bear"

def signal_badge(sig):
    labels = {"bull": "BULLISH", "bear": "BEARISH", "neutral": "NEUTRAL"}
    return f'<span class="signal-{sig}">{labels[sig]}</span>'

def make_chart(hist, name, color="#3b82f6"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.07)",
        name=name, hovertemplate="%{y:.2f}<extra></extra>"
    ))
    # MA overlays for price series
    if hist["Close"].iloc[-1] > 100:
        if len(hist) >= 50:
            ma50 = hist["Close"].rolling(50).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma50, mode="lines",
                line=dict(color="#f59e0b", width=1, dash="dot"), name="50 MA"))
        if len(hist) >= 200:
            ma200 = hist["Close"].rolling(200).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma200, mode="lines",
                line=dict(color="#a78bfa", width=1, dash="dot"), name="200 MA"))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0),
        height=180,
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=True, tickfont=dict(size=10, color="#4b5563"),
                   tickformat="%b %d", nticks=4),
        yaxis=dict(showgrid=True, gridcolor="#1e2330", tickfont=dict(size=10, color="#4b5563"), nticks=4),
        hovermode="x unified"
    )
    return fig

def yield_curve_chart(latest_prices):
    tenors = ["2Y Yield", "10Y Yield", "30Y Yield"]
    labels = ["2Y", "10Y", "30Y"]
    values = [latest_prices.get(t, {}).get("price", None) for t in tenors]
    if any(v is None for v in values):
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=values, mode="lines+markers",
        line=dict(color="#3b82f6", width=2),
        marker=dict(size=8, color="#3b82f6"),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0),
        height=200,
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="#1e2330", tickfont=dict(size=10, color="#4b5563"),
                   ticksuffix="%"),
        hovermode="x"
    )
    return fig

# ── Layout ─────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Macro Dashboard")
st.markdown(f"<span style='font-family:IBM Plex Mono;font-size:12px;color:#4b5563;'>Last refreshed · {datetime.now().strftime('%b %d, %Y  %H:%M')}</span>", unsafe_allow_html=True)

period_label = st.selectbox("Chart period", list(PERIOD_OPTIONS.keys()), index=2, label_visibility="collapsed")
period = PERIOD_OPTIONS[period_label]

with st.spinner("Fetching market data…"):
    all_data   = fetch_data(period)
    latest_px  = fetch_latest()

# ── EQUITIES ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Equities</div>', unsafe_allow_html=True)
eq_cols = st.columns(3)
equity_names  = ["S&P 500", "Nasdaq", "Dow Jones"]
equity_colors = ["#3b82f6", "#8b5cf6", "#06b6d4"]

for i, (name, color) in enumerate(zip(equity_names, equity_colors)):
    with eq_cols[i]:
        px = latest_px.get(name, {})
        price = px.get("price", 0)
        chg   = px.get("change", 0)
        hist  = all_data.get(name)
        sig   = ma_signal(hist["Close"]) if hist is not None else "neutral"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{name}</div>
            <div class="metric-value">{fmt_price(name, price)}</div>
            <div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D &nbsp;&nbsp; {signal_badge(sig)}</div>
        </div>""", unsafe_allow_html=True)
        if hist is not None:
            st.plotly_chart(make_chart(hist, name, color), use_container_width=True, config={"displayModeBar": False})

# ── RATES & YIELD CURVE ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">Rates & Yield Curve</div>', unsafe_allow_html=True)
rc1, rc2 = st.columns([1, 1])

with rc1:
    rate_names  = ["2Y Yield", "10Y Yield", "30Y Yield"]
    rate_colors = ["#f59e0b", "#3b82f6", "#a78bfa"]
    for name, color in zip(rate_names, rate_colors):
        px    = latest_px.get(name, {})
        price = px.get("price", 0)
        chg   = px.get("change", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{name}</div>
            <div class="metric-value">{fmt_price(name, price)}</div>
            <div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D</div>
        </div>""", unsafe_allow_html=True)

with rc2:
    y2  = latest_px.get("2Y Yield",  {}).get("price", None)
    y10 = latest_px.get("10Y Yield", {}).get("price", None)
    if y2 and y10:
        spread = y10 - y2
        if spread < 0:
            st.markdown(f'<div class="inversion-alert">⚠️ <strong>Yield Curve Inverted</strong><br>10Y–2Y spread: <strong>{spread:.2f}%</strong> — historically a recession leading indicator. Monitor duration positioning carefully.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="normal-curve">✓ <strong>Curve Normal</strong><br>10Y–2Y spread: <strong>+{spread:.2f}%</strong> — positive term premium, accommodative for risk assets.</div>', unsafe_allow_html=True)

    yc_fig = yield_curve_chart(latest_px)
    if yc_fig:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.plotly_chart(yc_fig, use_container_width=True, config={"displayModeBar": False})

# ── VOLATILITY ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Volatility</div>', unsafe_allow_html=True)
vix_px   = latest_px.get("VIX", {})
vix_val  = vix_px.get("price", 0)
vix_chg  = vix_px.get("change", 0)
vix_hist = all_data.get("VIX")

vc1, vc2 = st.columns([1, 2])
with vc1:
    if vix_val < 15:
        regime, regime_color = "LOW VOLATILITY", "#4ade80"
    elif vix_val < 25:
        regime, regime_color = "MODERATE VOLATILITY", "#fbbf24"
    elif vix_val < 35:
        regime, regime_color = "HIGH VOLATILITY", "#f87171"
    else:
        regime, regime_color = "EXTREME VOLATILITY", "#ef4444"

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">VIX — Fear Index</div>
        <div class="metric-value">{vix_val:.2f}</div>
        <div class="{price_color(vix_chg)}">{price_arrow(vix_chg)} {abs(vix_chg):.2f}% 1D</div>
        <div style="margin-top:8px;font-size:12px;font-family:'IBM Plex Mono';color:{regime_color};">{regime}</div>
    </div>""", unsafe_allow_html=True)
with vc2:
    if vix_hist is not None:
        st.plotly_chart(make_chart(vix_hist, "VIX", "#f59e0b"), use_container_width=True, config={"displayModeBar": False})

# ── FX ─────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">FX</div>', unsafe_allow_html=True)
fx_names  = ["EUR/USD", "USD/JPY", "USD/INR"]
fx_colors = ["#3b82f6", "#f59e0b", "#10b981"]
fx_cols   = st.columns(3)

for i, (name, color) in enumerate(zip(fx_names, fx_colors)):
    with fx_cols[i]:
        px    = latest_px.get(name, {})
        price = px.get("price", 0)
        chg   = px.get("change", 0)
        hist  = all_data.get(name)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{name}</div>
            <div class="metric-value">{fmt_price(name, price)}</div>
            <div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D</div>
        </div>""", unsafe_allow_html=True)
        if hist is not None:
            st.plotly_chart(make_chart(hist, name, color), use_container_width=True, config={"displayModeBar": False})

# ── COMMODITIES ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Commodities</div>', unsafe_allow_html=True)
cm_cols = st.columns(2)
comm_names  = ["Gold", "WTI Oil"]
comm_colors = ["#f59e0b", "#6b7280"]

for i, (name, color) in enumerate(zip(comm_names, comm_colors)):
    with cm_cols[i]:
        px    = latest_px.get(name, {})
        price = px.get("price", 0)
        chg   = px.get("change", 0)
        hist  = all_data.get(name)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{name}</div>
            <div class="metric-value">${fmt_price(name, price)}</div>
            <div class="{price_color(chg)}">{price_arrow(chg)} {abs(chg):.2f}% 1D</div>
        </div>""", unsafe_allow_html=True)
        if hist is not None:
            st.plotly_chart(make_chart(hist, name, color), use_container_width=True, config={"displayModeBar": False})

# ── MACRO COMMENTARY ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Weekly Macro Commentary</div>', unsafe_allow_html=True)
st.markdown("*Write your own macro view below — track your thesis week over week.*")

if "commentary" not in st.session_state:
    st.session_state.commentary = ""

commentary = st.text_area(
    "Your macro view",
    value=st.session_state.commentary,
    height=140,
    placeholder="e.g. Fed held rates this week as CPI came in hotter than expected at 3.4%. The 2Y-10Y spread widened to +18bps, suggesting the market is pricing in a soft landing. I'm watching for NFP Friday — a strong print could push the 10Y back above 4.5% and pressure equity multiples...",
    label_visibility="collapsed"
)
st.session_state.commentary = commentary

if commentary:
    st.markdown(f'<div class="commentary-box">{commentary}</div>', unsafe_allow_html=True)

st.markdown("""
---
<div style='font-family:IBM Plex Mono;font-size:11px;color:#374151;text-align:center;padding:8px 0;'>
Data via Yahoo Finance · Refreshes every 5 min · Built with Python + Streamlit
</div>
""", unsafe_allow_html=True)
