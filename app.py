import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_echarts import st_echarts
import time
import base64

st.set_page_config(page_title="Pro-Terminal AI v4.0", layout="wide", initial_sidebar_state="expanded")

# --- UI STYLING (Groww Dark Theme) ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; color: white; }
    .stMetric { background-color: #161a1e; border: 1px solid #2b3139; border-radius: 8px; padding: 15px; }
    .buy-signal { background-color: #00c076; color: white; padding: 20px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; border-left: 10px solid #ffffff; }
    .sell-signal { background-color: #cf304a; color: white; padding: 20px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; border-left: 10px solid #ffffff; }
    .report-btn { background-color: #f0b90b; color: black; font-weight: bold; padding: 10px; border-radius: 5px; text-decoration: none; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR & MODES ---
st.sidebar.title("💹 Master Terminal")
view_mode = st.sidebar.radio("Navigate", ["Live Trading", "Strategy Performance", "Download Trade Log"])

market_list = {
    "NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "CRUDE OIL": "CL=F", 
    "BITCOIN": "BTC-USD", "RELIANCE": "RELIANCE.NS", "SENSEX": "^BSESN"
}

st.sidebar.markdown("---")
selected_asset = st.sidebar.selectbox("Market Asset", list(market_list.keys()))
symbol = market_list[selected_market]
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

# --- CORE ENGINE: TRADING LOGIC ---
@st.cache_data(ttl=30)
def get_market_data(symbol, tf):
    data = yf.download(symbol, period="5d", interval=tf)
    if data.empty: return None
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

res = get_market_data(symbol, tf)

if res:
    df_data, trade_log = res
    lp = df_data['Close'].iloc[-1]
    
    # --- MODE 1: LIVE TRADING ---
    if view_mode == "Live Trading":
        st.title(f"🚀 {selected_asset} Live")
        l9, l21 = df_data['EMA_9'].iloc[-1], df_data['EMA_21'].iloc[-1]
        p9, p21 = df_data['EMA_9'].iloc[-2], df_data['EMA_21'].iloc[-2]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("LTP", f"{lp:.2f}")
        c2.metric("Trend", "BULLISH" if l9 > l21 else "BEARISH")
        
        diff = 50 if "NIFTY" in selected_asset else 100
        atm = round(lp / diff) * diff
        c3.metric("ATM Premium Strike", f"{atm}")

        if (l9 > l21) and (p9 <= p21):
            st.markdown(f'<div class="buy-signal">🟢 SIGNAL: BUY CALL (CE) @ {lp:.2f}<br>SL: {l21:.2f} | Tgt: {lp*1.01:.2f}</div>', unsafe_allow_html=True)
        elif (l9 < l21) and (p9 >= p21):
            st.markdown(f'<div class="sell-signal">🔴 SIGNAL: BUY PUT (PE) @ {lp:.2f}<br>SL: {l21:.2f} | Tgt: {lp*0.99:.2f}</div>', unsafe_allow_html=True)

        # Candlestick Chart
        chart_df = df_data.tail(50).reset_index()
        chart_data = [[row['Date' if 'Date' in row else 'Datetime'].strftime('%H:%M'), row['Open'], row['Close'], row['Low'], row['High']] for _, row in chart_df.iterrows()]
        option = {"xAxis": {"data": [d[0] for d in chart_data]}, "yAxis": {"scale": True}, "series": [{"type": "candlestick", "data": [d[1:] for d in chart_data], "itemStyle": {"color": "#00c076", "color0": "#cf304a"}}]}
        st_echarts(options=option, height="500px")

    # --- MODE 2: STRATEGY PERFORMANCE ---
    elif view_mode == "Strategy Performance":
        st.title("📊 Accuracy Tester")
        wins = sum(1 for i in range(len(trade_log)-1) if (trade_log[i]['Type'] == "BUY CALL" and trade_log[i+1]['Price'] > trade_log[i]['Price']) or (trade_log[i]['Type'] == "BUY PUT" and trade_log[i+1]['Price'] < trade_log[i]['Price']))
        accuracy = (wins / (len(trade_log)-1)) * 100 if len(trade_log) > 1 else 0
        
        mc1, mc2 = st.columns(2)
        mc1.metric("Accuracy Rate", f"{accuracy:.1f}%")
        mc2.metric("Total Signals (5 Days)", len(trade_log))
        st.dataframe(pd.DataFrame(trade_log).tail(10), use_container_width=True)

    # --- MODE 3: DOWNLOAD REPORT ---
    elif view_mode == "Download Trade Log":
        st.title("📂 Download Trading Report")
        df_log = pd.DataFrame(trade_log)
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Trade Log (CSV/PDF)", data=csv, file_name=f'TradeReport_{selected_asset}.csv', mime='text/csv')
        st.success("Report taiyaar hai! Aap ise Excel ya Google Sheets mein khol kar PDF save kar sakte hain.")

# Auto Refresh
time.sleep(30)
st.rerun()
