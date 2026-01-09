import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Master Terminal")

# --- INDEPENDENT LOGIC: MARKET STATUS & COUNTDOWN ---
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    try:
        # Verified Index Symbols
        n_data = yf.Ticker("^NSEI").fast_info
        s_data = yf.Ticker("^BSESN").fast_info
        
        nifty, nifty_prev = round(n_data['last_price'], 2), n_data['previous_close']
        sensex, sensex_prev = round(s_data['last_price'], 2), s_data['previous_close']
        
        n_delta = round(nifty - nifty_prev, 2)
        s_delta = round(sensex - sensex_prev, 2)
    except:
        nifty, n_delta, sensex, s_delta = "---", 0, "---", 0

    is_weekend = now.weekday() >= 5
    if is_weekend:
        status = "🔴 CLOSED (WEEKEND)"
    elif now < market_open_time:
        status = "🟡 PRE-OPEN"
    elif now > market_close_time:
        status = "🔴 CLOSED"
    else:
        status = "🟢 LIVE"

    if status == "🟢 LIVE":
        c_label = "Closing In:"
        remaining = market_close_time - now
    else:
        c_label = "Next Opening:"
        next_open = market_open_time
        if now >= market_close_time or is_weekend:
            days_ahead = 1
            if now.weekday() == 4: days_ahead = 3 
            elif now.weekday() == 5: days_ahead = 2 
            next_open = (now + timedelta(days=days_ahead)).replace(hour=9, minute=15, second=0, microsecond=0)
        remaining = next_open - now

    return nifty, n_delta, sensex, s_delta, status, c_label, str(remaining).split('.')[0]

# --- THE MASTER ENGINE (9 RULES LOCKED) ---
def get_num(data_input):
    if isinstance(data_input, (pd.Series, pd.DataFrame)): return float(data_input.iloc[-1])
    return float(data_input)

def calculate_master_signal(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        ticker_obj = yf.Ticker(symbol)
        fast = ticker_obj.fast_info
        live_price, prev_close = round(fast['last_price'], 2), fast['previous_close']
        pct_chg = round(((live_price - prev_close) / prev_close) * 100, 2)
        
        score = 0
        cp = get_num(df['Close'])
        # --- THE 9 RULES ---
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        # News Analysis
        try:
            if ticker_obj.news:
                h = ticker_obj.news[0]['title'].upper()
                if any(x in h for x in ["PROFIT", "ORDER", "WIN", "UPGRADE"]): score += 1
                if any(x in h for x in ["RBI", "PENALTY", "LOSS", "DOWNGRADE"]): score -= 1
        except: pass

        signal = "🔥 BUY" if score >= 3 else "⚠️ SELL" if score <= -1 else "⏳ WAIT"
        return score, live_price, pct_chg, signal
    except: return 0, 0, 0, "Error"

# --- DYNAMIC SCANNER (VERIFIED SYMBOLS) ---
@st.cache_data(ttl=3600) 
def get_dynamic_top_20():
    # Large pool of accurate NSE Tickers
    scan_pool = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
        "SBIN.NS", "BHARTIARTL.NS", "LICI.NS", "ITC.NS", "HINDALCO.NS", 
        "TATAMOTORS.NS", "ZOMATO.NS", "JIOFIN.NS", "ADANIENT.NS", "PAYTM.NS", 
        "RVNL.NS", "MAZDOCK.NS", "IREDA.NS", "BHEL.NS", "TATAELXSI.NS",
        "WIPRO.NS", "TITAN.NS", "ONGC.NS", "ADANIPORTS.NS", "COALINDIA.NS"
    ]
    try:
        data = yf.download(scan_pool, period="1d", progress=False)['Volume'].iloc[-1]
        return data.sort_values(ascending=False).head(20).index.tolist()
    except:
        return scan_pool[:20]

# --- UI SETUP ---
st.title("💹 India Master Terminal")
header_placeholder = st.empty()

# MODULE 1
st.header("🚀 Module 1: Strategy Watchlist (Fixed)")
# Verified Symbols for your Core 11
STOCKS_11 = ["IDEA.NS", "YESBANK.NS", "SUZLON.NS", "IDFCFIRSTB.NS", "TATASTEEL.NS", "RPOWER.NS", "PNB.NS", "IRFC.NS", "NHPC.NS", "GAIL.NS", "MRPL.NS"]
table1_placeholder = st.empty()

st.divider()

# MODULE 2
st.header("📊 Module 2: Live Volume Scanner (Top 20 Dynamic)")
table2_placeholder = st.empty()

# --- REFRESH LOOP ---
while True:
    nv, nd, sv, sd, stat, c_label, t_rem = get_market_info()
    
    with header_placeholder.container():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 NIFTY 50", f"{nv}", delta=f"{nd}")
        col2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}")
        col3.subheader(stat)
        col4.metric(c_label, t_rem)
        st.divider()

    if 'last_run' not in st.session_state or time.time() - st.session_state.last_run > 60:
        m1_data = []
        for s in STOCKS_11:
            sc, pr, ch, sig = calculate_master_signal(s)
            m1_data.append({"Script": s, "Price": pr, "Chg%": ch, "Power": "⭐"*sc, "Signal": sig})
        
        top_20_list = get_dynamic_top_20()
        m2_data = []
        for s in top_20_list:
            sc, pr, ch, sig = calculate_master_signal(s)
            m2_data.append({"Script": s, "Price": pr, "Chg%": ch, "Score": sc, "Signal": sig})

        with table1_placeholder.container():
            st.dataframe(pd.DataFrame(m1_data), use_container_width=True, hide_index=True)

        with table2_placeholder.container():
            df2 = pd.DataFrame(m2_data).sort_values(by="Score", ascending=False)
            st.dataframe(df2.style.background_gradient(subset=['Chg%'], cmap='RdYlGn'), use_container_width=True, hide_index=True)
            
        st.session_state.last_run = time.time()
    
    time.sleep(1)
