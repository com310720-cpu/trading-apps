import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time

st.set_page_config(page_title="Ultimate Terminal v6.0", layout="wide", initial_sidebar_state="expanded")

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: white; }
    .stMetric { background-color: #161a1e; border: 1px solid #2b3139; border-radius: 8px; padding: 15px; }
    .buy-signal { background-color: #00c076; color: white; padding: 20px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; }
    .sell-signal { background-color: #cf304a; color: white; padding: 20px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; }
    .goal-reached { background-color: #f0b90b; color: black; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.title("💹 Master Terminal")
view_mode = st.sidebar.radio("Navigate Mode", ["Live Trading", "Strategy Performance", "Live Market News", "Download Trade Log"])

# Fix Variable Names to prevent NameError
market_map = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD", "RELIANCE": "RELIANCE.NS"
}
selected_asset = st.sidebar.selectbox("Market Asset", list(market_map.keys()))
symbol = market_map[selected_asset]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Live Tracker & Goal")
e_price = st.sidebar.number_input("Entry Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=1)
daily_goal = st.sidebar.number_input("Daily Profit Goal (₹)", value=5000.0)

# --- ENGINE ---
@st.cache_data(ttl=5)
def get_data_engine(symbol, tf):
    data = yf.download(symbol, period="5d", interval=tf)
    if data.empty: return None, []
    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
    data['EMA_9'] = data['Close'].ewm(span=9, adjust=False).mean()
    data['EMA_21'] = data['Close'].ewm(span=21, adjust=False).mean()
    
    trades = []
    for i in range(1, len(data)):
        if (data['EMA_9'].iloc[i] > data['EMA_21'].iloc[i]) and (data['EMA_9'].iloc[i-1] <= data['EMA_21'].iloc[i-1]):
            trades.append({"Date": data.index[i], "Type": "BUY CALL", "Price": round(data['Close'].iloc[i], 2)})
        elif (data['EMA_9'].iloc[i] < data['EMA_21'].iloc[i]) and (data['EMA_9'].iloc[i-1] >= data['EMA_21'].iloc[i-1]):
            trades.append({"Date": data.index[i], "Type": "BUY PUT", "Price": round(data['Close'].iloc[i], 2)})
    return data, trades

res_data, trade_log = get_data_engine(symbol, tf)

if res_data is not None:
    lp = res_data['Close'].iloc[-1]
    
    # Header with Manual Refresh
    h1, h2 = st.columns([4, 1])
    h1.title(f"🚀 {selected_asset} Terminal")
    if h2.button("🔄 REFRESH"): st.rerun()

    # P&L Calculation & Goal Alert
    if e_price > 0:
        current_pnl = (lp - e_price) * qty
        st.sidebar.metric("Live P&L", f"{current_pnl:.2f}", delta=current_pnl)
        if current_pnl >= daily_goal:
            st.markdown(f'<div class="goal-reached">🎉 Daily Goal Reached! ₹{current_pnl:.2f} Profit</div>', unsafe_allow_html=True)
            st.balloons()

    # --- VIEWS ---
    if view_mode == "Live Trading":
        l9, l21 = res_data['EMA_9'].iloc[-1], res_data['EMA_21'].iloc[-1]
        p9, p21 = res_data['EMA_9'].iloc[-2], res_data['EMA_21'].iloc[-2]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Live Price", f"{lp:.2f}")
        c2.metric("Trend", "BULLISH" if l9 > l21 else "BEARISH")
        diff = 50 if "NIFTY" in selected_asset else 100
        atm = round(lp / diff) * diff
        c3.metric("ATM Strike", f"{atm}")

        if (l9 > l21) and (p9 <= p21):
            st.markdown(f'<div class="buy-signal">🟢 SIGNAL: BUY CALL (CE) @ {lp:.2f}</div>', unsafe_allow_html=True)
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-signal">🔴 SIGNAL: BUY PUT (PE) @ {lp:.2f}</div>', unsafe_allow_html=True)

        # Candlestick Chart
        chart_df = res_data.tail(50).reset_index()
        chart_data = [[row['Date' if 'Date' in row else 'Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        option = {"xAxis": {"data": [d[0] for d in chart_data]}, "yAxis": {"scale": True}, "tooltip": {"trigger": "axis"}, "series": [{"type": "candlestick", "data": [d[1:] for d in chart_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=option, height="450px")

    elif view_mode == "Strategy Performance":
        st.subheader("📊 Signal Accuracy Log")
        st.table(pd.DataFrame(trade_log).tail(10))

    elif view_mode == "Live Market News":
        st.subheader("📰 Market Updates")
        news = yf.Ticker(symbol).news
        for item in news[:10]:
            st.info(f"**{item['title']}**\n\nSource: {item['publisher']}")

    elif view_mode == "Download Trade Log":
        csv = pd.DataFrame(trade_log).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Report (CSV)", data=csv, file_name="TradeLog.csv")

# Auto-refresh
time.sleep(10)
st.rerun()
