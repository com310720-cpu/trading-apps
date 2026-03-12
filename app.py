import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="AI MASTER TERMINAL v20", layout="wide", initial_sidebar_state="expanded")

# --- GLOBAL CSS (Visibility & High Contrast) ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 26px !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #3e4251; }
    section[data-testid="stSidebar"] { background-color: #111418 !important; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #ffffff !important; font-weight: bold; }
    .master-signal { background: linear-gradient(90deg, #f0b90b, #ff9900); color: #000000 !important; padding: 20px; border-radius: 15px; text-align: center; font-size: 26px; font-weight: bold; border: 3px solid #ffffff; margin-bottom: 15px; }
    .greek-card { background-color: #1e2130; color: #ffffff !important; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #3e4251; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE: INDICATORS & GREEKS ---
def add_indicators(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['Vol_Avg'] = df['Volume'].rolling(window=5).mean()
    return df

def get_greeks(S, K, T, r, sigma, type="call"):
    if T <= 0: T = 0.00001
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if type == "call":
        delta = norm.cdf(d1); theta = -(S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))) - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        delta = norm.cdf(d1) - 1; theta = -(S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))) + r * K * np.exp(-r * T) * norm.cdf(-d2)
    return {"DELTA": round(delta, 2), "THETA": round(theta/365, 2), "GAMMA": round(norm.pdf(d1)/(S*sigma*np.sqrt(T)), 4)}

# --- SIDEBAR ---
st.sidebar.title("💎 MASTER AI v20")
nav = st.sidebar.radio("Navigate", ["Live Trading", "Option Greeks", "AI News", "P&L Summary", "Risk Mgmt"])

markets = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN", "GOLD": "GC=F", "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD", "ETH": "ETH-USD"}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]
tf_choice = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
entry_p = st.sidebar.number_input("Entry Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=1)

# --- DATA FETCH ---
@st.cache_data(ttl=5)
def get_data(symbol, tf):
    try:
        d1 = add_indicators(yf.download(symbol, period="2d", interval=tf))
        d15 = add_indicators(yf.download(symbol, period="5d", interval="15m"))
        return d1, d15
    except: return None, None

d_main, d_long = get_data(symbol, tf_choice)

if d_main is not None and not d_main.empty:
    lp = float(d_main['Close'].iloc[-1])
    
    # Top Bar
    h_col, r_col = st.columns([5, 1])
    h_col.title(f"🚀 {selected_asset} Terminal")
    if r_col.button("🔄 REFRESH"): st.rerun()

    # Shared Metrics
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("LTP", f"{lp:.2f}")
    t2.metric("RSI", f"{d_main['RSI'].iloc[-1]:.1f}")
    trend_s = "UP" if d_main['EMA9'].iloc[-1] > d_main['EMA21'].iloc[-1] else "DOWN"
    trend_l = "UP" if d_long['EMA9'].iloc[-1] > d_long['EMA21'].iloc[-1] else "DOWN"
    t3.metric(f"Trend ({tf_choice})", trend_s)
    t4.metric("Major Trend (15m)", trend_l)

    if nav == "Live Trading":
        # Master Signal
        st.markdown("---")
        if trend_s == "UP" and trend_l == "UP":
            st.markdown(f'<div class="master-signal">🔥 MASTER BUY CONFIRMED @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*1.01:.2f} | SL: {d_main['EMA21'].iloc[-1]:.2f}")
        elif trend_s == "DOWN" and trend_l == "DOWN":
            st.markdown(f'<div class="master-signal">🔥 MASTER SELL CONFIRMED @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*0.99:.2f} | SL: {d_main['EMA21'].iloc[-1]:.2f}")
        else:
            st.warning("⌛ SIDEWAYS: Waiting for Trend Sync...")

        # CHART FIX
        chart_df = d_main.tail(50).reset_index()
        # Finding time column dynamically
        t_col = [c for c in chart_df.columns if c in ['Datetime', 'Date']][0]
        chart_list = [[row[t_col].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        
        opt = {"tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}}, "xAxis": {"data": [x[0] for x in chart_list]}, "yAxis": {"scale": True},
               "series": [{"type": "candlestick", "data": [x[1:] for x in chart_list], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=opt, height="450px")

    elif nav == "Option Greeks":
        st.header("📉 ATM Option Greeks")
        diff = 50 if "NIFTY" in selected_asset else 100
        atm = round(lp / diff) * diff
        g_c = get_greeks(lp, atm, 0.02, 0.07, 0.20, "call")
        g_p = get_greeks(lp, atm, 0.02, 0.07, 0.20, "put")
        
        col_c, col_p = st.columns(2)
        with col_c:
            st.subheader(f"🟢 {atm} CE")
            for k,v in g_c.items(): st.markdown(f'<div class="greek-card">{k}: {v}</div>', unsafe_allow_html=True)
        with col_p:
            st.subheader(f"🔴 {atm} PE")
            for k,v in g_p.items(): st.markdown(f'<div class="greek-card">{k}: {v}</div>', unsafe_allow_html=True)

# Auto Refresh 10s
time.sleep(10)
st.rerun()
