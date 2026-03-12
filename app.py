import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="Master AI Terminal", layout="wide", initial_sidebar_state="expanded")

# --- ULTIMATE CSS (Global Visibility & Theme) ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: white; }
    /* Metric Boxes Visibility */
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 26px !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 16px !important; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4251; }
    
    /* Sidebar Text Visibility Fix */
    section[data-testid="stSidebar"] { background-color: #111418 !important; }
    section[data-testid="stSidebar"] .stText, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span {
        color: #ffffff !important; font-weight: bold !important;
    }

    /* Signal Cards */
    .buy-card { background-color: #00c076; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
    .sell-card { background-color: #cf304a; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
    
    /* Greeks Table Visibility */
    .greek-box { background-color: #262a33; border: 1px solid #4e5461; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 5px; }
    .greek-val { color: #00ff00; font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE: GREEKS ---
def get_greeks(S, K, T, r, sigma, type="call"):
    if T <= 0: T = 0.00001
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if type == "call":
        delta = norm.cdf(d1)
        theta = -(S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))) - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        delta = norm.cdf(d1) - 1
        theta = -(S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))) + r * K * np.exp(-r * T) * norm.cdf(-d2)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return {"DELTA": round(delta, 2), "THETA": round(theta/365, 2), "GAMMA": round(gamma, 4)}

# --- SIDEBAR CONTROLS ---
st.sidebar.title("💹 AI PRO TERMINAL")
nav_mode = st.sidebar.radio("Navigate", ["Live Trading", "Option Greeks", "Risk Management", "Trade Reports"])

# COMPLETE MARKET LIST
markets = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "GOLD": "GC=F", "CRUDE OIL": "CL=F", "NATURAL GAS": "NG=F",
    "BITCOIN": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD"
}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Live P&L Monitor")
entry_p = st.sidebar.number_input("Entry Price", value=0.0)
qty_v = st.sidebar.number_input("Quantity", value=1)
goal_p = st.sidebar.number_input("Daily Goal (₹)", value=5000.0)

# --- DATA ENGINE ---
@st.cache_data(ttl=5)
def get_live_market_data(symbol, tf):
    df = yf.download(symbol, period="2d", interval=tf)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    return df

data = get_live_market_data(symbol, timeframe)

if data is not None:
    lp = float(data['Close'].iloc[-1])
    
    # Header & Manual Refresh
    c_h, c_r = st.columns([5, 1])
    c_h.title(f"🚀 {selected_asset} Terminal")
    if c_r.button("🔄 REFRESH"): st.rerun()

    # Live P&L sidebar logic
    if entry_p > 0:
        pnl = (lp - entry_p) * qty_v
        st.sidebar.metric("Live P&L", f"{pnl:.2f}", delta=f"{pnl:.2f} ₹")
        if pnl >= goal_p: st.balloons()

    # --- TOP METRICS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"{lp:.2f}")
    col2.metric("Market Trend", "BULLISH 🟢" if data['EMA9'].iloc[-1] > data['EMA21'].iloc[-1] else "BEARISH 🔴")
    diff = 50 if "NIFTY" in selected_asset else 100
    atm = round(lp / diff) * diff
    col3.metric("ATM Strike", f"{atm}")

    # --- VIEWS ---
    if nav_mode == "Live Trading":
        l9, l21 = data['EMA9'].iloc[-1], data['EMA21'].iloc[-1]
        p9, p21 = data['EMA9'].iloc[-2], data['EMA21'].iloc[-2]

        if (l9 > l21) and (p9 <= p21):
            st.markdown(f'<div class="buy-card">🚀 ENTRY: BUY CALL (CE) @ {lp:.2f}</div>', unsafe_allow_html=True)
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-card">📉 ENTRY: BUY PUT (PE) @ {lp:.2f}</div>', unsafe_allow_html=True)
        else:
            st.info("⌛ Waiting for High-Accuracy Crossover...")

        # Professional Candlestick Chart
        chart_df = data.tail(60).reset_index()
        c_data = [[row['Date' if 'Date' in row else 'Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        option = {"xAxis": {"data": [d[0] for d in c_data]}, "yAxis": {"scale": True}, "series": [{"type": "candlestick", "data": [d[1:] for d in c_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=option, height="450px")

    elif nav_mode == "Option Greeks":
        st.subheader("📉 ATM Option Greeks")
        g_c = get_greeks(lp, atm, 0.02, 0.07, 0.20, "call")
        g_p = get_greeks(lp, atm, 0.02, 0.07, 0.20, "put")
        
        c_c, c_p = st.columns(2)
        with c_c:
            st.write("🟢 **CALL GREEKS**")
            for k, v in g_c.items(): st.markdown(f'<div class="greek-box">{k}<br><span class="greek-val">{v}</span></div>', unsafe_allow_html=True)
        with c_p:
            st.write("🔴 **PUT GREEKS**")
            for k, v in g_p.items(): st.markdown(f'<div class="greek-box">{k}<br><span class="greek-val">{v}</span></div>', unsafe_allow_html=True)

    elif nav_mode == "Risk Management":
        st.header("⚖️ Risk Calculator")
        cap = st.number_input("Total Capital (₹)", value=100000)
        risk_per = st.slider("Risk per trade (%)", 1, 5, 2)
        sl_pts = st.number_input("Stop Loss Points", value=20.0)
        if sl_pts > 0:
            qty = (cap * (risk_per/100)) / sl_pts
            st.success(f"Recommended Quantity: **{int(qty)} Units**")

    elif nav_mode == "Trade Reports":
        st.header("📂 Download Reports")
        st.write("Current session logs are ready for export.")
        if st.button("Generate CSV"):
            st.write("Exporting...")

# Auto Refresh 10s
time.sleep(10)
st.rerun()
