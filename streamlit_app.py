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
        n_data = yf.Ticker("^NSEI").fast_info
        s_data = yf.Ticker("^BSESN").fast_info
        nifty, sensex = round(n_data['last_price'], 2), round(s_data['last_price'], 2)
        n_delta = round(nifty - n_data['previous_close'], 2)
        s_delta = round(sensex - s_data['previous_close'], 2)
    except:
        nifty, sensex, n_delta, s_delta = "---", "---", 0, 0
    
    if now.weekday() >= 5: status = "🔴 CLOSED"
    elif now < market_open: status = "🟡 PRE-OPEN"
    elif now > market_close: status = "🔴 CLOSED"
    else: status = "🟢 LIVE"
    
    timer = str(market_close - now).split('.')[0] if status == "🟢 LIVE" else "Next: 09:15"
    return nifty, n_delta, sensex, s_delta, status, timer

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
        
        # Rule 8: News Intelligence
        try:
            if ticker_obj.news:
                headline = ticker_obj.news[0]['title'].upper()
                if any(x in headline for x in ["PROFIT", "ORDER", "WIN", "UPGRADE"]): score += 1
                if any(x in headline for x in ["RBI", "PENALTY", "LOSS", "DOWNGRADE"]): score -= 1
        except: pass

        signal = "🔥 BUY" if score >= 3 else "⚠️ SELL" if score <= -1 else "⏳ WAIT"
        return score, live_price, pct_chg, signal
    except: return 0, 0, 0, "Error"

# --- MODULE 2 SPECIFIC: DYNAMIC SCANNER ---
@st.cache_data(ttl=3600) 
def get_dynamic_top_20():
    # Large pool of active stocks to scan for highest volume today
    scan_pool = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS", "ITC.NS", "HINDALCO.NS", "TATAMOTORS.NS", "ZOMATO.NS", "JIOFIN.NS", "ADANIENT.NS", "PAYTM.NS", "RVNL.NS", "MAZDOCK.NS", "IREDA.NS", "BHEL.NS", "TATAELXSI.NS", "BAJFINANCE.NS", "AXISBANK.NS", "KOTAKBANK.NS", "LT.NS", "ONGC.NS", "SUNPHARMA.NS", "NTPC.NS", "COALINDIA.NS"]
    data = yf.download(scan_pool, period="1d", progress=False)['Volume']
    latest_vol = data.iloc[-1]
    top_20 = latest_vol.sort_values(ascending=False).head(20).index.tolist()
    return top_20

# --- UI SETUP ---
st.title("💹 India Master Terminal")
header_placeholder = st.empty()

# --- MODULE 1: THE CORE 11 (STATIC LIST) ---
st.header("🚀 Module 1: Your Strategy Watchlist (Locked)")
STOCKS_11 = ["IDEA.NS", "YESBANK.NS", "SUZLON.NS", "IDFCFIRSTB.NS", "TATASTEEL.NS", "RPOWER.NS", "PNB.NS", "IRFC.NS", "NHPC.NS", "GAIL.NS", "MRPL.NS"]
table1_placeholder = st.empty()

st.divider()

# --- MODULE 2: DYNAMIC SCANNER (VOLUME BASED) ---
st.header("📊 Module 2: Live Market Scanner (Top 20 Volume Leaders)")
st.info("Dynamic list: Automatically shows today's 20 most active stocks and ranks them by your 9-rule score.")
table2_placeholder = st.empty()

# --- MAIN REFRESH LOOP ---
while True:
    nv, nd, sv, sd, stat, t_rem = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY", f"{nv}", delta=f"{nd}")
        c2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}")
        c3.subheader(stat); c4.subheader(f"⏱️ {t_rem}")

    if 'last_run' not in st.session_state or time.time() - st.session_state.last_run > 60:
        # 1. Update Core 11 (Static scripts, Live data)
        m1_data = []
        for s in STOCKS_11:
            sc, pr, ch, sig = calculate_master_signal(s)
            m1_data.append({"Script": s, "Price": pr, "Chg%": ch, "Power": "⭐"*sc, "Signal": sig})
        
        # 2. Update Dynamic Top 20 (Module 2 Only)
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
