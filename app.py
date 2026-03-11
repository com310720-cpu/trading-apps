import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Global Trade Master AI", layout="wide")
st.title("🎯 Pro-Trader Terminal")

# Sidebar
symbol = st.sidebar.text_input("Enter Symbol (e.g. ^NSEI, BTC-USD)", "^NSEI")
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m"])

# Data Fetching with Error Handling
try:
    data = yf.download(symbol, period="2d", interval=tf)
    
    if not data.empty:
        # Fixing column multi-indexing if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        # Technical Calculations
        data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
        data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
        
        # Current Values
        last_price = float(data['Close'].iloc[-1])
        last_ema9 = float(data['EMA_9'].iloc[-1])
        last_ema21 = float(data['EMA_21'].iloc[-1])
        prev_ema9 = float(data['EMA_9'].iloc[-2])
        prev_ema21 = float(data['EMA_21'].iloc[-2])

        # Display Metrics
        c1, c2 = st.columns(2)
        c1.metric("Current Price", f"{last_price:.2f}")
        c2.metric("Trend", "BULLISH 📈" if last_ema9 > last_ema21 else "BEARISH 📉")

        # Signal Logic
        st.subheader("🔔 Real-Time Signal")
        if (last_ema9 > last_ema21) and (prev_ema9 <= prev_ema21):
            st.success(f"🚀 **BUY ENTRY** | Price: {last_price:.2f} | Target: {last_price * 1.005:.2f} | SL: {last_price * 0.995:.2f}")
            st.toast("BUY ALERT!")
        elif (last_ema9 < last_ema21) and (prev_ema9 >= prev_ema21):
            st.error(f"📉 **SELL/EXIT** | Price: {last_price:.2f} | Target: {last_price * 0.995:.2f} | SL: {last_price * 1.005:.2f}")
            st.toast("SELL ALERT!")
        else:
            st.info("⏳ Waiting for a clear crossover signal...")

        # Chart
        st.line_chart(data[['Close', 'EMA_9', 'EMA_21']])
    else:
        st.warning("Data fetch nahi hua. Kya aapne symbol sahi dala hai?")

except Exception as e:
    st.error(f"System Error: {e}")
