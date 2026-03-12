import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts

st.set_page_config(page_title="Global Trade Master Terminal", layout="wide")

# --- CUSTOM CSS (Fixing Black Boxes and styling) ---
st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    /* Clear and professional metrics cards */
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 30px !important; }
    [data-testid="stMetricLabel"] { color: #bbbbbb !important; font-size: 16px !important; }
    .stMetric { background-color: #1e2130; padding: 20px; border-radius: 12px; border: 1px solid #3e4251; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    /* Signals Styling */
    .buy-signal { background-color: #00ff00; color: black; padding: 20px; border-radius: 10px; text-align: center; font-size: 28px; font-weight: bold; border: 3px solid white; animation: pulse 1s infinite; }
    .sell-signal { background-color: #ff0000; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 28px; font-weight: bold; border: 3px solid white; animation: pulse 1s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🕹️ Trading Desk")
if st.sidebar.button("🔔 Activate Sound Alerts (Beep)"):
    st.toast("Sound Alerts Enabled!")

market_list = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "CRUDE OIL": "CL=F", "NATURAL GAS": "NG=F", "BITCOIN": "BTC-USD", "ETH": "ETH-USD"
}
selected_market = st.sidebar.selectbox("Market Select Karein", list(market_list.keys()))
symbol = market_list[selected_market]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d", "1wk", "1mo"])

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Live P&L Tracker")
entry_price = st.sidebar.number_input("Apni Entry Price Dalein", value=0.0)
quantity = st.sidebar.number_input("Quantity (Lots/Units)", value=1)

# --- GLOBAL MARKET MONITOR (New Added) ---
st.sidebar.markdown("---")
st.sidebar.subheader("🌍 Global Markets")
try:
    with st.sidebar.spinner('Loading Global Data...'):
        global_indices = yf.download(["^DJI", "^IXIC", "^FTSE", "^GDAXI"], period="2d", interval="1d")['Close']
        if not global_indices.empty:
            dji_change = ((global_indices["^DJI"].iloc[-1] - global_indices["^DJI"].iloc[-2]) / global_indices["^DJI"].iloc[-2]) * 100
            nas_change = ((global_indices["^IXIC"].iloc[-1] - global_indices["^IXIC"].iloc[-2]) / global_indices["^IXIC"].iloc[-2]) * 100
            
            # Simplified Global Display
            g_col1, g_col2 = st.sidebar.columns(2)
            g_col1.metric("Dow Jones", f"{dji_change:.2f}%")
            g_col2.metric("Nasdaq", f"{nas_change:.2f}%")
except Exception as e:
    st.sidebar.write("Global data unavailable.")

# --- ENGINE ---
def play_beep():
    # Base64 Beep sound for notifications
    audio_html = """
        <audio autoplay>
            <source src="https://www.soundjay.com/buttons/beep-07a.mp3" type="audio/mpeg">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

try:
    # Need period='max' for 1mo timeframe to work
    fetch_period = "max" if tf in ["1wk", "1mo"] else "5d"
    data = yf.download(symbol, period=fetch_period, interval=tf)
    
    if not data.empty:
        # Flatten MultiIndex columns if necessary
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Technical Indicators
        data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
        data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
        
        last_data = data.iloc[-1]
        prev_data = data.iloc[-2]
        
        lp = float(last_data['Close'])
        l9, l21 = float(last_data['EMA_9']), float(last_data['EMA_21'])
        p9, p21 = float(prev_data['EMA_9']), float(prev_data['EMA_21'])

        # ATM Strike
        strike_diff = 50 if "NIFTY" in selected_market else 100
        atm_strike = round(lp / strike_diff) * strike_diff

        # --- LIVE P&L DISPLAY ---
        if entry_price > 0:
            current_pnl = (lp - entry_price) * quantity
            pnl_color = "🟢 Profit" if current_pnl >= 0 else "🔴 Loss"
            st.sidebar.markdown(f"**P&L Status:** ### **{pnl_color}: {current_pnl:.2f}**")

        # --- MAIN DASHBOARD: Clear white columns ---
        st.title(f"📊 {selected_market} Live Terminal")
        col1, col2, col3 = st.columns(3)
        col1.metric("Live Price", f"{lp:.2f}", help="Current Last Price")
        col2.metric("Trend", "BULLISH 📈" if l9 > l21 else "BEARISH 📉", help="Based on EMA 9/21 Crossover")
        col3.metric("ATM Option Strike", f"{atm_strike}", help="At-The-Money for Nifty/BankNifty")

        st.markdown("---")

        # --- SIGNALS & STRATEGY ---
        st.subheader("🔔 Trading Signal")
        if (l9 > l21) and (p9 <= p21):
            st.markdown(f'<div class="buy-signal">🚀 BUY CALL (CE) NOW @ {lp:.2f}</div>', unsafe_allow_html=True)
            play_beep()
            st.info(f"👉 **Premium:** {atm_strike} CE (ATM) | **Target:** {lp*1.005:.2f} | **SL:** {l21:.2f}")
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-signal">📉 BUY PUT (PE) NOW @ {lp:.2f}</div>', unsafe_allow_html=True)
            play_beep()
            st.info(f"👉 **Premium:** {atm_strike} PE (ATM) | **Target:** {lp*0.995:.2f} | **SL:** {l21:.2f}")
        else:
            trend_desc = "Hold Call" if l9 > l21 else "Hold Put"
            st.info(f"⏳ Crossover is holding {trend_desc.upper()}. Wait for next confirmation.")

        # --- PROFESSIONAL CANDLESTICK & VOLUME CHART ---
        st.subheader(f"🕯️ Advanced {tf} Chart (TradingView Look)")
        
        # Prepare data for ECharts candlestick format [time, open, close, low, high, volume]
        chart_df = data.tail(100).reset_index()
        chart_data = []
        for index, row in chart_df.iterrows():
            time_str = row['Datetime' if 'Datetime' in row else 'Date'].strftime('%Y-%m-%d %H:%M')
            chart_data.append([time_str, float(row['Open']), float(row['Close']), float(row['Low']), float(row['High']), float(row['Volume'])])

        # ECharts Option configuration for candlestick + volume
        option = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "grid": [{"left": "3%", "right": "3%", "height": "60%"}, {"left": "3%", "right": "3%", "top": "70%", "height": "20%"}],
            "xAxis": [{"type": "category", "data": [d[0] for d in chart_data], "scale": True, "boundaryGap": False}, {"type": "category", "gridIndex": 1, "data": [d[0] for d in chart_data], "scale": True, "boundaryGap": False, "axisLabel": {"show": False}}],
            "yAxis": [{"scale": True, "splitArea": {"show": True}}, {"scale": True, "gridIndex": 1, "splitNumber": 2, "axisLabel": {"show": False}, "axisLine": {"show": False}, "axisTick": {"show": False}, "splitLine": {"show": False}}],
            "series": [
                {"name": "Candle", "type": "candlestick", "data": [d[1:5] for d in chart_data], "itemStyle": {"color": "#ef232a", "color0": "#14b143", "borderColor": "#ef232a", "borderColor0": "#14b143"}},
                {"name": "Volume", "type": "bar", "xAxisIndex": 1, "yAxisIndex": 1, "data": [d[5] for d in chart_data], "itemStyle": {"color": "#7fbe9e"}}
            ]
        }
        
        # Display the chart
        st_echarts(options=option, height="500px")

    else:
        st.warning("Data fetch nahi ho raha hai. Please symbol check karein.")
except Exception as e:
    st.error(f"Error fetching data: {e}")
