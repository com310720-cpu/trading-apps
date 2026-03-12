import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="Ultimate Terminal v10.0", layout="wide", initial_sidebar_state="expanded")

# --- FORCE WHITE TEXT CSS (Sabhi Errors Ka Pakka Ilaaj) ---
st.markdown("""
    <style>
    /* Sabhi metrics ka text white karein */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {
        color: #FFFFFF !important;
        font-weight: bold !important;
    }
    /* P&L Sidebar Text White */
    .stSidebar, .stSidebar p, .stSidebar span, .stSidebar div {
        color: #FFFFFF !important;
    }
    /* Greeks Box Styling - Full Visibility */
    .greek-card { 
        background-color: #1e2130; 
        color: #FFFFFF !important; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        margin-bottom: 10px; 
        border: 2px solid #3e4251;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .greek-label { color: #f0b90b !important; font-size: 14px; font-weight: bold; margin-bottom: 5px; }
    .greek-value { font-size: 20px; font-weight: bold; color: #FFFFFF !important; }
    
    /* Metrics Background */
    [data-testid="stMetric"] {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3e4251;
    }
    /* Signal Boxes */
    .buy-signal { background-color: #00c076; color: #FFFFFF !important; padding: 20px; border-radius: 10px; text-align: center; font-size: 26px; font-weight: bold; }
    .sell-signal { background-color: #cf304a; color: #FFFFFF !important; padding: 20px; border-radius: 10px; text-align: center; font-size: 26px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE: GREEKS ---
def calculate_greeks(S, K, T, r, sigma, type="call"):
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
    vega = S * norm.pdf(d1) * np.sqrt(T)
    return {"DELTA": delta, "THETA": theta/365, "GAMMA": gamma, "VEGA": vega/100}

# --- SIDEBAR ---
st.sidebar.title("💹 Pro Terminal")
view_mode = st.sidebar.radio("Navigation", ["Live Trading", "Option Greeks", "Risk Management"])

market_map = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "BITCOIN": "BTC-USD", "CRUDE OIL": "CL=F"}
selected_asset = st.sidebar.selectbox("Market Asset", list(market_map.keys()))
symbol = market_map[selected_asset]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Live P&L Monitor")
entry_p = st.sidebar.number_input("Entry Price", value=0.0)
qty_v = st.sidebar.number_input("Quantity", value=1)

# --- DATA ---
@st.cache_data(ttl=5)
def get_final_data(symbol, tf):
    data = yf.download(symbol, period="2d", interval=tf)
    if data.empty: return None
    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
    data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
    data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
    return data

df = get_final_data(symbol, tf)

if df is not None:
    lp = float(df['Close'].iloc[-1])
    
    # Live P&L Tracker (Sidebar)
    if entry_p > 0:
        pnl = (lp - entry_p) * qty_v
        st.sidebar.metric("Live P&L (₹)", f"{pnl:.2f}", delta=f"{((lp-entry_p)/entry_p)*100:.2f}%")

    # --- TOP METRICS ---
    st.title(f"🚀 {selected_asset} Terminal")
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"{lp:.2f}")
    col2.metric("Market Trend", "BULLISH 📈" if df['EMA_9'].iloc[-1] > df['EMA_21'].iloc[-1] else "BEARISH 📉")
    diff = 50 if "NIFTY" in selected_asset else 100
    atm = round(lp / diff) * diff
    col3.metric("ATM Strike", f"{atm}")

    # --- VIEWS ---
    if view_mode == "Live Trading":
        l9, l21 = df['EMA_9'].iloc[-1], df['EMA_21'].iloc[-1]
        p9, p21 = df['EMA_9'].iloc[-2], df['EMA_21'].iloc[-2]

        if (l9 > l21) and (p9 <= p21):
            st.markdown(f'<div class="buy-signal">🚀 ENTRY: BUY CALL (CE) @ {lp:.2f}</div>', unsafe_allow_html=True)
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-signal">📉 ENTRY: BUY PUT (PE) @ {lp:.2f}</div>', unsafe_allow_html=True)

        chart_df = df.tail(60).reset_index()
        c_data = [[row['Date' if 'Date' in row else 'Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        option = {"xAxis": {"data": [d[0] for d in c_data]}, "yAxis": {"scale": True}, "series": [{"type": "candlestick", "data": [d[1:] for d in c_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=option, height="450px")

    elif view_mode == "Option Greeks":
        st.header("📉 Option Greeks (ATM)")
        g_call = calculate_greeks(lp, atm, 0.02, 0.07, 0.18, "call")
        g_put = calculate_greeks(lp, atm, 0.02, 0.07, 0.18, "put")
        
        col_c, col_p = st.columns(2)
        with col_c:
            st.subheader("🟢 Call Greeks")
            for k, v in g_call.items():
                st.markdown(f'<div class="greek-card"><div class="greek-label">{k}</div><div class="greek-value">{v:.4f}</div></div>', unsafe_allow_html=True)
        with col_p:
            st.subheader("🔴 Put Greeks")
            for k, v in g_put.items():
                st.markdown(f'<div class="greek-card"><div class="greek-label">{k}</div><div class="greek-value">{v:.4f}</div></div>', unsafe_allow_html=True)

    elif view_mode == "Risk Management":
        st.header("⚖️ Risk & Quantity Calculator")
        cap = st.number_input("Capital (₹)", value=100000)
        risk = st.slider("Risk per Trade %", 1, 5, 2)
        sl = st.number_input("SL Points (Target - SL)", value=20.0)
        if sl > 0:
            q = (cap * (risk/100)) / sl
            st.success(f"Dhyan se trade karein! Recommended Quantity: **{int(q)}**")

# Auto Refresh 10s
time.sleep(10)
st.rerun()
