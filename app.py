import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import base64

st.set_page_config(page_title="Ultimate Pro Terminal", layout="wide", initial_sidebar_state="expanded")

# --- 1. SETTINGS & REFRESH ---
REFRESH_TIME = 10 # Har 10 second mein auto-refresh

# --- 2. UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: white; }
    .stMetric { background-color: #161a1e; border: 1px solid #2b3139; border-radius: 8px; padding: 15px; }
    .buy-signal { background-color: #00c076; color: white; padding: 20px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; border: 3px solid white; }
    .sell-signal { background-color: #cf304a; color: white; padding: 20px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; border: 3px solid white; }
    .news-card { background-color: #1c2127; padding: 10px; border-radius: 5px; border-left: 4px solid #f0b90b; margin-bottom: 5px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (All Previous Controls) ---
st.sidebar.title("💹 Ultimate Terminal")
view_mode = st.sidebar.radio("Navigate Mode", ["Live Trading", "Strategy Performance", "Live Market News", "Download Trade Log"])

if st.sidebar.button("🔔 Activate Sound Alerts"):
    st.toast("Sound Alerts Enabled!")

market_list = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "CRUDE OIL": "CL=F", "BITCOIN": "BTC-USD", "RELIANCE": "RELIANCE.NS"
}
selected_asset = st.sidebar.selectbox("Market Asset", list(market_list.keys()))
symbol = market_list[selected_market]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Live P&L Tracker")
e_price = st.sidebar.number_input("Entry Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=1)

# --- 4. ENGINE: DATA & TRADES ---
@st.cache_data(ttl=5)
def get_full_data(symbol, tf):
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

res_data, trade_log = get_full_data(symbol, tf)

if res_data is not None:
    lp = res_data['Close'].iloc[-1]
    
    # --- TOP REFRESH BAR ---
    head_col, btn_col = st.columns([4, 1])
    with head_col: st.title(f"🚀 {selected_asset} Terminal")
    with btn_col: 
        if st.button("🔄 REFRESH NOW"): st.rerun()

    # --- MODE 1: LIVE TRADING ---
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
            st.toast("⚡ BUY SIGNAL!")
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-signal">🔴 SIGNAL: BUY PUT (PE) @ {lp:.2f}</div>', unsafe_allow_html=True)
            st.toast("⚡ SELL SIGNAL!")

        # Chart
        chart_df = res_data.tail(60).reset_index()
        chart_data = [[row['Date' if 'Date' in row else 'Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        option = {"xAxis": {"data": [d[0] for d in chart_data]}, "yAxis": {"scale": True}, "series": [{"type": "candlestick", "data": [d[1:] for d in chart_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=option, height="450px")

    # --- MODE 2: STRATEGY PERFORMANCE (Strategy Tester) ---
    elif view_mode == "Strategy Performance":
        st.subheader("📊 Backtesting Performance (Last 5 Days)")
        df_trades = pd.DataFrame(trade_log)
        st.dataframe(df_trades.tail(20), use_container_width=True)

    # --- MODE 3: LIVE NEWS ---
    elif view_mode == "Live Market News":
        st.subheader("📰 Market News Feed")
        ticker = yf.Ticker(symbol)
        for item in ticker.news[:10]:
            st.markdown(f'<div class="news-card"><b>{item["title"]}</b><br><small>{item["publisher"]}</small></div>', unsafe_allow_html=True)

    # --- MODE 4: DOWNLOAD LOG (PDF/CSV Report) ---
    elif view_mode == "Download Trade Log":
        st.subheader("📂 Export Trade Data")
        csv = pd.DataFrame(trade_log).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Trade Log (CSV)", data=csv, file_name="Trade_Report.csv")

    # Live P&L in Sidebar
    if e_price > 0:
        pnl = (lp - e_price) * qty
        st.sidebar.metric("Live P&L", f"{pnl:.2f}", delta=pnl)

# Auto Refresh Countdown
st.caption(f"Auto-refreshing in {REFRESH_TIME}s...")
time.sleep(REFRESH_TIME)
st.rerun()
