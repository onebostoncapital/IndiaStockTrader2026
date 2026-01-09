import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# 1. Page Config
st.set_page_config(layout="wide", page_title="India Top 11 Master Dashboard")
st.title("💹 India Top 11: Auto-Refreshing Rule Book")

# 2. Fixed Universe (Rule 1)
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

# 3. The Core Signal Logic (Rules 2-8)
def calculate_master_signal(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return 0, "⚠️ Link Busy"
        
        score = 0
        cp = get_num(df['Close'])
        
        # Applying your 7 Technical Rules
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        
        # Rule 8: News Filter
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

# 4. The Auto-Refresh Fragment (Updates every 5 minutes)
@st.fragment(run_every=300) 
def show_dashboard():
    st.write(f"🕒 Last Auto-Update: {datetime.now().strftime('%H:%M:%S')}")
    results = []
    
    # Simple Loop for the 11 Stocks
    for ticker, name in STOCKS.items():
        score, mkt_note = calculate_master_signal(ticker)
        try:
            live = round(get_num(yf.Ticker(ticker).fast_info['last_price']), 2)
        except: live = "---"
        
        # Rule 9: Signal Assignment
        if score >= 3: act = "🔥 GO LONG"
        elif score <= -1: act = "⚠️ GO SHORT"
        else: act = "⏳ WAIT"
            
        results.append({
            "Stock Name": name,
            "CMP (₹)": live,
            "Strength": "⭐" * score,
            "Score": f"{score}/7",
            "Signal": act,
            "Market Note": mkt_note
        })

    # Professional Data Display
    df_final = pd.DataFrame(results)
    st.table(df_final)

# 5. Run the dashboard
show_dashboard()

st.sidebar.info("Dashboard auto-refreshes every 5 mins.")
st.sidebar.warning("Note: Free data sources may occasionally delay updates.")
