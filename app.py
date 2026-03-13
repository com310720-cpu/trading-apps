import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="MASTER AI v24", layout="wide", initial_sidebar_state="expanded")

# --- ADVANCED UI CSS ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 24px !important; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 12px; border-radius: 12px; border: 1px solid #3e4251; }
    section[data-testid="stSidebar"] { background-color: #111418 !important; }
    .signal-card { background: linear-gradient(135deg, #f0b90b, #ff9900); color: black !important; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid white; margin-bottom: 20px; }
    .virtual-pnl { background-color: #1c2127; border: 2px dashed #f0b90b; padding: 15px; border-radius: 10px; margin-top: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- TECHNICAL ENGINE ---
def get_indicators(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    return df

# --- SIDEBAR & NAVIGATION ---
st.sidebar.title("💎 MASTER AI v24")
nav = st.sidebar.radio("Navigate", ["Live Trading & Signals", "Paper Trading", "Full Option Chain", "Risk Mgmt"])

markets = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN", "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD"}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]

# Paper Trading State
if 'virtual_balance' not in st.session_state: st.session_state.virtual_balance = 100000.0
if 'trades' not in st.session_state: st.session_state.trades = []

# --- DATA FETCH ---
@st.cache_data(ttl=5)
def get_all_data(symbol):
    d_m = get_indicators(yf.download(symbol, period="2d", interval="1m"))
    d_l = get_indicators(yf.download(symbol, period="5d", interval="15m"))
    return d_m, d_l

data_m, data_l = get_all_data(symbol)

if data_m is not None and not data_m.empty:
    lp = float(data_m['Close'].iloc[-1])
    trend_s = "UP" if data_m['EMA9'].iloc[-1] > data_m['EMA21'].iloc[-1] else "DOWN"
    trend_l = "UP" if data_l['EMA9'].iloc[-1] > data_l['EMA21'].iloc[-1] else "DOWN"

    if nav == "Live Trading & Signals":
        st.title(f"🚀 {selected_asset} Terminal")
        c1, c2, c3 = st.columns(3)
        c1.metric("LTP", f"{lp:.2f}")
        c2.metric("Trend (1m)", trend_s)
        c3.metric("Trend (15m)", trend_l)

        # Signal Logic
        st.markdown("---")
        if trend_s == "UP" and trend_l == "UP":
            st.markdown(f'''<div class="signal-card">
                <h2>🔥 MASTER BUY CONFIRMED</h2>
                <p>Entry: Above {lp:.2f} | Target: {lp*1.01:.2f} | SL: {lp*0.995:.2f}</p>
                <b>Buy CE (Call Option)</b>
            </div>''', unsafe_allow_html=True)
        elif trend_s == "DOWN" and trend_l == "DOWN":
            st.markdown(f'''<div class="signal-card" style="background: linear-gradient(135deg, #cf304a, #ff4b4b);">
                <h2 style="color:white;">🔥 MASTER SELL CONFIRMED</h2>
                <p style="color:white;">Entry: Below {lp:.2f} | Target: {lp*0.99:.2f} | SL: {lp*1.005:.2f}</p>
                <b style="color:white;">Buy PE (Put Option)</b>
            </div>''', unsafe_allow_html=True)
        else:
            st.warning("⌛ SIDEWAYS: Waiting for Trends to Sync...")

        # Chart
        chart_df = data_m.tail(40).reset_index()
        t_col = 'Datetime' if 'Datetime' in chart_df.columns else 'Date'
        times = chart_df[t_col].dt.strftime('%H:%M').tolist()
        vals = chart_df[['Open', 'Close', 'Low', 'High']].values.tolist()
        opt = {"tooltip":{"trigger":"axis"},"xAxis":{"data":times},"yAxis":{"scale":True},
               "series":[{"type":"candlestick","data":vals,"itemStyle":{"color":"#00c076","color0":"#cf304a"}}]}
        st_echarts(options=opt, height="400px")

    elif nav == "Paper Trading":
        st.title("📝 Paper Trading Simulator")
        st.sidebar.subheader(f"Virtual Funds: ₹{st.session_state.virtual_balance:.2f}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("EXECUTE BUY (VIRTUAL)"):
                st.session_state.trades.append({"asset": selected_asset, "price": lp, "type": "BUY", "time": time.ctime()})
                st.success(f"Bought @ {lp}")
        with col2:
            if st.button("RESET PORTFOLIO"):
                st.session_state.virtual_balance = 100000.0
                st.session_state.trades = []
                st.rerun()

        if st.session_state.trades:
            st.table(pd.DataFrame(st.session_state.trades))

# Auto Refresh 10s
time.sleep(10)
st.rerun()
