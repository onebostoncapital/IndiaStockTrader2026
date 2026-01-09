import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Master Terminal", page_icon="💹")

# --- CLOUD-RESILIENT MARKET INFO ---
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    try:
        # Use a timeout-safe fetch for indices
        nifty_tick = yf.Ticker("^NSEI")
        s_tick = yf.Ticker("^BSESN")
        
        # Accessing .info can be slow on Cloud; fast_info is preferred
        n_data = nifty_tick.fast_info
        s_data = s_tick.fast_info
        
        nifty, nifty_prev = round(n_data['last_price'], 2), n_data['previous_close']
        sensex, sensex_prev = round(s_data['last_price'], 2), s_data['previous_close']
        
        n_delta, s_delta = round(nifty - nifty_prev, 2), round(sensex - sensex_prev, 2)
    except Exception as e:
        # Fallback to prevent crash
        nifty, n_delta, sensex, s_delta = "---", 0, "---", 0

    is_weekend = now.weekday() >= 5
    status = "🔴 CLOSED (WEEKEND)" if is_weekend else ("🟡 PRE-OPEN" if now < market_open_time else ("🔴 CLOSED" if now > market_close_time else "🟢 LIVE"))

    if status == "🟢 LIVE":
        c_label, remaining = "Closing In:", market_close_time - now
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

# --- ROBUST ENGINE (ADAPTED FOR STREAMLIT CLOUD) ---
def get_num(data_input):
    if isinstance(data_input, (pd.Series, pd.DataFrame)): return float(data_input.iloc[-1])
    return float(data_input)

def calculate_master_signal(symbol):
    try:
        # download() is more reliable on cloud than Ticker().history()
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return 0, 0, 0, "No Data", symbol, ""
        
        ticker_obj = yf.Ticker(symbol)
        fast = ticker_obj.fast_info
        
        # Get Info carefully (Slowest part)
        info = ticker_obj.info
        full_name = info.get('longName', symbol.replace('.NS', ''))
        website = info.get('website', '').replace('http://', '').replace('https://', '').split('/')[0]
        logo_url = f"https://logo.clearbit.com/{website}" if website else "https://cdn-icons-png.flaticon.com/512/1691/1691811.png"
        
        live_price, prev_close = round(fast['last_price'], 2), fast['previous_close']
        pct_chg = round(((live_price - prev_close) / prev_close) * 100, 2)
        
        # --- THE 9 RULES ---
        score = 0
        cp = get_num(df['Close'])
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        signal = "🔥 BUY" if score >= 3 else "⚠️ SELL" if score <= -1 else "⏳ WAIT"
        return score, live_price, pct_chg, signal, full_name, logo_url
    except Exception as e:
        return 0, 0, 0, "Error", symbol, ""

# --- UI & REFRESH ---
st.title("💹 India Master Terminal")
header_placeholder = st.empty()
STOCKS_11 = ["IDEA.NS", "YESBANK.NS", "SUZLON.NS", "IDFCFIRSTB.NS", "TATASTEEL.NS", "RPOWER.NS", "PNB.NS", "IRFC.NS", "NHPC.NS", "GAIL.NS", "MRPL.NS"]

st.header("🚀 Module 1: Strategy Watchlist")
table1_placeholder = st.empty()

while True:
    nv, nd, sv, sd, stat, c_label, t_rem = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY 50", f"{nv}", delta=f"{nd}")
        c2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}")
        c3.subheader(stat)
        c4.metric(c_label, t_rem)
        st.divider()

    if 'last_run' not in st.session_state or time.time() - st.session_state.last_run > 60:
        m1_data = []
        for s in STOCKS_11:
            sc, pr, ch, sig, name, logo = calculate_master_signal(s)
            m1_data.append({"Logo": logo, "Company": name, "Price": pr, "Chg%": ch, "Power": "⭐"*sc, "Signal": sig})
        
        with table1_placeholder.container():
            st.dataframe(pd.DataFrame(m1_data), use_container_width=True, hide_index=True, 
                         column_config={"Logo": st.column_config.ImageColumn("Logo")})
        st.session_state.last_run = time.time()
    
    time.sleep(1)
