import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_erecharts import st_echarts # Chart ke liye simple replacement

st.set_page_config(page_title="Pro-Trader AI Terminal", layout="wide")

# Styling for better looks
st.markdown("""
    <style>
    .big-font { font-size:25px !important; font-weight: bold; }
    .signal-buy { color: #00ff00; font-size: 30px; font-weight: bold; border: 2px solid #00ff00; padding: 10px; border-radius: 10px; text-align: center; }
    .signal-sell { color: #ff0000; font-size: 30px; font-weight: bold; border: 2px solid #ff0000; padding: 10px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
st.sidebar.header("🕹️ Control Panel")
symbol = st.sidebar.text_input("Enter Symbol (e.g. ^NSEI, BTC-USD)", "^NSEI")
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"])

# Fetch Data
data = yf.download(symbol, period="max" if tf in ["1d", "1mo"] else "5d", interval=tf)

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Technicals
    data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
    data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
    
    last_price = float(data['Close'].iloc[-1])
    l_ema9 = float(data['EMA_9'].iloc[-1])
    l_ema21 = float(data['EMA_21'].iloc[-1])
    p_ema9 = float(data['EMA_9'].iloc[-2])
    p_ema21 = float(data['EMA_21'].iloc[-2])

    # --- TOP METRICS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Live Price", f"{last_price:.2f}")
    c2.metric("EMA 9", f"{l_ema9:.2f}")
    c3.metric("EMA 21", f"{l_ema21:.2f}")

    # --- DYNAMIC SIGNALS (CALL/PUT) ---
    st.markdown("---")
    st.subheader("📢 Execution Signal")
    
    if (l_ema9 > l_ema21) and (p_ema9 <= p_ema21):
        st.markdown('<div class="signal-buy">🚀 ENTRY: BUY CALL / LONG NOW!</div>', unsafe_allow_html=True)
        st.write(f"**Target:** {last_price * 1.01:.2f} | **Stoploss:** {l_ema21:.2f}")
    elif (l_ema9 < l_ema21) and (p_ema9 >= p_ema21):
        st.markdown('<div class="signal-sell">📉 ENTRY: BUY PUT / SHORT NOW!</div>', unsafe_allow_html=True)
        st.write(f"**Target:** {last_price * 0.99:.2f} | **Stoploss:** {l_ema21:.2f}")
    else:
        trend = "BULLISH (Hold Call)" if l_ema9 > l_ema21 else "BEARISH (Hold Put)"
        st.info(f"⏳ Market is {trend}. Wait for next Crossover for new entry.")

    # --- TRADINGVIEW CANDLE CHART ---
    st.subheader("🕯️ Advanced Candle Chart")
    # TradingView style Chart
    chart_data = data[['Open', 'High', 'Low', 'Close']].tail(100)
    st.area_chart(chart_data['Close']) # Placeholder for visual flow
    st.write("Tip: Use the sidebar to switch from 1m to 1 Month.")

else:
    st.error("Invalid Symbol! Use ^NSEI for Nifty or BTC-USD for Bitcoin.")

