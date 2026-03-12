import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from datetime import datetime

st.set_page_config(page_title="AI MASTER TERMINAL v18", layout="wide", initial_sidebar_state="expanded")

# --- FINAL GLOBAL CSS (Colour & Visibility Fix) ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: #ffffff; }
    /* Metric Cards Fix */
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 28px !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 16px !important; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #3e4251; box-shadow: 0px 4px 10px rgba(0,0,0,0.5); }
    
    /* Sidebar Text & Dropdown Fix */
    section[data-testid="stSidebar"] { background-color: #111418 !important; border-right: 1px solid #333; }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {
        color: #ffffff !important; font-weight: bold !important;
    }

    /* Signal & Alert Boxes */
    .master-signal { background: linear-gradient(90deg, #f0b90b, #ff9900); color: #000000 !important; padding: 25px; border-radius: 15px; text-align: center; font-size: 30px; font-weight: bold; border: 4px solid #ffffff; margin-bottom: 20px; }
    .operator-buy { background-color: #00c076; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; border: 2px solid #ffffff; margin-bottom: 10px; }
    .operator-sell { background-color: #cf304a; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; border: 2px solid #ffffff; margin-bottom: 10px; }
    .holiday-box { background-color: #ff9800; color: black; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; }
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

# --- SIDEBAR CONTROLS ---
st.sidebar.title("💎 MASTER AI v18")
nav = st.sidebar.radio("Navigate", ["Live Trading", "AI News & Calendar", "P&L Summary", "Risk Mgmt"])

# Full Asset List Restored
markets = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "GOLD": "GC=F", "CRUDE OIL": "CL=F", "NATURAL GAS": "NG=F",
    "BITCOIN": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD", "RELIANCE": "RELIANCE.NS"
}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]

st.sidebar.markdown("---")
entry_p = st.sidebar.number_input("Entry Price", value=0.0, format="%.2f")
qty = st.sidebar.number_input("Quantity", value=1)
if 'total_pnl' not in st.session_state: st.session_state.total_pnl = 0.0

# --- DATA FETCH ---
@st.cache_data(ttl=5)
def get_dual_data(symbol):
    try:
        d1 = add_indicators(yf.download(symbol, period="2d", interval="1m"))
        d15 = add_indicators(yf.download(symbol, period="5d", interval="15m"))
        return d1, d15
    except: return None, None

d1m, d15m = get_dual_data(symbol)

if d1m is not None and not d1m.empty:
    lp = float(d1m['Close'].iloc[-1])
    vol_curr, vol_avg = d1m['Volume'].iloc[-1], d1m['Vol_Avg'].iloc[-1]
    
    # Trend Analysis
    trend1m = "UP" if d1m['EMA9'].iloc[-1] > d1m['EMA21'].iloc[-1] else "DOWN"
    trend15m = "UP" if d15m['EMA9'].iloc[-1] > d15m['EMA21'].iloc[-1] else "DOWN"

    if nav == "Live Trading":
        st.title(f"🚀 {selected_asset} Pro Terminal")
        
        # Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("LTP", f"{lp:.2f}")
        m2.metric("RSI (1m)", f"{d1m['RSI'].iloc[-1]:.1f}")
        m3.metric("Short Trend", trend1m)
        m4.metric("Major Trend", trend15m)

        # 🐳 Operator Logic
        if vol_curr > (vol_avg * 1.5):
            if d1m['Close'].iloc[-1] > d1m['Open'].iloc[-1]:
                st.markdown('<div class="operator-buy">🐳 OPERATOR ALERT: HEAVY BUYING (UP SIDE)</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="operator-sell">🐳 OPERATOR ALERT: HEAVY SELLING (DOWN SIDE)</div>', unsafe_allow_html=True)

        # 🎯 Master Signal (Dual Confirmation)
        st.markdown("---")
        if trend1m == "UP" and trend15m == "UP":
            st.markdown(f'<div class="master-signal">🔥 MASTER BUY CONFIRMED @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*1.01:.2f} | StopLoss: {d1m['EMA21'].iloc[-1]:.2f}")
        elif trend1m == "DOWN" and trend15m == "DOWN":
            st.markdown(f'<div class="master-signal">🔥 MASTER SELL CONFIRMED @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.info(f"Target: {lp*0.99:.2f} | StopLoss: {d1m['EMA21'].iloc[-1]:.2f}")
        else:
            st.warning("⌛ SIDEWAYS: 1m aur 15m ke trends match nahi ho rahe. Wait karein.")

        # Professional Candle Chart
        chart_df = d1m.tail(60).reset_index()
        t_col = 'Datetime' if 'Datetime' in chart_df.columns else 'Date'
        chart_list = [[row[t_col].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        
        opt = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "xAxis": {"data": [x[0] for x in chart_list]},
            "yAxis": {"scale": True},
            "series": [{"type": "candlestick", "data": [x[1:] for x in chart_list], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]
        }
        st_echarts(options=opt, height="450px")

    elif nav == "AI News & Calendar":
        st.header("📅 Market Calendar & News")
        st.markdown('<div class="holiday-box">Next Market Holiday: Holi (March 14, 2025)</div>', unsafe_allow_html=True)
        st.markdown("---")
        news = yf.Ticker(symbol).news
        if news:
            for n in news[:5]: st.success(f"**{n['title']}**\n\n*Source: {n['publisher']}*")
        else: st.write("No News available.")

    elif nav == "P&L Summary":
        st.title("💰 Day P&L")
        cpnl = (lp - entry_p) * qty if entry_p > 0 else 0
        st.metric("Current Open Trade P&L", f"₹ {cpnl:.2f}", delta=cpnl)
        if st.button("Close & Save Trade"):
            st.session_state.total_pnl += cpnl
            st.balloons()
        st.subheader(f"Total Session Profit: ₹ {st.session_state.total_pnl:.2f}")

# Refresh every 10s
time.sleep(10)
st.rerun()
