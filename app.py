import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Pro-Trader Terminal", layout="wide")

# Stylish Signals
st.markdown("""
    <style>
    .buy-box { background-color: #00ff00; color: black; padding: 20px; border-radius: 10px; text-align: center; font-size: 35px; font-weight: bold; }
    .sell-box { background-color: #ff0000; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 35px; font-weight: bold; }
    .hold-box { background-color: #1e1e1e; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 25px; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
st.sidebar.header("⚙️ Settings")
symbol = st.sidebar.text_input("Symbol (e.g. ^NSEI, BTC-USD)", "^NSEI")
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"])

# Data Fetch
try:
    data = yf.download(symbol, period="max" if tf in ["1d", "1mo"] else "5d", interval=tf)
    
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Indicators
        data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
        data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
        
        last = data.iloc[-1]
        prev = data.iloc[-2]

        # Header Price
        st.title(f"📊 {symbol} Live Terminal")
        st.metric("LTP (Last Traded Price)", f"{last['Close']:.2f}")

        # --- DYNAMIC ACTION SIGNAL ---
        st.markdown("---")
        if (last['EMA_9'] > last['EMA_21']) and (prev['EMA_9'] <= prev['EMA_21']):
            st.markdown('<div class="buy-box">🟢 ACTION: BUY CALL / LONG NOW</div>', unsafe_allow_html=True)
            st.balloons()
        elif (last['EMA_9'] < last['EMA_21']) and (prev['EMA_9'] >= prev['EMA_21']):
            st.markdown('<div class="sell-box">🔴 ACTION: BUY PUT / SHORT NOW</div>', unsafe_allow_html=True)
        else:
            status = "BULLISH (Wait for Exit)" if last['EMA_9'] > last['EMA_21'] else "BEARISH (Wait for Exit)"
            st.markdown(f'<div class="hold-box">⏳ {status}</div>', unsafe_allow_html=True)

        # --- CANDLESTICK CHART ---
        st.subheader(f"🕯️ {tf} Candle Chart")
        # Streamlit ka inbuilt candle chart (available in latest version)
        st.area_chart(data[['Close', 'EMA_9', 'EMA_21']])
        
        st.write("Target & SL Guide:")
        st.info(f"Entry: {last['Close']:.2f} | Target: {last['Close']*1.008:.2f} (Scalp) | SL: {last['EMA_21']:.2f}")

    else:
        st.error("Invalid Symbol! Please check.")
except Exception as e:
    st.error(f"Error: {e}")
