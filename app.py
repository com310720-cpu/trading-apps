import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import numpy as np
from scipy.stats import norm

st.set_page_config(page_title="AI PRO TERMINAL v15", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS (Visibility & Professional Theme) ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: white; }
    [data-testid="stMetricValue"] { color: #00ff00 !important; font-size: 28px !important; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4251; }
    
    /* Sidebar Fix */
    section[data-testid="stSidebar"] { background-color: #111418 !important; border-right: 1px solid #333; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #ffffff !important; }

    /* Professional Signal Boxes */
    .signal-box { padding: 25px; border-radius: 12px; text-align: center; border: 2px solid #ffffff; margin-bottom: 15px; }
    .buy-zone { background-color: #00c076; }
    .sell-zone { background-color: #cf304a; }
    .wait-zone { background-color: #2b3139; }
    
    /* Operator Alert Styles */
    .operator-buy { background-color: #155724; color: #d4edda; padding: 12px; border-radius: 8px; border: 2px solid #28a745; margin-bottom: 10px; text-align: center; font-weight: bold; }
    .operator-sell { background-color: #721c24; color: #f8d7da; padding: 12px; border-radius: 8px; border: 2px solid #dc3545; margin-bottom: 10px; text-align: center; font-weight: bold; }
    
    .signal-text { font-size: 32px; font-weight: bold; color: white; }
    .sub-text { font-size: 18px; color: #f0b90b; font-weight: bold; margin-top: 8px; }
    .indicator-label { font-size: 14px; color: #ffffff; background: rgba(0,0,0,0.3); padding: 4px 10px; border-radius: 5px; margin: 2px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# --- TECHNICAL CALCULATIONS ---
def add_pro_indicators(df):
    # EMA
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    # MACD
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    # Volume Spurt Logic
    df['Vol_Avg'] = df['Volume'].rolling(window=5).mean()
    return df

# --- SIDEBAR ---
st.sidebar.title("MASTER TERMINAL v15")
nav = st.sidebar.radio("Navigate", ["Live Trading", "Option Greeks", "Risk Management"])

markets = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "GOLD": "GC=F", "CRUDE OIL": "CL=F", "NATURAL GAS": "NG=F",
    "BITCOIN": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD"
}
selected_asset = st.sidebar.selectbox("Market Asset", list(markets.keys()))
symbol = markets[selected_asset]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
entry_p = st.sidebar.number_input("My Entry Price", value=0.0)
qty = st.sidebar.number_input("Qty", value=1)

# --- DATA ENGINE ---
@st.cache_data(ttl=5)
def fetch_data(symbol, tf):
    df = yf.download(symbol, period="5d", interval=tf)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return add_pro_indicators(df)

data = fetch_data(symbol, tf)

if data is not None:
    # Current Values
    curr = data.iloc[-1]
    lp = float(curr['Close'])
    vol_curr = curr['Volume']
    vol_avg = curr['Vol_Avg']
    ema9, ema21 = curr['EMA9'], curr['EMA21']
    rsi_val, macd_val, macd_sig = curr['RSI'], curr['MACD'], curr['Signal_Line']

    # --- TOP METRICS ---
    st.title(f"📊 {selected_asset} Institutional Tracker")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LTP", f"{lp:.2f}")
    c2.metric("RSI", f"{rsi_val:.1f}")
    c3.metric("Volume Spurt", f"{round(vol_curr/vol_avg, 1)}x" if vol_avg > 0 else "1x")
    diff = 50 if "NIFTY" in selected_asset else 100
    c4.metric("ATM Strike", f"{round(lp/diff)*diff}")

    # --- OPERATOR DIRECTION ALERT ---
    if vol_curr > (vol_avg * 1.5):
        if curr['Close'] > curr['Open']:
            st.markdown(f'<div class="operator-buy">🐳 BIG PLAYER ALERT: LARGE BUYING (UP SIDE) DETECTED</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="operator-sell">🐳 BIG PLAYER ALERT: LARGE SELLING (DOWN SIDE) DETECTED</div>', unsafe_allow_html=True)

    # --- TRIPLE CONFIRMATION SIGNAL ---
    st.markdown("---")
    is_ema_buy = ema9 > ema21
    is_rsi_buy = rsi_val > 50
    is_macd_buy = macd_val > macd_sig
    
    if is_ema_buy and is_rsi_buy and is_macd_buy:
        st.markdown(f'''<div class="signal-box buy-zone">
            <div class="signal-text">🟢 STRONG BUY SIGNAL (CALL)</div>
            <div class="sub-text">Target: {lp + (lp*0.01):.2f} | SL: {ema21:.2f}</div>
            <div class="indicator-label">EMA: Bullish</div><div class="indicator-label">RSI: {rsi_val:.1f}</div><div class="indicator-label">MACD: Positive</div>
        </div>''', unsafe_allow_html=True)
    elif not is_ema_buy and not is_rsi_buy and not is_macd_buy:
        st.markdown(f'''<div class="signal-box sell-zone">
            <div class="signal-text">🔴 STRONG SELL SIGNAL (PUT)</div>
            <div class="sub-text">Target: {lp - (lp*0.01):.2f} | SL: {ema21:.2f}</div>
            <div class="indicator-label">EMA: Bearish</div><div class="indicator-label">RSI: {rsi_val:.1f}</div><div class="indicator-label">MACD: Negative</div>
        </div>''', unsafe_allow_html=True)
    else:
        st.markdown(f'''<div class="signal-box wait-zone">
            <div class="signal-text">⌛ SIDEWAYS / MIXED - NO TRADE</div>
            <div class="sub-text">Operator is quiet or Indicators are conflicting.</div>
        </div>''', unsafe_allow_html=True)

    # --- CHART ---
    chart_df = data.tail(60).reset_index()
    c_data = [[row['Date' if 'Date' in row else 'Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
    option = {"xAxis": {"data": [d[0] for d in c_data]}, "yAxis": {"scale": True}, "tooltip": {"trigger": "axis"},
              "series": [{"type": "candlestick", "data": [d[1:] for d in chart_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
    st_echarts(options=option, height="450px")

# Refresh every 10s
time.sleep(10)
st.rerun()
