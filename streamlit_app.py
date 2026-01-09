import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Top 11 Master Terminal")

# 2. Market Status & Timer Logic (Live Countdown)
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    try:
        n_data = yf.Ticker("^NSEI").fast_info
        s_data = yf.Ticker("^BSESN").fast_info
        nifty = round(n_data['last_price'], 2)
        sensex = round(s_data['last_price'], 2)
        n_delta = round(nifty - n_data['previous_close'], 2)
        s_delta = round(sensex - s_data['previous_close'], 2)
    except:
        nifty, sensex, n_delta, s_delta = "---", "---", 0, 0

    if now.weekday() >= 5:
        return nifty, n_delta, sensex, s_delta, "🔴 CLOSED", "Opens Mon", 0
    elif now < market_open:
        diff = market_open - now
        return nifty, n_delta, sensex, s_delta, "🟡 PRE-OPEN", str(diff).split('.')[0], 0
    elif now > market_close:
        return nifty, n_delta, sensex, s_delta, "🔴 CLOSED", "Ended", 0
    else:
        diff = market_close - now
        return nifty, n_delta, sensex, s_delta, "🟢 LIVE", str(diff).split('.')[0], 1

# 3. Strategy Engine (Rules 1-9 Locked)
STOCKS = {
    "IDEA.NS": "Vodafone Idea", "YESBANK.NS": "Yes Bank", "SUZLON.NS": "Suzlon Energy",
    "IDFCFIRSTB.NS": "IDFC First Bank", "TATASTEEL.NS": "Tata Steel", "RPOWER.NS": "Reliance Power",
    "PNB.NS": "PNB", "IRFC.NS": "IRFC", "NHPC.NS": "NHPC", "GAIL.NS": "GAIL", "MRPL.NS": "MRPL"
}

def get_num(data_input):
    try:
        if isinstance(data_input, (pd.Series, pd.DataFrame)): return float(data_input.iloc[-1])
        return float(data_input)
    except: return 0.0

def calculate_master_signal(symbol):
    try:
        # Download data for technicals
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return 0, "⚠️ Busy", 0, 0
        
        score = 0
        cp = get_num(df['Close'])
        
        # Get yesterday's close for % change calculation
        # Note: yf.Ticker.fast_info is more reliable for live CMP
        ticker_obj = yf.Ticker(symbol)
        fast = ticker_obj.fast_info
        live_price = round(fast['last_price'], 2)
        prev_close = fast['previous_close']
        pct_chg = round(((live_price - prev_close) / prev_close) * 100, 2)
        
        # RULES 2-7
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        # Rule 8: News
        n_p, note = 0, "No News"
        try:
            if ticker_obj.news:
                h = ticker_obj.news[0]['title'].upper()
                note = h[:30] + "..."
                if any(x in h for x in ["PROFIT", "ORDER", "WIN"]): n_p = 1
                if any(x in h for x in ["RBI", "PENALTY", "LOSS"]): n_p = -1
        except: pass
        
        return (score + n_p), note, live_price, pct_chg
    except:
        return 0, "Scanning...", 0, 0

# --- UI LAYOUT ---
st.title("💹 India Top 11 Master Terminal")
header_placeholder = st.empty()
table_placeholder = st.empty()

# 4. Main Real-Time Loop
while True:
    # A. Dynamic Header Update
    nv, nd, sv, sd, stat, t_rem, is_live = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY 50", f"{nv}", delta=f"{nd}")
        c2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}")
        c3.subheader(stat)
        c4.subheader(f"⏱️ {t_rem}")
        st.divider()

    # B. Dynamic Table Update (Runs every 60 seconds)
    if 'last_refresh' not in st.session_state or time.time() - st.session_state.last_refresh > 60:
        results = []
        for ticker, name in STOCKS.items():
            score, note, price, change = calculate_master_signal(ticker)
            
            # Rule 9: Signal
            if score >= 3: act = "🔥 BUY"
            elif score <= -1: act = "⚠️ SELL"
            else: act = "⏳ WAIT"
            
            # Format the change string
            chg_str = f"{'+' if change > 0 else ''}{change}%"
            
            results.append({
                "Script": name,
                "Price (₹)": price,
                "Day Chg %": chg_str,
                "Power": "⭐" * score,
                "Signal": act,
                "Market Note": note
            })
            
        with table_placeholder.container():
            st.table(pd.DataFrame(results))
            st.caption(f"Last Engine Refresh: {datetime.now().strftime('%H:%M:%S')}")
        
        st.session_state.last_refresh = time.time()

    time.sleep(1) # Ticks the clock every second
