# --- UPDATED INDEPENDENT LOGIC: MARKET STATUS & COUNTDOWN ---
def get_market_info():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Define Market Hours
    market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    # 1. Fetch Nifty and Sensex Data
    try:
        n_data = yf.Ticker("^NSEI").fast_info
        s_data = yf.Ticker("^BSESN").fast_info  # Added Sensex Ticker
        
        nifty, nifty_prev = round(n_data['last_price'], 2), n_data['previous_close']
        sensex, sensex_prev = round(s_data['last_price'], 2), s_data['previous_close']
        
        n_delta = round(nifty - nifty_prev, 2)
        s_delta = round(sensex - sensex_prev, 2)
    except:
        nifty, n_delta, sensex, s_delta = "---", 0, "---", 0

    # 2. Determine Market Status
    is_weekend = now.weekday() >= 5
    if is_weekend:
        status = "🔴 CLOSED (WEEKEND)"
    elif now < market_open_time:
        status = "🟡 PRE-OPEN"
    elif now > market_close_time:
        status = "🔴 CLOSED"
    else:
        status = "🟢 LIVE"

    # 3. Dynamic Countdown Logic
    if status == "🟢 LIVE":
        countdown_label = "Closing In:"
        remaining = market_close_time - now
    else:
        countdown_label = "Opens In:"
        # Find next opening day (skip weekends)
        next_open = market_open_time
        if now >= market_close_time or is_weekend:
            days_ahead = 1
            if now.weekday() == 4: days_ahead = 3 # Friday -> Monday
            elif now.weekday() == 5: days_ahead = 2 # Saturday -> Monday
            next_open = (now + pd.Timedelta(days=days_ahead)).replace(hour=9, minute=15, second=0, microsecond=0)
        remaining = next_open - now

    timer_str = str(remaining).split('.')[0] # Format as HH:MM:SS
    return nifty, n_delta, sensex, s_delta, status, countdown_label, timer_str

# --- UI HEADER SETUP (Update this part in your code) ---
while True:
    nv, nd, sv, sd, stat, c_label, t_rem = get_market_info()
    with header_placeholder.container():
        # Displaying Nifty and Sensex dynamically with Up/Down colors
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 NIFTY 50", f"{nv}", delta=f"{nd}")
        col2.metric("🏛️ SENSEX", f"{sv}", delta=f"{sd}") # Now shows Sensex Up/Down
        col3.subheader(stat)
        col4.metric(c_label, t_rem) # Dynamic Countdown
        st.divider()
    
    # ... (Rest of your Module 1 and Module 2 refresh code stays the same)
    time.sleep(1)
