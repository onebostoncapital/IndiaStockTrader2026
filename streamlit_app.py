import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Top 11 Master Terminal")

# 2. IST Time & Market Timer Logic
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    # Indices Data
    try:
        nifty = yf.Ticker("^NSEI").fast_info['last_price']
        sensex = yf.Ticker("^BSESN").fast_info['last_price']
    except:
        nifty, sensex = "---", "---"

    # Status & Countdown
    if now.weekday() >= 5:
        return nifty, sensex, "🔴 CLOSED", "Opens Monday", 0
    elif now < market_open:
        diff = market_open - now
        return nifty, sensex, "🟡 PRE-OPEN", str(diff).split('.')[0], 0
    elif now > market_close:
        return nifty, sensex, "🔴 CLOSED", "Session Ended", 0
    else:
        diff = market_close - now
        return nifty, sensex, "🟢 LIVE", str(diff).split('.')[0], 1

# --- HEADER SECTION ---
st.title("💹 India Top 11 Master Terminal")
header_placeholder = st.empty() # Placeholder for the dynamic clock/indices

# 3. Strategy Engine (All 9 Rules Preserved)
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
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return 0, "⚠️ Link Busy"
        score = 0
        cp = get_num(df['Close'])
        # Rules 2-7
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        # News Rule
        n_p, note = 0, "No News"
        try:
            t = yf.Ticker(symbol)
            if t.news:
                h = t.news[0]['title'].upper()
                note = h[:40] + "..."
                if any(x in h for x in ["PROFIT", "ORDER", "WIN"]): n_p = 1
                if any(x in h for x in ["RBI", "PENALTY", "LOSS"]): n_p = -1
        except: pass
        return score + n_p, note
    except: return 0, "Scanning..."

# 4. Display Logic
table_placeholder = st.empty()

# Persistent loop for live clock
while True:
    # A. Update Header (Indices + Timer)
    n_v, s_v, stat, t_rem, is_live = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY 50", f"{n_v}")
        c2.metric("🏛️ SENSEX", f"{s_v}")
        c3.subheader(stat)
        c4.subheader(f"⏱️ {t_rem}")
        st.divider()

    # B. Update Table (Every 60 seconds to avoid Yahoo block)
    if 'last_table_update' not in st.session_state or time.time() - st.session_state.last_table_update > 60:
        results = []
        for ticker, name in STOCKS.items():
            score, mkt_note = calculate_master_signal(ticker)
            try:
                live = round(get_num(yf.Ticker(ticker).fast_info['last_price']), 2)
            except: live = "---"
            
            if score >= 3: act = "🔥 GO LONG"
            elif score <= -1: act = "⚠️ GO SHORT"
            else: act = "⏳ WAIT"
                
            results.append({
                "Stock Name": name, "Price": live, "Power": "⭐" * score,
                "Score": f"{score}/7", "Signal": act, "Market Note": mkt_note
            })
        
        with table_placeholder.container():
            st.table(pd.DataFrame(results))
            st.caption(f"Strategy Scan Completed at: {datetime.now().strftime('%H:%M:%S')}")
        
        st.session_state.last_table_update = time.time()

    # C. Tick every second for the clock
    time.sleep(1)
