import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="MASTER AI v22", layout="wide", initial_sidebar_state="expanded")

# --- FORCE VISIBILITY CSS ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 26px !important; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #3e4251; }
    section[data-testid="stSidebar"] { background-color: #111418 !important; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #ffffff !important; font-weight: bold; }
    .master-signal { background: linear-gradient(90deg, #f0b90b, #ff9900); color: #000000 !important; padding: 20px; border-radius: 15px; text-align: center; font-size: 24px; font-weight: bold; border: 3px solid #ffffff; }
    .pnl-box { background-color: #262a33; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff00; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CALCULATIONS ---
def get_indicators(df):
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
st.sidebar.title("💎 MASTER AI v22")
nav = st.sidebar.radio("Navigate", ["Live Trading", "Option Greeks", "AI News", "Risk Mgmt"])

markets = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN", "GOLD": "GC=F", "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD", "ETH": "ETH-USD"}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]
tf_choice = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
entry_p = st.sidebar.number_input("My Entry Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=1)

# --- DATA FETCH ---
@st.cache_data(ttl=5)
def fetch_all_data(symbol, tf):
    try:
        d1 = get_indicators(yf.download(symbol, period="2d", interval=tf))
        d15 = get_indicators(yf.download(symbol, period="5d", interval="15m"))
        return d1, d15
    except: return None, None

d_main, d_long = fetch_all_data(symbol, tf_choice)

if d_main is not None and not d_main.empty:
    lp = float(d_main['Close'].iloc[-1])
    
    # Live P&L Monitor (Sidebar mein hamesha dikhega)
    if entry_p > 0:
        pnl = (lp - entry_p) * qty
        st.sidebar.markdown(f'''<div class="pnl-box">
            <small>LIVE P&L</small><br>
            <span style="font-size:20px; color:{'#00ff00' if pnl>=0 else '#ff4b4b'}">₹ {pnl:.2f}</span>
        </div>''', unsafe_allow_html=True)

    # UI Header
    h_col, r_col = st.columns([5, 1])
    h_col.title(f"🚀 {selected_asset}")
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

        # --- NEW ROBUST CHART ENGINE ---
        try:
            chart_df = d_main.tail(40).reset_index()
            t_col = 'Datetime' if 'Datetime' in chart_df.columns else 'Date'
            
            # Formating data to prevent "null or undefined" error
            times = chart_df[t_col].dt.strftime('%H:%M').tolist()
            values = chart_df[['Open', 'Close', 'Low', 'High']].values.tolist()
            
            option = {
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
                "xAxis": {"data": times},
                "yAxis": {"scale": True},
                "series": [{
                    "type": "candlestick",
                    "data": values,
                    "itemStyle": {"color": "#00c076", "color0": "#cf304a", "borderColor": "#00c076", "borderColor0": "#cf304a"}
                }]
            }
            st_echarts(options=option, height="450px")
        except Exception as e:
            st.error(f"Chart System Rebooting... {e}")

    elif nav == "Option Greeks":
        diff = 50 if "NIFTY" in selected_asset else 100
        atm = round(lp / diff) * diff
        g_c = get_greeks(lp, atm, 0.02, 0.07, 0.20, "call")
        g_p = get_greeks(lp, atm, 0.02, 0.07, 0.20, "put")
        st.subheader(f"ATM Greeks ({atm} Strike)")
        c1, c2 = st.columns(2)
        with c1: st.write("🟢 CALL"); st.json(g_c)
        with c2: st.write("🔴 PUT"); st.json(g_p)

# Refresh 10s
time.sleep(10)
st.rerun()
