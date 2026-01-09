import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# 1. Page Config
st.set_page_config(layout="wide", page_title="India Top 11 Master Dashboard")

# 2. IST Time & Market Timer Logic
def get_market_status():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Define Market Hours
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    is_weekend = now.weekday() >= 5
    
    if is_weekend:
        # Find next Monday
        days_ahead = 7 - now.weekday()
        next_open = (now + timedelta(days=days_ahead)).replace(hour=9, minute=15, second=0)
        return f"🔴 MARKET CLOSED (Opens Monday 09:15)", "N/A"
    
    if now < market_open:
        diff = market_open - now
        return f"🟡 OPENING IN: {str(diff).split('.')[0]}", "Wait"
    elif now > market_close:
        # Check if today is Friday for next open
        days_to_add = 3 if now.weekday() == 4 else 1
        next_open = (now + timedelta(days=days_to_add)).replace(hour=9, minute=15, second=0)
        return f"🔴 CLOSED (Next Open: {next_open.strftime('%d %b %H:%M')})", "Closed"
    else:
        diff = market_close - now
        return f"🟢 MARKET OPEN", f"CLOSES IN: {str(diff).split('.')[0]}"

# 3. Fetch Indices (Nifty & Sensex)
def get_indices():
    try:
        nifty = yf.Ticker("^NSEI").fast_info['last_price']
        sensex = yf.Ticker("^BSESN").fast_info['last_price']
        return round(nifty, 2), round(sensex, 2)
    except:
        return "N/A", "N/A"

# --- HEADER SECTION ---
st.title("💹 India Top 11: Master Rule Book")

m_status, m_timer = get_market_status()
nifty_val, sensex_val = get_indices()

col1, col2, col3, col4 = st.columns(4)
col1.metric("NIFTY 50", f"₹{nifty_val}")
col2.metric("SENSEX", f"₹{sensex_val}")
col3.subheader(m_status)
col4.subheader(m_timer)
st.divider()

# 4. Your Rule-Locked Stocks Logic
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
        
        # RULES 2-8 LOCKED
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        # News
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

# 5. Dashboard Refresh Fragment
@st.fragment(run_every=60) # Refreshes every 1 minute for the timer
def show_dashboard():
    results = []
    p_bar = st.progress(0)
    for i, (ticker, name) in enumerate(STOCKS.items()):
        score, mkt_note = calculate_master_signal(ticker)
        try:
            live = round(get_num(yf.Ticker(ticker).fast_info['last_price']), 2)
        except: live = "---"
        
        if score >= 3: act = "🔥 GO LONG"
        elif score <= -1: act = "⚠️ GO SHORT"
        else: act = "⏳ WAIT"
            
        results.append({
            "Stock Name": name, "CMP (₹)": live, "Strength": "⭐" * score,
            "Score": f"{score}/7", "Signal": act, "Market Note": mkt_note
        })
        p_bar.progress((i + 1) / len(STOCKS))

    st.table(pd.DataFrame(results))

show_dashboard()
