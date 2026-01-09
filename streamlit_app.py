import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Top 11 Hybrid Tracker")
st.title("💹 India Top 11: Multi-Source Dashboard")

# 2. Your Stock List (NSE Tickers)
STOCKS = {
    "IDEA.NS": "Vodafone Idea", "YESBANK.NS": "Yes Bank", "SUZLON.NS": "Suzlon Energy",
    "IDFCFIRSTB.NS": "IDFC First Bank", "TATASTEEL.NS": "Tata Steel", "RPOWER.NS": "Reliance Power",
    "PNB.NS": "PNB", "IRFC.NS": "IRFC", "NHPC.NS": "NHPC", "GAIL.NS": "GAIL", "MRPL.NS": "MRPL"
}

# 3. Helper function to ensure we have a single number
def clean_val(val):
    if isinstance(val, pd.Series):
        return float(val.iloc[-1])
    return float(val)

# 4. Resilient Data Fetcher (Sources from Yahoo and Fallback)
def fetch_stock_data(symbol):
    """Tries to get data with retries if the first attempt fails."""
    for attempt in range(3): # Try up to 3 times
        try:
            data = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
            if not data.empty:
                return data
        except:
            time.sleep(1) # Wait 1 second before retrying
    return pd.DataFrame()

# 5. The News & Scoring Engine
def calculate_score(symbol):
    data = fetch_stock_data(symbol)
    if data.empty: return 0, "⚠️ Data Source Busy"
    
    score = 0
    try:
        curr_price = clean_val(data['Close'])
        curr_open = clean_val(data['Open'])
        
        # Rule 1: Price Cap
        if curr_price <= 300: score += 1
        # Rule 2: Trend (200 EMA)
        ema200 = clean_val(data['Close'].ewm(span=200).mean())
        if curr_price > ema200: score += 1
        # Rule 3: 9/21 EMA Cross
        ema9 = clean_val(data['Close'].ewm(span=9).mean())
        ema21 = clean_val(data['Close'].ewm(span=21).mean())
        if ema9 > ema21: score += 1
        # Rule 4: Volume Spike
        if clean_val(data['Volume']) > data['Volume'].tail(10).mean(): score += 1
        # Rule 5: Candle Color
        if curr_price > curr_open: score += 1
        
        # Get News
        ticker_obj = yf.Ticker(symbol)
        news = ticker_obj.news
        headline = "No News Found"
        if news:
            headline = news[0]['title'].upper()
            if any(w in headline for w in ["PROFIT", "ORDER", "CONTRACT"]): score += 1
            if any(w in headline for w in ["PENALTY", "LOSS", "RBI"]): score -= 1
            
        return score, headline[:50] + "..."
    except:
        return 0, "Error Calculating"

# 6. Build UI
st.sidebar.markdown("### 🛠️ System Control")
if st.sidebar.button('🔄 Force Refresh All Data'):
    st.rerun()

results = []
# Create a progress bar for better user experience
progress_bar = st.progress(0)
for i, (ticker, name) in enumerate(STOCKS.items()):
    score, news = calculate_score(ticker)
    
    # Try to get live price from yf.Ticker if download failed
    try:
        price = round(float(yf.Ticker(ticker).fast_info['last_price']), 2)
    except:
        price = "---"
    
    # Action Logic
    if score >= 3: action = "🟢 GO LONG"
    elif score <= -1: action = "🔴 GO SHORT"
    else: action = "⚪ WAIT"
        
    results.append({
        "Stock": name, "Price": price, "Score": f"{score}/7", 
        "Signal": action, "Latest News": news
    })
    progress_bar.progress((i + 1) / len(STOCKS))

# 7. Final Display
if results:
    df = pd.DataFrame(results)
    st.table(df)
else:
    st.warning("All data sources are temporarily busy. Please try again in 1 minute.")

st.sidebar.info("Tip: If you see 'Data Source Busy', wait a moment and refresh. Free data sources have limits.")
