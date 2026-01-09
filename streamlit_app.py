import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Master Terminal")

# --- INDEPENDENT LOGIC: MARKET STATUS ---
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    try:
        ticker_n = yf.Ticker("^NSEI")
        n_data = ticker_n.fast_info
        nifty = round(n_data['last_price'], 2)
        n_delta = round(nifty - n_data['previous_close'], 2)
        
        # Check for Extended Hours (Global/NSE proxy)
        ext_price = ticker_n.info.get('preMarketPrice', nifty)
    except:
        nifty, n_delta, ext_price = "---", 0, 0
    
    if now.weekday() >= 5: status = "🔴 CLOSED"
    elif now < market_open: status = "🟡 PRE-MARKET"
    elif now > market_close: status = "🔵 POST-MARKET"
    else: status = "🟢 LIVE"
    
    timer = str(market_close - now).split('.')[0] if status == "🟢 LIVE" else "Session Active"
    return nifty, n_delta, status, timer

# --- THE MASTER ENGINE (9 RULES LOCKED) ---
def get_num(data_input):
    if isinstance(data_input, (pd.Series, pd.DataFrame)): return float(data_input.iloc[-1])
    return float(data_input)

def calculate_master_signal(symbol):
    try:
        # Fetching data with Extended Hours enabled
        ticker_obj = yf.Ticker(symbol)
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        fast = ticker_obj.fast_info
        
        reg_price = round(fast['last_price'], 2)
        prev_close = fast['previous_close']
        
        # EXTENDED HOURS LOGIC
        # Grabbing Pre/Post Market data from the Ticker Info
        info = ticker_obj.info
        ext_price = info.get('preMarketPrice') or info.get('postMarketPrice') or reg_price
        ext_chg = round(((ext_price - prev_close) / prev_close) * 100, 2)
        
        score = 0
        cp = get_num(df['Close'])
        # --- THE 9 RULES ---
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        # Rule 8: News Intelligence
        try:
            if ticker_obj.news:
                h = ticker_obj.news[0]['title'].upper()
                if any(x in h for x in ["PROFIT", "ORDER", "WIN"]): score += 1
                if any(x in h for x in ["RBI", "LOSS", "PENALTY"]): score -= 1
        except: pass

        signal = "🔥 BUY" if score >= 3 else "⚠️ SELL" if score <= -1 else "⏳ WAIT"
        return score, reg_price, ext_price, ext_chg, signal
    except: return 0, 0, 0, 0, "Error"

# --- DYNAMIC SCANNER LOGIC (MODULE 2) ---
@st.cache_data(ttl=3600)
def get_dynamic_top_20():
    scan_pool = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS", "ITC.NS", "HINDALCO.NS", "TATAMOTORS.NS", "ZOMATO.NS", "JIOFIN.NS", "ADANIENT.NS", "PAYTM.NS", "RVNL.NS", "MAZDOCK.NS", "IREDA.NS", "BHEL.NS", "TATAELXSI.NS"]
    data = yf.download(scan_pool, period="1d", progress=False)['Volume']
    top_20 = data.iloc[-1].sort_values(ascending=False).head(20).index.tolist()
    return top_20

# --- UI SETUP ---
st.title("💹 India Master Terminal (Extended Hours)")
header_placeholder = st.empty()

st.header("🚀 Module 1: Strategy Watchlist (With Ext. Hours)")
STOCKS_11 = ["IDEA.NS", "YESBANK.NS", "SUZLON.NS", "IDFCFIRSTB.NS", "TATASTEEL.NS", "RPOWER.NS", "PNB.NS", "IRFC.NS", "NHPC.NS", "GAIL.NS", "MRPL.NS"]
table1_placeholder = st.empty()

st.divider()

st.header("📊 Module 2: Dynamic Volume Scanner")
table2_placeholder = st.empty()

# --- MAIN REFRESH LOOP ---
while True:
    nv, nd, stat, t_rem = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY", f"{nv}", delta=f"{nd}")
        c2.subheader(stat)
        c3.subheader(f"⏱️ {t_rem}")
        st.divider()

    if 'last_run' not in st.session_state or time.time() - st.session_state.last_run > 60:
        # Module 1
        m1_data = []
        for s in STOCKS_11:
            sc, reg, ext, echg, sig = calculate_master_signal(s)
            m1_data.append({"Script": s, "LTP": reg, "Ext. Price": ext, "Ext. Chg%": echg, "Signal": sig, "Power": "⭐"*sc})
        
        # Module 2
        top_20 = get_dynamic_top_20()
        m2_data = []
        for s in top_20:
            sc, reg, ext, echg, sig = calculate_master_signal(s)
            m2_data.append({"Script": s, "LTP": reg, "Ext. Price": ext, "Ext. Chg%": echg, "Score": sc, "Signal": sig})

        with table1_placeholder.container():
            st.dataframe(pd.DataFrame(m1_data), use_container_width=True, hide_index=True)

        with table2_placeholder.container():
            df2 = pd.DataFrame(m2_data).sort_values(by="Score", ascending=False)
            st.dataframe(df2.style.background_gradient(subset=['Ext. Chg%'], cmap='RdYlGn'), use_container_width=True, hide_index=True)
            
        st.session_state.last_run = time.time()
    
    time.sleep(1)
