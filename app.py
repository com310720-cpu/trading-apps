import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np

st.set_page_config(page_title="MASTER AI v25", layout="wide", initial_sidebar_state="expanded")

# --- GLOBAL STYLE ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 24px !important; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 12px; border-radius: 10px; border: 1px solid #3e4251; }
    .signal-card { background: linear-gradient(135deg, #f0b90b, #ff9900); color: black !important; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid white; margin-bottom: 20px; font-weight: bold; }
    .premium-box { background-color: #1c2127; border-left: 5px solid #f0b90b; padding: 15px; border-radius: 8px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CALCULATIONS ---
def add_indicators(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['Vol_Avg'] = df['Volume'].rolling(window=5).mean()
    return df

# --- SIDEBAR & ASSETS ---
st.sidebar.title("💎 MASTER AI v25")
nav = st.sidebar.radio("Navigate", ["Live Trading & Signal", "Option Chain & Greeks", "Paper Trading", "News"])

# Sabhi Assets Add Kar Diye Gaye Hain
markets = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "BITCOIN": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD",
    "CRUDE OIL": "CL=F", "GOLD": "GC=F", "SILVER": "SI=F", "NATURAL GAS": "NG=F"
}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]

# Timeframe restored
tf_choice = st.sidebar.selectbox("Select Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=0)

# --- DATA ENGINE ---
@st.cache_data(ttl=5)
def fetch_data_v25(symbol, tf):
    try:
        d1 = add_indicators(yf.download(symbol, period="2d", interval=tf))
        d15 = add_indicators(yf.download(symbol, period="5d", interval="15m"))
        return d1, d15
    except: return None, None

d_main, d_long = fetch_data_v25(symbol, tf_choice)

if d_main is not None and not d_main.empty:
    lp = float(d_main['Close'].iloc[-1])
    trend_s = "UP" if d_main['EMA9'].iloc[-1] > d_main['EMA21'].iloc[-1] else "DOWN"
    trend_l = "UP" if d_long['EMA9'].iloc[-1] > d_long['EMA21'].iloc[-1] else "DOWN"
    vol_curr, vol_avg = float(d_main['Volume'].iloc[-1]), float(d_main['Vol_Avg'].iloc[-1])

    # Header & Refresh
    c_head, c_ref = st.columns([5, 1])
    c_head.title(f"🚀 {selected_asset} Terminal")
    if c_ref.button("🔄 REFRESH"): st.rerun()

    if nav == "Live Trading & Signal":
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Price", f"{lp:.2f}")
        m2.metric("RSI", f"{d_main['RSI'].iloc[-1]:.1f}")
        m3.metric("Trend Sync", "MATCHED ✅" if trend_s == trend_l else "WAITING ⌛")
        m4.metric("Vol Spurt", f"{round(vol_curr/vol_avg, 1) if vol_avg > 0 else 1}x")

        # --- OPTION SIGNAL & PREMIUM ENTRY ---
        st.markdown("---")
        diff = 50 if "NIFTY" in selected_asset else 100
        atm_strike = round(lp / diff) * diff

        if trend_s == "UP" and trend_l == "UP":
            st.markdown(f'''<div class="signal-card">
                <h2 style="margin:0;">🔥 SIGNAL: STRONG BUY (CALL)</h2>
                <p style="font-size:18px;">Target: {lp*1.01:.2f} | SL: {lp*0.995:.2f}</p>
            </div>''', unsafe_allow_html=True)
            st.markdown(f'''<div class="premium-box">
                <b>🎯 OPTION ENTRY:</b> Buy <b>{atm_strike} CE</b><br>
                <b>Entry Price:</b> Current Market Premium<br>
                <b>Target:</b> 25% Profit | <b>StopLoss:</b> 15% of Premium
            </div>''', unsafe_allow_html=True)
        elif trend_s == "DOWN" and trend_l == "DOWN":
            st.markdown(f'''<div class="signal-card" style="background: linear-gradient(135deg, #cf304a, #ff4b4b);">
                <h2 style="margin:0; color:white;">🔥 SIGNAL: STRONG SELL (PUT)</h2>
                <p style="font-size:18px; color:white;">Target: {lp*0.99:.2f} | SL: {lp*1.005:.2f}</p>
            </div>''', unsafe_allow_html=True)
            st.markdown(f'''<div class="premium-box">
                <b>🎯 OPTION ENTRY:</b> Buy <b>{atm_strike} PE</b><br>
                <b>Entry Price:</b> Current Market Premium<br>
                <b>Target:</b> 25% Profit | <b>StopLoss:</b> 15% of Premium
            </div>''', unsafe_allow_html=True)
        else:
            st.warning("⌛ SIDEWAYS: Waiting for 1m and 15m trends to align. No trade.")

        # Robust Chart
        chart_df = d_main.tail(50).reset_index()
        t_col = 'Datetime' if 'Datetime' in chart_df.columns else 'Date'
        times = chart_df[t_col].dt.strftime('%H:%M').tolist()
        vals = chart_df[['Open', 'Close', 'Low', 'High']].values.tolist()
        opt = {"xAxis":{"data":times},"yAxis":{"scale":True},"series":[{"type":"candlestick","data":vals,"itemStyle":{"color":"#00c076","color0":"#cf304a"}}],"tooltip":{"trigger":"axis"}}
        st_echarts(options=opt, height="450px")

    elif nav == "Option Chain & Greeks":
        st.subheader(f"📊 {selected_asset} Near-ATM Chain")
        tk = yf.Ticker(symbol)
        try:
            exp = tk.options[0]
            chain = tk.option_chain(exp)
            st.write(f"Expiry: {exp}")
            st.dataframe(chain.calls[['strike', 'lastPrice', 'change', 'volume']].tail(10))
        except: st.error("Option data not available for this asset.")

# Auto Refresh
time.sleep(10)
st.rerun()
