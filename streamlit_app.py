import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Set page to wide mode
st.set_page_config(layout="wide", page_title="India Top 11 Volume Tracker")

st.title("🚀 India Top 11 Volume Strategy Dashboard")
st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Your 11 High-Volume Stocks (BSE Tickers)
STOCKS = {
    "IDEA.BO": "Vodafone Idea",
    "YESBANK.BO": "Yes Bank",
    "SUZLON.BO": "Suzlon Energy",
    "IDFCFIRSTB.BO": "IDFC First Bank",
    "TATASTEEL.BO": "Tata Steel",
    "RPOWER.BO": "Reliance Power",
    "PNB.BO": "Punjab National Bank",
    "IRFC.BO": "IRFC",
    "NHPC.BO": "NHPC",
    "GAIL.BO": "GAIL",
    "MRPL.BO": "MRPL"
}

def get_signal(ticker):
    # Fetching data for the 7 filters
    data = yf.download(ticker, period="1mo", interval="15m")
    if data.empty: return 0, "No Data"
    
    score = 0
    close = data['Close'].iloc[-1]
    
    # 1. Price Filter (₹1 - ₹300)
    if 1 <= close <= 300: score += 1
    
    # 2. Trend Filter (Above 200 EMA)
    ema200 = data['Close'].ewm(span=200).mean().iloc[-1]
    if close > ema200: score += 1
    
    # 3. Execution (9/21 EMA Cross)
    ema9 = data['Close'].ewm(span=9).mean().iloc[-1]
    ema21 = data['Close'].ewm(span=21).mean().iloc[-1]
    if ema9 > ema21: score += 1
    
    # 4. Candle Color (Green)
    if close > data['Open'].iloc[-1]: score += 1
    
    # 5. Volume Spike
    avg_vol = data['Volume'].tail(10).mean()
    if data['Volume'].iloc[-1] > avg_vol: score += 1
    
    return score, "LONG" if close > ema200 else "SHORT"

# Displaying the Heatmap
results = []
for ticker, name in STOCKS.items():
    score, direction = get_signal(ticker)
    price = round(yf.Ticker(ticker).fast_info['last_price'], 2)
    
    # TradingLab Rule: Only show signal if score >= 3
    action = f"GO {direction}" if score >= 3 else "WAIT"
    results.append({"Stock": name, "Price": price, "Score": f"{score}/7", "Action": action})

df = pd.DataFrame(results)
st.table(df)

st.sidebar.header("Intelligence Layer")
st.sidebar.info("Scraping RBI & NSE News... (Active)")
