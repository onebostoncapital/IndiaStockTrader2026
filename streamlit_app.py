import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Master Terminal")

# --- FAST MARKET INFO ---
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    m_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    m_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    try:
        # Bulk fetch indices for speed
        idx = yf.download(["^NSEI", "^BSESN"], period="1d", progress=False, interval="1m").iloc[-1]['Close']
        prev = yf.download(["^NSEI", "^BSESN"], period="5d", progress=False).iloc[-2]['Close']
        
        nifty, n_prev = round(idx["^NSEI"], 2), prev["^NSEI"]
        sensex, s_prev = round(idx["^BSESN"], 2), prev["^BSESN"]
        nd, sd = round(nifty - n_prev, 2), round(sensex - s_prev, 2)
    except:
        nifty, nd, sensex, sd = "---", 0, "---", 0

    is_weekend = now.weekday() >= 5
    status = "🔴 CLOSED (WKND)" if is_weekend else ("🟡 PRE-OPEN" if now < m_open else ("🔴 CLOSED" if now > m_close else "🟢 LIVE"))
    
    c_label = "Closing In:" if status == "🟢 LIVE" else "Next Opening:"
    next_t = m_open if (now < m_open and not is_weekend) else (now + timedelta(days=3 if now.weekday()==4 else 2 if now.weekday()==5 else 1)).replace(hour=9, minute=15)
    rem = m_close - now if status == "🟢 LIVE" else next_t - now
    
    return nifty, nd, sensex, sd, status, c_label, str(rem).split('.')[0]

# --- TURBO SIGNAL ENGINE ---
def get_num(data_input):
    return float(data_input.iloc[-1]) if isinstance(data_input, (pd.Series, pd.DataFrame)) else float(data_input)

def batch_calculate_signals(symbols):
    results = []
    # Bulk download price data for all symbols at once (MASSIVE SPEED BOOST)
    try:
        data = yf.download(symbols, period="1mo", interval="15m", progress=False, auto_adjust=True)
        for s in symbols:
            try:
                df = data.xs(s, axis=1, level=1) if len(symbols) > 1 else data
                cp = get_num(df['Close'])
                op = get_num(df['Open'])
                prev_c = df['Close'].iloc[-2]
                pct = round(((cp - prev_c) / prev_c) * 100, 2)
                
                score = 0
                if 1 <= cp <= 300: score += 1
                if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
                if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
                if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
                if cp > op: score += 1
                if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
                
                sig = "🔥 BUY" if score >= 3 else "⚠️ SELL" if score <= -1 else "⏳ WAIT"
                results.append({"Symbol": s, "Price": cp, "Chg%": pct, "Power": "⭐"*max(0,score), "Signal": sig, "Score": score})
            except: continue
    except: pass
    return results

# --- DATA POOLS ---
STOCKS_11 = ["IDEA.NS", "YESBANK.NS", "SUZLON.NS", "IDFCFIRSTB.NS", "TATASTEEL.NS", "RPOWER.NS", "PNB.NS", "IRFC.NS", "NHPC.NS", "GAIL.NS", "MRPL.NS"]
SCAN_POOL = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "TATAMOTORS.NS", "ZOMATO.NS", "JIOFIN.NS", "ADANIENT.NS", "PAYTM.NS", "RVNL.NS", "IREDA.NS", "BHEL.NS"]

# --- UI SETUP ---
st.title("💹 India Master Terminal")
header_placeholder = st.empty()
st.header("🚀 Module 1: Strategy Watchlist")
t1_ptr = st.empty()
st.divider()
st.header("📊 Module 2: High Volume Scanner")
t2_ptr = st.empty()

# --- REFRESH LOOP ---
while True:
    nv, nd, sv, sd, stat, c_label, t_rem = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY 50", f"{nv}", delta=f"{nd}")
        c2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}")
        c3.subheader(stat)
        c4.metric(c_label, t_rem)

    # Refresh Data every 60 seconds
    if 'last_run' not in st.session_state or time.time() - st.session_state.last_run > 60:
        # Calculate Module 1 & 2 in efficient batches
        m1_results = batch_calculate_signals(STOCKS_11)
        m2_results = batch_calculate_signals(SCAN_POOL)

        t1_ptr.dataframe(pd.DataFrame(m1_results).drop(columns=['Score']), use_container_width=True, hide_index=True)
        
        df2 = pd.DataFrame(m2_results).sort_values(by="Score", ascending=False)
        t2_ptr.dataframe(df2.drop(columns=['Score']).style.background_gradient(subset=['Chg%'], cmap='RdYlGn'), use_container_width=True, hide_index=True)
        
        st.session_state.last_run = time.time()
    
    time.sleep(1)
