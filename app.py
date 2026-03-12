import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="Pro Terminal v8.0", layout="wide", initial_sidebar_state="expanded")

# --- BLACK-SCHOLES FOR GREEKS ---
def calculate_greeks(S, K, T, r, sigma, type="call"):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if type == "call":
        delta = norm.cdf(d1)
        theta = -(S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))) - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        delta = norm.cdf(d1) - 1
        theta = -(S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))) + r * K * np.exp(-r * T) * norm.cdf(-d2)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T)
    return {"Delta": round(delta, 2), "Theta": round(theta/365, 2), "Gamma": round(gamma, 4), "Vega": round(vega/100, 2)}

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: white; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 26px !important; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4251; }
    .buy-signal { background-color: #00c076; color: white; padding: 15px; border-radius: 8px; text-align: center; font-size: 22px; font-weight: bold; }
    .sell-signal { background-color: #cf304a; color: white; padding: 15px; border-radius: 8px; text-align: center; font-size: 22px; font-weight: bold; }
    .greek-box { background: #262a33; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #444; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("💹 Ultimate Terminal")
view_mode = st.sidebar.radio("Navigate", ["Live Trading", "Option Greeks", "Risk Management", "Strategy Stats", "Market News"])

market_map = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN", "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD"}
selected_asset = st.sidebar.selectbox("Market Asset", list(market_map.keys()))
symbol = market_map[selected_asset]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
e_price = st.sidebar.number_input("Entry Price", value=0.0)
qty_val = st.sidebar.number_input("Qty", value=1)
goal = st.sidebar.number_input("Daily Goal (₹)", value=5000.0)

# --- DATA ENGINE ---
@st.cache_data(ttl=5)
def fetch_data(symbol, tf):
    data = yf.download(symbol, period="5d", interval=tf)
    if data.empty: return None, []
    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
    data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
    data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
    return data

data = fetch_data(symbol, tf)

if data is not None:
    lp = float(data['Close'].iloc[-1])
    
    # Header
    col_t, col_r = st.columns([5, 1])
    col_t.title(f"🚀 {selected_asset}")
    if col_r.button("🔄 REFRESH"): st.rerun()

    # P&L Tracker
    if e_price > 0:
        pnl = (lp - e_price) * qty_val
        st.sidebar.metric("Live P&L", f"{pnl:.2f}", delta=pnl)
        if pnl >= goal: st.balloons()

    # --- VIEWS ---
    if view_mode == "Live Trading":
        l9, l21 = data['EMA_9'].iloc[-1], data['EMA_21'].iloc[-1]
        p9, p21 = data['EMA_9'].iloc[-2], data['EMA_21'].iloc[-2]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("LTP", f"{lp:.2f}")
        c2.metric("Trend", "BULLISH" if l9 > l21 else "BEARISH")
        diff = 50 if "NIFTY" in selected_asset else 100
        atm = round(lp / diff) * diff
        c3.metric("ATM Strike", f"{atm}")

        if (l9 > l21) and (p9 <= p21):
            st.markdown(f'<div class="buy-signal">🟢 BUY CALL (CE) @ {lp:.2f}</div>', unsafe_allow_html=True)
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-signal">🔴 BUY PUT (PE) @ {lp:.2f}</div>', unsafe_allow_html=True)

        chart_df = data.tail(50).reset_index()
        c_data = [[row['Date' if 'Date' in row else 'Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        option = {"xAxis": {"data": [d[0] for d in c_data]}, "yAxis": {"scale": True}, "series": [{"type": "candlestick", "data": [d[1:] for d in c_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=option, height="400px")

    elif view_mode == "Option Greeks":
        st.header("📉 Real-Time Option Greeks (ATM)")
        # Inputs for Black-Scholes
        diff = 50 if "NIFTY" in selected_asset else 100
        atm = round(lp / diff) * diff
        vol = 0.15 # Approx IV
        time_exp = 5 / 365 # Approx 5 days to expiry
        
        g_call = calculate_greeks(lp, atm, time_exp, 0.07, vol, "call")
        g_put = calculate_greeks(lp, atm, time_exp, 0.07, vol, "put")
        
        st.subheader(f"Strike: {atm}")
        col_c, col_p = st.columns(2)
        with col_c:
            st.write("🟢 **CALL GREEKS**")
            for k, v in g_call.items(): st.markdown(f'<div class="greek-box">{k}: {v}</div>', unsafe_allow_html=True)
        with col_p:
            st.write("🔴 **PUT GREEKS**")
            for k, v in g_put.items(): st.markdown(f'<div class="greek-box">{k}: {v}</div>', unsafe_allow_html=True)
        

    elif view_mode == "Risk Management":
        st.header("⚖️ Position Sizing")
        cap = st.number_input("Capital (₹)", value=100000)
        risk = st.slider("Risk %", 1, 5, 2)
        sl_pts = st.number_input("SL Points", value=20.0)
        if sl_pts > 0:
            pos_size = (cap * (risk/100)) / sl_pts
            st.success(f"Quantity: {int(pos_size)} Units")

    elif view_mode == "Market News":
        st.header("📰 News")
        try:
            for n in yf.Ticker(symbol).news[:5]: st.info(f"**{n['title']}**\n{n['publisher']}")
        except: st.write("No news.")

# Auto Refresh
time.sleep(10)
st.rerun()
