import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# 1. Page Config
st.set_page_config(layout="wide", page_title="India Top 11 Master Dashboard")
st.title("💹 India Top 11: Rules-Locked Strategy")

# 2. The Fixed Universe (Rule 1)
STOCKS = {
    "IDEA.NS": "Vodafone Idea", "YESBANK.NS": "Yes Bank", "SUZLON.NS": "Suzlon Energy",
    "IDFCFIRSTB.NS": "IDFC First Bank", "TATASTEEL.NS": "Tata Steel", "RPOWER.NS": "Reliance Power",
    "PNB.NS": "PNB", "IRFC.NS": "IRFC", "NHPC.NS": "NHPC", "GAIL.NS": "GAIL", "MRPL.NS": "MRPL"
}

def clean_val(val):
    if isinstance(val, pd.Series): return float(val.iloc[-1])
    return float(val)

# 3. The Signal Engine (Rules 2 to 9)
def calculate_master_signal(symbol):
    try:
        # Download 1 month of 15m data to cover 200 EMA and 20-candle lookback
        data = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if data.empty: return 0, "⚠️ Data Link Failed"
        
        score = 0
        curr_price = clean_val(data['Close'])
        curr_open = clean_val(data['Open'])
        
        # RULE 2: Price Cap (₹1 - ₹300)
        if 1 <= curr_price <= 300: score += 1
        
        # RULE 3: Macro Trend (Above 200 EMA)
        ema200 = data['Close'].ewm(span=200).mean()
        if curr_price > clean_val(ema200): score += 1
        
        # RULE 4: SMC Trap (20-candle Lookback)
        recent_low = data['Low'].tail(20).min()
        if data['Low'].iloc[-1] <= recent_low: score += 1 # Price 'swept' the low
        
        # RULE 5: Execution (9/21 EMA Cross)
        ema9 = clean_val(data['Close'].ewm(span=9).mean())
        ema21 = clean_val(data['Close'].ewm(span=21).mean())
        if ema9 > ema21: score += 1
        
        # RULE 6: Confirmation (Green Candle)
        if curr_price > curr_open: score += 1
        
        # RULE 7: Momentum (Volume > 10-avg)
        avg_vol = data['Volume'].tail(10).mean()
        if clean_val(data['Volume']) > avg_vol: score += 1
        
        # RULE 8: Intelligence (News)
        news_score = 0
        headline = "No News"
        try:
            ticker_obj = yf.Ticker(symbol)
            news = ticker_obj.news
            if news:
                headline = news[0]['title'].upper()
                if any(w in headline for w in ["PROFIT", "ORDER", "WIN"]): news_score = 1
                if any(w in headline for w in ["PENALTY", "RBI", "LOSS"]): news_score = -1
        except: pass
        
        score += news_score
        return score, headline[:40] + "..."
    
    except Exception as e:
        return 0, f"Error: {str(e)[:20]}"

# 4. Dashboard UI
st.sidebar.header("Strategy Settings")
if st.sidebar.button('🔄 Refresh Signals'):
    st.rerun()

st.info("Strategy: SMC Liquidity + EMA Crossover + News Filter (Target Score: 3+)")

results = []
progress_bar = st.progress(0)

for i, (ticker, name) in enumerate(STOCKS.items()):
    score, info = calculate_master_signal(ticker)
    
    # Get live price
    try:
        price = round(float(yf.Ticker(ticker).fast_info['last_price']), 2)
    except:
        price = "---"

    # RULE 9: Signal Generation (3+ Rule)
    if score >= 3:
        signal = "🟢 GO LONG"
    elif score <= -1:
        signal = "🔴 GO SHORT"
    else:
        signal = "⚪ WAIT"
        
    results.append({
        "Stock": name,
        "Price": price,
        "Score": f"{score}/7",
        "Action": signal,
        "Market Note": info
    })
    progress_bar.progress((i + 1) / len(STOCKS))

# 5. Show Table
st.table(pd.DataFrame(results))
