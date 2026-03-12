import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np

st.set_page_config(page_title="AI MASTER TERMINAL v19", layout="wide", initial_sidebar_state="expanded")

# --- GLOBAL CSS (Final Visibility Fix) ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 28px !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #3e4251; }
    
    /* Sidebar Fix */
    section[data-testid="stSidebar"] { background-color: #111418 !important; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #ffffff !important; font-weight: bold; }

    /* Master Signal UI */
    .master-signal { background: linear-gradient(90deg, #f0b90b, #ff9900); color: #000000 !important; padding: 20px; border-radius: 15px; text-align: center; font-size: 26px; font-weight: bold; border: 3px solid #ffffff; margin-bottom: 20px; }
    .buy-signal { background-color: #00c076; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; }
    .sell-signal { background-color: #cf304a; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- TECHNICAL ENGINE ---
def add_indicators(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['Vol_Avg'] = df['Volume'].rolling(window=5).mean()
    return df

# --- SIDEBAR ---
st.sidebar.title("💎 MASTER AI v19")
nav = st.sidebar.radio("Navigate", ["Live Trading", "AI News", "P&L Summary", "Risk Mgmt"])

markets = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "GOLD": "GC=F", "CRUDE OIL": "CL=F", "NATURAL GAS": "NG=F",
    "BITCOIN": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD", "RELIANCE": "RELIANCE.NS"
}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]
tf_choice = st.sidebar.selectbox("Main Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=0)

st.sidebar.markdown("---")
entry_p = st.sidebar.number_input("Entry Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=1)

# --- DATA FETCH ---
@st.cache_data(ttl=5)
def get_live_data(symbol, tf):
    try:
        d1 = add_indicators(yf.download(symbol, period="2d", interval=tf))
        d15 = add_indicators(yf.download(symbol, period="5d", interval="15m"))
        return d1, d15
    except: return None, None

d_main, d_long = get_live_data(symbol, tf_choice)

if d_main is not None and not d_main.empty:
    # Fix: Converting series to float
    lp = float(d_main['Close'].iloc[-1])
    vol_curr = float(d_main['Volume'].iloc[-1])
    vol_avg = float(d_main['Vol_Avg'].iloc[-1])
    
    # Header & Manual Refresh
    h_col, r_col = st.columns([5, 1])
    h_col.title(f"🚀 {selected_asset} Terminal")
    if r_col.button("🔄 REFRESH"): st.rerun()

    # Metrics
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("LTP", f"{lp:.2f}")
    t2.metric("RSI", f"{d_main['RSI'].iloc[-1]:.1f}")
    
    trend_s = "UP" if d_main['EMA9'].iloc[-1] > d_main['EMA21'].iloc[-1] else "DOWN"
    trend_l = "UP" if d_long['EMA9'].iloc[-1] > d_long['EMA21'].iloc[-1] else "DOWN"
    t3.metric(f"Trend ({tf_choice})", trend_s)
    t4.metric("Major Trend", trend_l)

    if nav == "Live Trading":
        # 🐳 Operator Logic
        if vol_curr > (vol_avg * 1.5):
            op_color = "buy-signal" if d_main['Close'].iloc[-1] > d_main['Open'].iloc[-1] else "sell-signal"
            st.markdown(f'<div class="{op_color}">🐳 OPERATOR ALERT: HEAVY VOL DETECTED</div>', unsafe_allow_html=True)

        # 🎯 Master Signals
        st.markdown("---")
        if trend_s == "UP" and trend_l == "UP":
            st.markdown(f'<div class="master-signal">🔥 MASTER BUY CONFIRMED @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*1.01:.2f} | StopLoss: {d_main['EMA21'].iloc[-1]:.2f}")
        elif trend_s == "DOWN" and trend_l == "DOWN":
            st.markdown(f'<div class="master-signal">🔥 MASTER SELL CONFIRMED @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*0.99:.2f} | StopLoss: {d_main['EMA21'].iloc[-1]:.2f}")
        else:
            st.warning("⌛ SIDEWAYS: Waiting for Trend Sync (1m & 15m)...")

        # CANDLESTICK CHART
        chart_df = d_main.tail(50).reset_index()
        t_col = 'Datetime' if 'Datetime' in chart_df.columns else 'Date'
        chart_list = [[row[t_col].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        
        opt = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "xAxis": {"data": [x[0] for x in chart_list]},
            "yAxis": {"scale": True},
            "series": [{"type": "candlestick", "data": [x[1:] for x in chart_list], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]
        }
        st_echarts(options=opt, height="450px")

# Auto Refresh 10s
time.sleep(10)
st.rerun()
