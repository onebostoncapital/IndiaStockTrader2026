import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Top 11 Master Terminal")

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

# --- MODULE 1: THE MASTER RULE ENGINE (LOCKED) ---
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
        ticker_obj = yf.Ticker(symbol)
        fast = ticker_obj.fast_info
        live_price, prev_close = round(fast['last_price'], 2), fast['previous_close']
        pct_chg = round(((live_price - prev_close) / prev_close) * 100, 2)
        
        score = 0
        cp = get_num(df['Close'])
        # RULES 1-9 (LOCKED)
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        return score, live_price, pct_chg
    except: return 0, 0, 0

# --- MODULE 2: MARKET PULSE (INDEPENDENT DATA) ---
@st.cache_data(ttl=300) 
def fetch_market_movers():
    # Top 20 High-Activity Scripts
    movers_list = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "LICI.NS", "ITC.NS", "HINDALCO.NS", "TATAMOTORS.NS", "ZOMATO.NS", "JIOFIN.NS", "ADANIENT.NS", "PAYTM.NS", "RVNL.NS", "MAZDOCK.NS", "IREDA.NS", "BHEL.NS", "TATAELXSI.NS"]
    data = yf.download(movers_list, period="1d", progress=False)
    
    # Get current price and yesterday's close for % calculation
    close = data['Close'].iloc[-1]
    # For a 1-day download, we use the first row of the 'Open' column as a proxy for baseline if 1d data is thin
    baseline = data['Open'].iloc[0] 
    vol = data['Volume'].iloc[-1]
    pct = ((close - baseline) / baseline) * 100
    
    df = pd.DataFrame({
        'Price': close.round(2),
        'Chg%': pct.round(2),
        'Volume': vol
    })
    return df

# --- UI DISPLAY ---
st.title("💹 India Top 11 Master Terminal")
header_placeholder = st.empty()

st.header("🚀 Module 1: Strategy Signals (Rule-Locked)")
table_placeholder = st.empty()

st.divider()

st.header("📊 Module 2: Market Pulse (Top Movers with Prices)")
movers_placeholder = st.empty()

# --- MAIN REFRESH LOOP ---
while True:
    nv, nd, sv, sd, stat, t_rem = get_market_info()
    with header_placeholder.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 NIFTY", f"{nv}", delta=f"{nd}")
        c2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}")
        c3.subheader(stat)
        c4.subheader(f"⏱️ {t_rem}")

    # Update Module 1 (Strategy)
    if 'last_ref' not in st.session_state or time.time() - st.session_state.last_ref > 60:
        res = []
        for tick, name in STOCKS.items():
            sc, pr, ch = calculate_master_signal(tick)
            sig = "🔥 BUY" if sc >= 3 else "⚠️ SELL" if sc <= -1 else "⏳ WAIT"
            res.append({"Script": name, "Price": pr, "Chg %": ch, "Power": "⭐"*sc, "Signal": sig})
        
        df1 = pd.DataFrame(res)
        with table_placeholder.container():
            st.dataframe(df1.style.format({"Chg %": "{:.2f}%"}), use_container_width=True, hide_index=True)
        st.session_state.last_ref = time.time()

    # Update Module 2 (Movers with Prices)
    movers = fetch_market_movers()
    with movers_placeholder.container():
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.subheader("🔥 Top 5 Volume")
            top_vol = movers.sort_values(by='Volume', ascending=False).head(5)[['Price', 'Chg%']]
            st.dataframe(top_vol, use_container_width=True)
            
        with m2:
            st.subheader("📈 Top 5 Gainers")
            top_gain = movers.sort_values(by='Chg%', ascending=False).head(5)[['Price', 'Chg%']]
            st.dataframe(top_gain.style.background_gradient(subset=['Chg%'], cmap='Greens'), use_container_width=True)
            
        with m3:
            st.subheader("📉 Top 5 Losers")
            top_loss = movers.sort_values(by='Chg%', ascending=True).head(5)[['Price', 'Chg%']]
            st.dataframe(top_loss.style.background_gradient(subset=['Chg%'], cmap='Reds'), use_container_width=True)
    
    time.sleep(1)
