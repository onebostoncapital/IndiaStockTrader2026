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

# 3. Multi-Source Price Fetcher (Backup Logic)
def get_live_price(ticker):
    """Try multiple ways to get the price if one fails."""
    # Source A: Fast Info (Standard)
    try:
        t = yf.Ticker(ticker)
        price = t.fast_info['last_price']
        if price > 0: return round(float(price), 2)
    except:
        pass
    
    # Source B: Historical Download (Backup)
    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)
        if not data.empty:
            price = data['Close'].iloc[-1]
            return round(float(price), 2)
    except:
        pass
        
    return 0.0

# 4. Helper function to ensure clean numbers
def clean_val(val):
    if isinstance(val, pd.Series):
        return float(val.iloc[-1])
    return float(val)

# 5. The News & Scoring Engine
def calculate_score(symbol):
    try:
        data = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if data.empty: return 0, "No Data"
        
        score = 0
        curr_price = clean_val(data['Close'])
        
        # Rule 1: Price Cap
        if curr_price <= 300: score += 1
        # Rule 2: Trend (200 EMA)
        ema200 = clean_val(data['Close'].ewm(span=200).mean())
        if curr_price > ema200: score += 1
        # Rule 3: 9/21 EMA Cross
        ema9 = clean_val(data['Close'].ewm(span=9).mean())
        ema21 = clean_val(data['Close'].ewm(span=21).mean())
        if ema9 > ema21: score += 1
        
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
        return 0, "Error Scanning"

# 6. Build UI
if st.button('🔄 Refresh Prices & Signals'):
    st.rerun()

results = []
for ticker, name in STOCKS.items():
    price = get_live_price(ticker)
    
    # If price is 0, skip to avoid errors
    if price == 0:
        continue
        
    score, news = calculate_score(ticker)
    
    # Action Logic
    if score >= 3: action = "🟢 GO LONG"
    elif score <= -1: action = "🔴 GO SHORT"
    else: action = "⚪ WAIT"
        
    results.append({
        "Stock": name, "Price": price, "Score": f"{score}/7", 
        "Signal": action, "Latest News": news
    })

# 7. Final Display
if results:
    st.table(pd.DataFrame(results))
else:
    st.warning("Data providers are currently busy. Please wait 10 seconds and click 'Refresh'.")

st.sidebar.markdown("### 🛠️ Multi-Source System")
st.sidebar.write("If Yahoo fails, the system tries a deep-download fallback.")
