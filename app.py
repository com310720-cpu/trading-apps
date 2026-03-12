import streamlit as st
import yfinance as yf
import pandas as pd
import base64

st.set_page_config(page_title="Pro-Trader AI Terminal", layout="wide")

# --- SOUND ALERT LOGIC ---
def play_sound():
    # Simple Beep Sound in Base64
    audio_html = """
        <audio autoplay>
            <source src="https://www.soundjay.com/buttons/beep-07a.mp3" type="audio/mpeg">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# Custom Styling
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    .buy-signal { background-color: #00ff00; color: black; padding: 20px; border-radius: 10px; text-align: center; font-size: 28px; font-weight: bold; animation: pulse 1s infinite; }
    .sell-signal { background-color: #ff0000; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 28px; font-weight: bold; animation: pulse 1s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🕹️ Trading Desk")
if st.sidebar.button("🔔 Click to Activate Sound Alerts"):
    st.toast("Sound Alerts Enabled!")

market_list = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD", "ETH": "ETH-USD"
}
selected_market = st.sidebar.selectbox("Market", list(market_list.keys()))
symbol = market_list[selected_market]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Live P&L Tracker")
entry_price = st.sidebar.number_input("Entry Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=1)

# --- ENGINE ---
try:
    data = yf.download(symbol, period="2d", interval=tf)
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
        data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
        
        lp = float(data['Close'].iloc[-1])
        l9, l21 = float(data['EMA_9'].iloc[-1]), float(data['EMA_21'].iloc[-1])
        p9, p21 = float(data['EMA_9'].iloc[-2]), float(data['EMA_21'].iloc[-2])

        # ATM Strike
        diff = 50 if "NIFTY" in selected_market else 100
        atm = round(lp / diff) * diff

        # P&L Calculation
        if entry_price > 0:
            current_pnl = (lp - entry_price) * qty
            color = "green" if current_pnl >= 0 else "red"
            st.sidebar.markdown(f"### P&L: :{color}[{current_pnl:.2f}]")

        # --- DISPLAY ---
        st.title(f"📊 {selected_market} Live")
        c1, c2, c3 = st.columns(3)
        c1.metric("Live Price", f"{lp:.2f}")
        c2.metric("Trend", "BULLISH" if l9 > l21 else "BEARISH")
        c3.metric("ATM Strike", f"{atm}")

        # --- SIGNAL & SOUND ---
        if (l9 > l21) and (p9 <= p21):
            st.markdown(f'<div class="buy-signal">🚀 BUY CALL (CE) @ {lp:.2f}</div>', unsafe_allow_html=True)
            play_sound()
            st.info(f"🎯 Target: {lp*1.005:.2f} | 🛡️ SL: {l21:.2f}")
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-signal">📉 BUY PUT (PE) @ {lp:.2f}</div>', unsafe_allow_html=True)
            play_sound()
            st.info(f"🎯 Target: {lp*0.995:.2f} | 🛡️ SL: {l21:.2f}")
        else:
            st.info("⌛ Trend Following... No New Entry.")

        st.area_chart(data[['Close', 'EMA_9', 'EMA_21']])

except Exception as e:
    st.error(f"Waiting for Data... {e}")
