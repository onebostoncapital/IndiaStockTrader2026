import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# 1. Page Config
st.set_page_config(layout="wide", page_title="India Top 11 Master Dashboard")
st.title("💹 India Top 11: Master Rule Book")

# 2. Fixed Universe (Rule 1)
STOCKS = {
    "IDEA.NS": "Vodafone Idea", "YESBANK.NS": "Yes Bank", "SUZLON.NS": "Suzlon Energy",
    "IDFCFIRSTB.NS": "IDFC First Bank", "TATASTEEL.NS": "Tata Steel", "RPOWER.NS": "Reliance Power",
    "PNB.NS": "PNB", "IRFC.NS": "IRFC", "NHPC.NS": "NHPC", "GAIL.NS": "GAIL", "MRPL.NS": "MRPL"
}

# Safety function to extract a single number no matter what
def get_num(data_input):
    try:
        if isinstance(data_input, (pd.Series, pd.DataFrame)):
            return float(data_input.iloc[-1])
        return float(data_input)
    except:
        return 0.0

# 3. The Signal Engine (Locked Rules 2-9)
def calculate_master_signal(symbol):
    try:
        # Fetching 1 month of 15m data
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return 0, "⚠️ Connection Busy"
        
        score = 0
        
        # Rule 2: Price Cap (₹1 - ₹300)
        curr_price = get_num(df['Close'])
        if 1 <= curr_price <= 300: score += 1
        
        # Rule 3: Macro Trend (Above 200 EMA)
        ema200_val = get_num(df['Close'].ewm(span=200).mean())
        if curr_price > ema200_val: score += 1
        
        # Rule 4: SMC Trap (20-candle Low Sweep)
        low_20 = float(df['Low'].tail(20).min())
        if get_num(df['Low']) <= low_20: score += 1
        
        # Rule 5: Execution (9/21 EMA Cross)
        ema9 = get_num(df['Close'].ewm(span=9).mean())
        ema21 = get_num(df['Close'].ewm(span=21).mean())
        if ema9 > ema21: score += 1
        
        # Rule 6: Confirmation (Green Candle)
        if curr_price > get_num(df['Open']): score += 1
        
        # Rule 7: Momentum (Volume > 10-period avg)
        vol_now = get_num(df['Volume'])
        vol_avg = float(df['Volume'].tail(10).mean())
        if vol_now > vol_avg: score += 1
        
        # Rule 8: Intelligence (News)
        news_point = 0
        note = "No News"
        try:
            t = yf.Ticker(symbol)
            if t.news:
                head = t.news[0]['title'].upper()
                note = head[:40] + "..."
                if any(x in head for x in ["PROFIT", "ORDER", "WIN"]): news_point = 1
                if any(x in head for x in ["RBI", "PENALTY", "LOSS"]): news_point = -1
        except: pass
        
        score += news_point
        return score, note

    except Exception as e:
        return 0, f"Wait & Refresh"

# 4. Dashboard UI
st.sidebar.header("Controls")
if st.sidebar.button('🔄 Refresh Signals'):
    st.rerun()

st.info("Strategy: 200 EMA Trend + 20-Candle SMC Trap + 9/21 EMA Cross (Target: 3+)")

results = []
p_bar = st.progress(0)

for i, (ticker, name) in enumerate(STOCKS.items()):
    score, mkt_note = calculate_master_signal(ticker)
    
    # Live Price Fetch
    try:
        live_price = round(get_num(yf.Ticker(ticker).fast_info['last_price']), 2)
        if live_price == 0: live_price = round(get_num(yf.download(ticker, period="1d", interval="1m", progress=False)['Close']), 2)
    except:
        live_price = "---"

    # Rule 9: Signal (3+ Rule)
    if score >= 3: act = "🟢 GO LONG"
    elif score <= -1: act = "🔴 GO SHORT"
    else: act = "⚪ WAIT"
        
    results.append({
        "Stock": name,
        "Price": live_price,
        "Score": f"{score}/7",
        "Action": act,
        "Market Note": mkt_note
    })
    p_bar.progress((i + 1) / len(STOCKS))

# 5. Show Table
st.table(pd.DataFrame(results))
st.sidebar.write(f"Last Scan: {datetime.now().strftime('%H:%M:%S')}")
