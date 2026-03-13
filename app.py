import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="MASTER AI v23", layout="wide", initial_sidebar_state="expanded")

# --- ADVANCED UI CSS ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 24px !important; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 10px; border-radius: 10px; border: 1px solid #3e4251; }
    section[data-testid="stSidebar"] { background-color: #111418 !important; }
    .signal-card { background: linear-gradient(135deg, #f0b90b, #ff9900); color: black !important; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid white; margin-bottom: 20px; }
    .option-table { width: 100%; border-collapse: collapse; color: white; background-color: #1e2130; border-radius: 10px; overflow: hidden; }
    .option-table th { background-color: #2b3139; padding: 10px; border: 1px solid #3e4251; }
    .option-table td { padding: 8px; text-align: center; border: 1px solid #3e4251; font-size: 14px; }
    .highlight-ce { background-color: rgba(0, 192, 118, 0.2); }
    .highlight-pe { background-color: rgba(207, 48, 74, 0.2); }
    </style>
    """, unsafe_allow_html=True)

# --- TECHNICAL CALCULATIONS ---
def get_indicators(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['Vol_Avg'] = df['Volume'].rolling(window=5).mean()
    return df

# --- OPTION CHAIN ENGINE ---
def fetch_option_chain(symbol, spot_price):
    try:
        tk = yf.Ticker(symbol)
        expirations = tk.options
        if not expirations: return None
        chain = tk.option_chain(expirations[0])
        diff = 50 if "NIFTY" in symbol else 100
        atm = round(spot_price / diff) * diff
        
        calls = chain.calls[(chain.calls['strike'] >= atm - (diff*5)) & (chain.calls['strike'] <= atm + (diff*5))]
        puts = chain.puts[(chain.puts['strike'] >= atm - (diff*5)) & (chain.puts['strike'] <= atm + (diff*5))]
        return calls, puts, atm
    except: return None, None, None

# --- SIDEBAR ---
st.sidebar.title("💎 MASTER AI v23")
nav = st.sidebar.radio("Navigate", ["Live Trading & Signals", "Full Option Chain", "Option Greeks", "P&L Summary"])

markets = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN", "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD"}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
entry_p = st.sidebar.number_input("Entry Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=1)

# --- DATA FETCH ---
@st.cache_data(ttl=5)
def get_all_data(symbol, tf):
    d_m = get_indicators(yf.download(symbol, period="2d", interval=tf))
    d_l = get_indicators(yf.download(symbol, period="5d", interval="15m"))
    return d_m, d_l

data_m, data_l = get_all_data(symbol, tf)

if data_m is not None and not data_m.empty:
    lp = float(data_m['Close'].iloc[-1])
    trend_s = "UP" if data_m['EMA9'].iloc[-1] > data_m['EMA21'].iloc[-1] else "DOWN"
    trend_l = "UP" if data_l['EMA9'].iloc[-1] > data_l['EMA21'].iloc[-1] else "DOWN"
    rsi = data_m['RSI'].iloc[-1]

    # --- TOP METRICS ---
    st.title(f"🚀 {selected_asset} Terminal")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LTP", f"{lp:.2f}")
    c2.metric("RSI", f"{rsi:.1f}")
    c3.metric("Short Trend", trend_s)
    c4.metric("Major Trend", trend_l)

    if nav == "Live Trading & Signals":
        # --- PRECISION ENTRY/EXIT SIGNAL ---
        st.markdown("---")
        calls, puts, atm = fetch_option_chain(symbol, lp)
        
        if trend_s == "UP" and trend_l == "UP":
            premium = calls[calls['strike'] == atm]['lastPrice'].values[0] if calls is not None else 0
            st.markdown(f'''<div class="signal-card">
                <h2 style="margin:0;">🔥 MASTER BUY SIGNAL: CALL (CE)</h2>
                <p style="font-size:20px; margin:5px;">Buy {atm} CE @ ₹{premium:.2f}</p>
                <b style="color:white;">Target: ₹{premium*1.2:.2f} | SL: ₹{premium*0.8:.2f}</b><br>
                <small>Entry Reason: Dual Timeframe Bullish + RSI Strength</small>
            </div>''', unsafe_allow_html=True)
        elif trend_s == "DOWN" and trend_l == "DOWN":
            premium = puts[puts['strike'] == atm]['lastPrice'].values[0] if puts is not None else 0
            st.markdown(f'<div class="signal-card" style="background: linear-gradient(135deg, #cf304a, #ff4b4b);"> \
                <h2 style="margin:0; color:white;">🔥 MASTER SELL SIGNAL: PUT (PE)</h2> \
                <p style="font-size:20px; margin:5px; color:white;">Buy {atm} PE @ ₹{premium:.2f}</p> \
                <b style="color:white;">Target: ₹{premium*1.2:.2f} | SL: ₹{premium*0.8:.2f}</b><br> \
                <small style="color:white;">Entry Reason: Dual Timeframe Bearish + RSI Weakness</small> \
            </div>', unsafe_allow_html=True)
        else:
            st.warning("⌛ SIDEWAYS MARKET: 1m and 15m trends are mismatched. No fresh entry recommended.")

        # --- CHART ---
        chart_df = data_m.tail(50).reset_index()
        t_col = 'Datetime' if 'Datetime' in chart_df.columns else 'Date'
        times = chart_df[t_col].dt.strftime('%H:%M').tolist()
        vals = chart_df[['Open', 'Close', 'Low', 'High']].values.tolist()
        opt = {"tooltip":{"trigger":"axis","axisPointer":{"type":"cross"}},"xAxis":{"data":times},"yAxis":{"scale":True},
               "series":[{"type":"candlestick","data":vals,"itemStyle":{"color":"#00c076","color0":"#cf304a"}}]}
        st_echarts(options=opt, height="400px")

    elif nav == "Full Option Chain":
        st.subheader(f"📊 {selected_asset} Option Chain (Near Expiry)")
        calls, puts, atm = fetch_option_chain(symbol, lp)
        if calls is not None:
            df_chain = pd.merge(calls[['strike', 'lastPrice', 'change', 'openInterest']], 
                                puts[['strike', 'lastPrice', 'change', 'openInterest']], 
                                on='strike', suffixes=('_CE', '_PE'))
            df_chain = df_chain.rename(columns={'strike': 'Strike'})
            st.dataframe(df_chain.style.highlight_max(axis=0, color='#1e2130'), use_container_width=True)
            

# Auto Refresh 10s
time.sleep(10)
st.rerun()
