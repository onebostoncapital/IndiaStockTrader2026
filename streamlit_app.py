import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Master Terminal")

# --- CORE LOGIC: MARKET STATUS ---
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    try:
        n_data = yf.Ticker("^NSEI").fast_info
        nifty = round(n_data['last_price'], 2)
        n_delta = round(nifty - n_data['previous_close'], 2)
    except:
        nifty, n_delta = "---", 0
    
    if now.weekday() >= 5: status = "🔴 CLOSED"
    elif now < market_open: status = "🟡 PRE-OPEN"
    elif now > market_close: status = "🔴 CLOSED"
    else: status = "🟢 LIVE"
    
    timer = str(market_close - now).split('.')[0] if status == "🟢 LIVE" else "Next: 09:15"
    return nifty, n_delta, status, timer

# --- THE ORIGINAL RULE ENGINE (LOCKED) ---
def get_num(data_input):
    if isinstance(data_input, (pd.Series, pd.DataFrame)): return float(data_input.iloc[-1])
    return float(data_input)

def calculate_master_signal(symbol):
    try:
        # Standard data for the 9 rules
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        ticker_obj = yf.Ticker(symbol)
        fast = ticker_obj.fast_info
        
        # Original Metrics
        live_price = round(fast['last_price'], 2)
        prev_close = fast['previous_close']
        pct_chg = round(((live_price - prev_close) / prev_close) * 100, 2)
        
        # NEW: Pre/Post Market Column Data
        info = ticker_obj.info
        ext_price = info.get('preMarketPrice') or info.get('postMarketPrice') or live_price
        
        score = 0
        cp = get_num(df['Close'])
        # --- THE 9 RULES (ORIGINAL) ---
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        # Rule 8: News (Kept as per original discussion)
        if ticker_obj.news:
            h = ticker_obj.news[0]['title'].upper()
            if any(x in h for x in ["PROFIT", "ORDER", "WIN"]): score += 1
            if any(x in h for x in ["RBI", "LOSS", "PENALTY"]): score -= 1

        signal = "🔥 BUY" if score >= 3 else "⚠️ SELL" if score <= -1 else "⏳ WAIT"
        return score, live_price, pct_chg, ext_price, signal
    except: return 0, 0, 0, 0, "Error"

# --- UI SETUP ---
st.title("💹 India Master Terminal")
header_placeholder = st.empty()

# Create Tabs to keep things clean
tab1, tab2 = st.tabs(["🚀 Main Watchlist", "🌗 Pre/Post Tracking"])

with tab1:
    st.header("Module 1: Original Watchlist (9 Rules)")
    STOCKS_11 = ["IDEA.NS", "YESBANK.NS", "SUZLON.NS", "IDFCFIRSTB.NS", "TATASTEEL.NS", "RPOWER.NS", "PNB.NS", "IRFC.NS", "NHPC.NS", "GAIL.NS", "MRPL.NS"]
    table1_placeholder = st.empty()

with tab2:
    st.header("Module 2: Session Gap Analysis")
    st.info("Tracking Pre-Market and Post-Market price deviations.")
    table2_placeholder = st.empty()

# --- REFRESH LOOP ---
while True:
    nv, nd, stat, t_rem = get_market_info()
    with header_placeholder.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("📊 NIFTY", f"{nv}", delta=f"{nd}")
        c2.subheader(stat)
        c3.subheader(f"⏱️ {t_rem}")

    if 'last_run' not in st.session_state or time.time() - st.session_state.last_run > 60:
        results = []
        for s in STOCKS_11:
            sc, pr, ch, ext, sig = calculate_master_signal(s)
            results.append({
                "Script": s, 
                "Price": pr, 
                "Chg%": ch, 
                "Ext. Price": ext,
                "Gap%": round(((ext - pr)/pr)*100, 2) if pr > 0 else 0,
                "Power": "⭐"*sc, 
                "Signal": sig
            })
        
        df = pd.DataFrame(results)
        
        # Original Version (Tab 1)
        with table1_placeholder.container():
            st.dataframe(df[["Script", "Price", "Chg%", "Power", "Signal"]], use_container_width=True, hide_index=True)
            
        # Pre/Post Tracking (Tab 2)
        with table2_placeholder.container():
            st.dataframe(df[["Script", "Price", "Ext. Price", "Gap%", "Signal"]], use_container_width=True, hide_index=True)
            
        st.session_state.last_run = time.time()
    
    time.sleep(1)
