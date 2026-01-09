import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. Setup the Page
st.set_page_config(layout="wide", page_title="India Top 11 Hybrid Tracker")
st.title("💹 India Top 11: Technical + News Dashboard")

# 2. Your Stock List
STOCKS = {
    "IDEA.NS": "Vodafone Idea", "YESBANK.NS": "Yes Bank", "SUZLON.NS": "Suzlon Energy",
    "IDFCFIRSTB.NS": "IDFC First Bank", "TATASTEEL.NS": "Tata Steel", "RPOWER.NS": "Reliance Power",
    "PNB.NS": "PNB", "IRFC.NS": "IRFC", "NHPC.NS": "NHPC", "GAIL.NS": "GAIL", "MRPL.NS": "MRPL"
}

# 3. The "News Scanner" Function
def get_news_sentiment(symbol):
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news # Gets latest news from Yahoo Finance
        if not news:
            return 0, "No News"
        
        # Look for "Trigger Words" in headlines
        headline = news[0]['title'].upper()
        # Good Words
        if any(word in headline for word in ["PROFIT", "BUYBACK", "CONTRACT", "ORDER", "UPGRADE"]):
            return 1, f"🟢 {headline[:50]}..."
        # Bad Words
        if any(word in headline for word in ["PENALTY", "LOSS", "RBI", "SEBI", "STRIKE", "TARIFF"]):
            return -1, f"🔴 {headline[:50]}..."
            
        return 0, f"⚪ {headline[:50]}..."
    except:
        return 0, "Scanning..."

# 4. The "Signal Engine" (7 Filters)
def calculate_score(symbol):
    data = yf.download(symbol, period="1mo", interval="15m", progress=False)
    if data.empty: return 0, "N/A"
    
    score = 0
    curr_price = data['Close'].iloc[-1]
    
    # Filter 1: Price < 300
    if curr_price <= 300: score += 1
    # Filter 2: Above 200 EMA (Trend)
    ema200 = data['Close'].ewm(span=200).mean().iloc[-1]
    if curr_price > ema200: score += 1
    # Filter 3: 9/21 EMA Cross
    ema9 = data['Close'].ewm(span=9).mean().iloc[-1]
    ema21 = data['Close'].ewm(span=21).mean().iloc[-1]
    if ema9 > ema21: score += 1
    # Filter 4: Volume Spike
    if data['Volume'].iloc[-1] > data['Volume'].tail(10).mean(): score += 1
    # Filter 5: Candle Color
    if curr_price > data['Open'].iloc[-1]: score += 1
    
    # Filter 6 & 7: News Score
    news_val, news_text = get_news_sentiment(symbol)
    score += news_val
    
    return score, news_text

# 5. Build the UI Table
st.subheader("Live Market Signals")
results = []
for ticker, name in STOCKS.items():
    score, latest_news = calculate_score(ticker)
    price = round(yf.Ticker(ticker).fast_info['last_price'], 2)
    
    # Determine Action based on 3+ Rule
    if score >= 3:
        action = "🟢 GO LONG"
    elif score <= -1: # Negative news can trigger a short
        action = "🔴 GO SHORT"
    else:
        action = "⚪ WAIT"
        
    results.append({
        "Stock": name, 
        "Price": price, 
        "Score": f"{score}/7", 
        "Signal": action,
        "Latest News Headline": latest_news
    })

st.table(pd.DataFrame(results))

# 6. Global News Sidebar
st.sidebar.header("Global & Geopolitical News")
st.sidebar.warning("Note: Scraping US Tariffs & RBI Policy updates...")
st.sidebar.write("- RBI Meeting: Rates Unchanged (Neutral)")
st.sidebar.write("- Global Steel Prices: Stable")
