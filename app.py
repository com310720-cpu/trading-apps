import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np

st.set_page_config(page_title="AI MASTER TERMINAL v16", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: white; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 26px !important; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4251; }
    .operator-buy { background-color: #155724; color: #d4edda; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px; }
    .operator-sell { background-color: #721c24; color: #f8d7da; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px; }
    .master-signal { background: linear-gradient(90deg, #f0b90b, #e0a800); color: black; padding: 20px; border-radius: 12px; text-align: center; font-size: 28px; font-weight: bold; border: 4px solid white; }
    .pnl-summary { background-color: #1c2127; border: 1px dashed #f0b90b; padding: 15px; border-radius: 8px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE ---
def get_indicators(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['Vol_Avg'] = df['Volume'].rolling(window=5).mean()
    return df

# --- SIDEBAR ---
st.sidebar.title("MASTER TERMINAL v16")
nav = st.sidebar.radio("Navigate", ["Live Trading", "Day-End Summary", "Risk Management"])

markets = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "GOLD": "GC=F", "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD"}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]

st.sidebar.markdown("---")
entry_p = st.sidebar.number_input("Entry Price", value=0.0)
qty = st.sidebar.number_input("Qty", value=1)

# Day End Tracking
if 'total_pnl' not in st.session_state: st.session_state.total_pnl = 0.0

# --- DATA FETCH (Dual Timeframe) ---
@st.cache_data(ttl=5)
def fetch_dual_tf(symbol):
    d_short = get_indicators(yf.download(symbol, period="2d", interval="1m"))
    d_long = get_indicators(yf.download(symbol, period="5d", interval="15m"))
    return d_short, d_long

d_1m, d_15m = fetch_dual_tf(symbol)

if d_1m is not None and d_15m is not None:
    # Current values
    lp = float(d_1m['Close'].iloc[-1])
    vol_curr, vol_avg = d_1m['Volume'].iloc[-1], d_1m['Vol_Avg'].iloc[-1]
    
    # Trend Analysis
    trend_1m = "UP" if d_1m['EMA9'].iloc[-1] > d_1m['EMA21'].iloc[-1] else "DOWN"
    trend_15m = "UP" if d_15m['EMA9'].iloc[-1] > d_15m['EMA21'].iloc[-1] else "DOWN"

    if nav == "Live Trading":
        st.title(f"📊 {selected_asset} Pro Dashboard")
        
        # Dual Trend Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("LTP", f"{lp:.2f}")
        m2.metric("Short Trend (1m)", trend_1m)
        m3.metric("Major Trend (15m)", trend_15m)

        # Operator Alert
        if vol_curr > (vol_avg * 1.5):
            div_class = "operator-buy" if d_1m['Close'].iloc[-1] > d_1m['Open'].iloc[-1] else "operator-sell"
            st.markdown(f'<div class="{div_class}">🐳 OPERATOR ACTIVITY: {"BUYING" if "buy" in div_class else "SELLING"} DETECTED</div>', unsafe_allow_html=True)

        # Master Confirmed Signal
        st.markdown("---")
        if trend_1m == "UP" and trend_15m == "UP":
            st.markdown(f'<div class="master-signal">🔥 MASTER BUY CONFIRMED (CALL) @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*1.01:.2f} | SL: {d_1m['EMA21'].iloc[-1]:.2f}")
        elif trend_1m == "DOWN" and trend_15m == "DOWN":
            st.markdown(f'<div class="master-signal">🔥 MASTER SELL CONFIRMED (PUT) @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*0.99:.2f} | SL: {d_1m['EMA21'].iloc[-1]:.2f}")
        else:
            st.warning("⚠️ TREND MISMATCH: 1m and 15m are not in sync. Avoid fresh entry.")

        # Real-time Chart
        chart_df = d_1m.tail(50).reset_index()
        c_data = [[row['Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        option = {"xAxis": {"data": [d[0] for d in c_data]}, "yAxis": {"scale": True}, "series": [{"type": "candlestick", "data": [d[1:] for d in c_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=option, height="400px")

    elif nav == "Day-End Summary":
        st.title("📝 Trading Day Summary")
        if entry_p > 0:
            current_trade_pnl = (lp - entry_p) * qty
            if st.button("Save Trade to Summary"):
                st.session_state.total_pnl += current_trade_pnl
                st.success("Trade Saved!")
        
        st.markdown(f'''<div class="pnl-summary">
            <h3>Total Realized P&L: <span style="color:{'#00ff00' if st.session_state.total_pnl >=0 else '#ff0000'}">
            ₹ {st.session_state.total_pnl:.2f}</span></h3>
            <p>Market Status: {"Closed" if time.localtime().tm_hour >= 16 else "Open"}</p>
        </div>''', unsafe_allow_html=True)

# Auto Refresh 10s
time.sleep(10)
st.rerun()
