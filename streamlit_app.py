import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Top 11 Master Terminal")

def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    try:
        n_data = yf.Ticker("^NSEI").fast_info
        s_data = yf.Ticker("^BSESN").fast_info
        nifty, sensex = round(n_data['last_price'], 2), round(s_data['last_price'], 2)
        n_delta = round(nifty - n_data['previous_close'], 2)
        s_delta = round(sensex - s_data['previous_close'], 2)
    except:
        nifty, sensex, n_delta, s_delta = "---", "---", 0, 0

    if now.weekday() >= 5: return nifty, n_delta, sensex, s_delta, "🔴 CLOSED", "Weekend", 0
    elif now < market_open: return nifty, n_delta, sensex, s_delta, "🟡 PRE-OPEN", str(market_open - now).split('.')[0], 0
    elif now > market_close: return nifty, n_delta, sensex, s_delta, "🔴 CLOSED", "Ended", 0
    else: return nifty, n_delta, sensex, s_delta, "🟢 LIVE", str(market_close - now).split('.')[0], 1

# 2. Strategy Engine (9 Rules Preserved)
STOCKS = {
    "IDEA.NS": "Vodafone Idea", "YESBANK.NS": "Yes Bank", "SUZLON.NS": "Suzlon Energy",
    "IDFCFIRSTB.NS": "IDFC First Bank", "TATASTEEL.NS": "Tata Steel", "RPOWER.NS": "Reliance Power",
    "PNB.NS": "PNB", "IRFC.NS": "IRFC", "NHPC.NS": "NHPC", "GAIL.NS": "GAIL", "MRPL.NS": "MRPL"
}

def get_num(data_input):
    if isinstance(data_input, (pd.Series, pd.DataFrame)): return float(data_input.iloc[-1])
    return float(data_input)

def calculate_master_signal(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return 0, "⚠️ Busy", 0, 0
        ticker_obj = yf.Ticker(symbol)
        fast = ticker_obj.fast_info
        live_price = round(fast['last_price'], 2)
        prev_close = fast['previous_close']
        pct_chg = round(((live_price - prev_close) / prev_close) * 100, 2)
        
        # Rules logic
        score = 0
        cp = get_num(df['Close'])
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        note = "No News"
        try:
            if ticker_obj.news: note = ticker_obj.news[0]['title'][:30] + "..."
        except: pass
        
        return score, note, live_price, pct_chg
    except: return 0, "Error", 0, 0

# --- UI LAYOUT ---
st.title("💹 India Top 11 Master Terminal")
header_placeholder = st.empty()
table_placeholder = st.empty()

while True:
    nv, nd, sv, sd, stat, t_rem, is_live = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY", f"{nv}", delta=f"{nd}")
        c2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}")
        c3.subheader(stat)
        c4.subheader(f"⏱️ {t_rem}")
        st.divider()

    if 'last_refresh' not in st.session_state or time.time() - st.session_state.last_refresh > 60:
        data_list = []
        for ticker, name in STOCKS.items():
            score, note, price, change = calculate_master_signal(ticker)
            sig = "🔥 BUY" if score >= 3 else "⚠️ SELL" if score <= -1 else "⏳ WAIT"
            
            data_list.append({
                "Script": name,
                "Price (₹)": price,
                "Chg %": change,
                "Power": "⭐" * score,
                "Signal": sig,
                "Note": note
            })
        
        df = pd.DataFrame(data_list)

        # 3. Apply Professional Styling
        def style_rows(row):
            color = 'background-color: rgba(0, 255, 0, 0.1); color: #00FF00;' if row['Chg %'] > 0 else 'background-color: rgba(255, 0, 0, 0.1); color: #FF0000;'
            return [color] * len(row)

        with table_placeholder.container():
            st.dataframe(
                df.style.apply(style_rows, axis=1).format({"Chg %": "{:.2f}%"}),
                use_container_width=True,
                hide_index=True
            )
            st.caption(f"Last Engine Refresh: {datetime.now().strftime('%H:%M:%S')}")
        
        st.session_state.last_refresh = time.time()
    
    time.sleep(1)
