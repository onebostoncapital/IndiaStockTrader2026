import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="India Top 11 Trading Bot")
st.title("💹 India Top 11: Technical + News Dashboard")

# 2. Your Stock List (NSE Tickers)
STOCKS = {
    "IDEA.NS": "Vodafone Idea", "YESBANK.NS": "Yes Bank", "SUZLON.NS": "Suzlon Energy",
    "IDFCFIRSTB.NS": "IDFC First Bank", "TATASTEEL.NS": "Tata Steel", "RPOWER.NS": "Reliance Power",
    "PNB.NS": "PNB", "IRFC.NS": "IRFC", "NHPC.NS": "NHPC", "GAIL.NS": "GAIL", "MRPL.NS": "MRPL"
}

# 3. Helper function to ensure we have a single number (Fixes your ValueError)
def clean_val(val):
    if isinstance(val, pd.Series):
        return float(val.iloc[-1])
    return float(val)

# 4. The News Scanner
def get_news_sentiment(symbol):
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        if not news: return 0, "No News"
        headline = news[0]['title'].upper()
        if any(word in headline for word in ["PROFIT", "BUYBACK", "CONTRACT", "ORDER", "UPGRADE"]):
            return 1, f"🟢 {headline[:50]}..."
        if any(word in headline for word in ["PENALTY", "LOSS", "RBI", "SEBI", "STRIKE", "TARIFF"]):
            return -1, f"🔴 {headline[:50]}..."
        return 0, f"⚪ {headline[:50]}..."
    except:
        return 0, "Scanning..."

# 5. The Scoring Engine (7 Filters)
def calculate_score(symbol):
    # Download data with auto_adjust to keep columns clean
    data = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
    if data.empty: return 0, "N/A"
    
    score = 0
    # Fix: Get the very last Close price as a single number
    curr_price = clean_val(data['Close'])
    curr_open = clean_val(data['Open'])
    
    # Filter 1: Price < 300
    if curr_price <= 300: score += 1
    
    # Filter 2: Trend (Above 200 EMA)
    ema200_series = data['Close'].ewm(span=200).mean()
    ema200 = clean_val(ema200_series)
    if curr_price > ema200: score += 1
    
    # Filter 3: Trigger (9/21 EMA Cross)
    ema9 = clean_val(data['Close'].ewm(span=9).mean())
    ema21 = clean_val(data['Close'].ewm(span=21).mean())
    if ema9 > ema21: score += 1
    
    # Filter 4: Volume Spike
    last_vol = clean_val(data['Volume'])
    avg_vol = float(data['Volume'].tail(10).mean())
    if last_vol > avg_vol: score += 1
    
    # Filter 5: Candle Color
    if curr_price > curr_open: score += 1
    
    # Filter 6 & 7: News Score
    news_val, news_text = get_news_sentiment(symbol)
    score += news_val
    
    return score, news_text

# 6. Build the UI
if st.button('🔄 Refresh Data'):
    st.rerun()

st.subheader("Live Market Signals (Score 3+ for GO LONG)")
results = []

for ticker, name in STOCKS.items():
    try:
        score, latest_news = calculate_score(ticker)
        # Get live price safely
        live_info = yf.Ticker(ticker).fast_info
        price = round(float(live_info['last_price']), 2)
        
        if score >= 3: action = "🟢 GO LONG"
        elif score <= -1: action = "🔴 GO SHORT"
        else: action = "⚪ WAIT"
            
        results.append({
            "Stock": name, "Price": price, "Score": f"{score}/7", 
            "Signal": action, "Latest News": latest_news
        })
    except:
        continue

# Display Table
if results:
    df = pd.DataFrame(results)
    st.table(df)
else:
    st.error("Market data currently unavailable. Check your internet connection.")

st.sidebar.info("System Status: Active. Logic: Technical + News Hybrid.")
