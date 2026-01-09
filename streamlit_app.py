import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Top 11 Master Dashboard")

# 2. Market Status & Timer Logic
def get_market_status():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now.weekday() >= 5:
        return "🔴 MARKET CLOSED", "Opens Monday 09:15"
    if now < market_open:
        diff = market_open - now
        return "🟡 PRE-MARKET", f"Opens in: {str(diff).split('.')[0]}"
    elif now > market_close:
        return "🔴 MARKET CLOSED", "Next session: 09:15"
    else:
        diff = market_close - now
        return "🟢 MARKET LIVE", f"Closes in: {str(diff).split('.')[0]}"

# 3. Fetch Indices (Nifty & Sensex)
def get_indices():
    try:
        # Fetching data for Nifty and Sensex
        nifty_data = yf.Ticker("^NSEI").fast_info
        sensex_data = yf.Ticker("^BSESN").fast_info
        
        n_val = round(nifty_data['last_price'], 2)
        s_val = round(sensex_data['last_price'], 2)
        
        # Calculate change to show color
        n_change = round(n_val - nifty_data['previous_close'], 2)
        s_change = round(s_val - sensex_data['previous_close'], 2)
        
        return n_val, n_change, s_val, s_change
    except:
        return "N/A", 0, "N/A", 0

# --- HEADER SECTION (Logo & Metrics) ---
st.title("💹 India Top 11 Master Terminal")

m_status, m_timer = get_market_status()
n_val, n_chg, s_val, s_chg = get_indices()

# Create the top bar
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="📊 NIFTY 50", value=f"{n_val}", delta=f"{n_chg}")
with col2:
    st.metric(label="🏛️ SENSEX", value=f"{s_val}", delta=f"{s_chg}")
with col3:
    st.subheader(m_status)
with col4:
    st.subheader(m_timer)

st.divider()

# 4. Strategy Engine (Rules 1-9 Locked)
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
        
        # --- THE 9 RULES ---
        if 1 <= cp <= 300: score += 1 # Price Cap
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1 # 200 EMA
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1 # SMC Trap
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1 # 9/21 Cross
        if cp > get_num(df['Open']): score += 1 # Green Candle
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1 # Volume
        
        # News Factor
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

# 5. Refresh Logic
@st.fragment(run_every=60)
def show_dashboard():
    results = []
    p_bar = st.progress(0)
    for i, (ticker, name) in enumerate(STOCKS.items()):
        score, mkt_note = calculate_master_signal(ticker)
        try:
            live = round(get_num(yf.Ticker(ticker).fast_info['last_price']), 2)
        except: live = "---"
        
        # Signal Generation
        if score >= 3: act = "🔥 GO LONG"
        elif score <= -1: act = "⚠️ GO SHORT"
        else: act = "⏳ WAIT"
            
        results.append({
            "Stock Name": name, "Price (pts)": live, "Power": "⭐" * score,
            "Score": f"{score}/7", "Action": act, "Market Note": mkt_note
        })
        p_bar.progress((i + 1) / len(STOCKS))

    st.table(pd.DataFrame(results))
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} IST")

show_dashboard()
