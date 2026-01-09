import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. Page Config
st.set_page_config(layout="wide", page_title="India Top 11 Master Dashboard")
st.title("💹 India Top 11: Master Rule Book")

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

def calculate_master_signal(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return 0, "⚠️ Link Busy"
        score = 0
        cp = get_num(df['Close'])
        # Rules 2-7
        if 1 <= cp <= 300: score += 1
        if cp > get_num(df['Close'].ewm(span=200).mean()): score += 1
        if get_num(df['Low']) <= float(df['Low'].tail(20).min()): score += 1
        if get_num(df['Close'].ewm(span=9).mean()) > get_num(df['Close'].ewm(span=21).mean()): score += 1
        if cp > get_num(df['Open']): score += 1
        if get_num(df['Volume']) > float(df['Volume'].tail(10).mean()): score += 1
        # Rule 8: News
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

# UI Construction
st.sidebar.header("Controls")
if st.sidebar.button('🔄 Refresh Market Data'): st.rerun()

results = []
p_bar = st.progress(0)

for i, (ticker, name) in enumerate(STOCKS.items()):
    score, mkt_note = calculate_master_signal(ticker)
    try:
        live = round(get_num(yf.Ticker(ticker).fast_info['last_price']), 2)
    except: live = "---"
    
    # Rule 9: Signal Generation
    if score >= 3: act = "🔥 GO LONG"
    elif score <= -1: act = "⚠️ GO SHORT"
    else: act = "⏳ WAIT"
        
    results.append({
        "Stock Name": name,
        "CMP (₹)": live,
        "Power": "⭐" * score, # Visual stars for the score
        "Score": f"{score}/7",
        "Signal": act,
        "Market Note": mkt_note
    })
    p_bar.progress((i + 1) / len(STOCKS))

# 5. Professional Table Display
df_final = pd.DataFrame(results)
st.dataframe(df_final, use_container_width=True, hide_index=True)

st.sidebar.success(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.write("System: 7-Layer SMC Filter Active")
