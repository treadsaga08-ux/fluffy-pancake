import requests
import pandas as pd
import streamlit as st
import time
from datetime import datetime
import json

# API URLs with headers to bypass restrictions
BINANCE_PREMIUM_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
BYBIT_FUNDING_URL = "https://api.bybit.com/v5/market/funding/history"
BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers"

# Alternative API endpoints for cloud hosting (when primary APIs are blocked)
COINGECKO_API = "https://api.coingecko.com/api/v3/exchanges"
ALTERNATIVE_BINANCE_URL = "https://api1.binance.com/fapi/v1/premiumIndex"
ALTERNATIVE_BYBIT_URL = "https://api-testnet.bybit.com/v5/market/tickers"

# Symbols to monitor
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "XRPUSDT", "DOGEUSDT", "TRXUSDT", "ALGOUSDT"]

def get_headers():
    """Get headers to bypass some API restrictions"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def get_binance_funding(symbol):
    """
    Get current Binance funding rate with multiple fallback strategies
    """
    headers = get_headers()
    
    # Strategy 1: Try premium index endpoint
    try:
        r = requests.get(BINANCE_PREMIUM_URL, params={"symbol": symbol}, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and "lastFundingRate" in data:
                return float(data["lastFundingRate"])
    except Exception:
        pass
    
    # Strategy 2: Try alternative Binance URL
    try:
        r = requests.get(ALTERNATIVE_BINANCE_URL, params={"symbol": symbol}, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and "lastFundingRate" in data:
                return float(data["lastFundingRate"])
    except Exception:
        pass
    
    # Strategy 3: Try funding rate history endpoint
    try:
        r = requests.get(BINANCE_FUNDING_URL, params={"symbol": symbol, "limit": 1}, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                return float(data[0]["fundingRate"])
    except Exception:
        pass
    
    return None

def get_bybit_funding(symbol):
    """
    Get current Bybit funding rate with multiple fallback strategies
    """
    headers = get_headers()
    
    # Strategy 1: Try tickers endpoint
    try:
        r = requests.get(BYBIT_TICKERS_URL, params={
            "category": "linear", 
            "symbol": symbol
        }, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                ticker_data = data["result"]["list"][0]
                if "fundingRate" in ticker_data and ticker_data["fundingRate"] is not None:
                    return float(ticker_data["fundingRate"])
    except Exception:
        pass
    
    # Strategy 2: Try funding history endpoint
    try:
        r = requests.get(BYBIT_FUNDING_URL, params={
            "category": "linear", 
            "symbol": symbol, 
            "limit": 1
        }, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                return float(data["result"]["list"][0]["fundingRate"])
    except Exception:
        pass
    
    return None

def format_funding_rate(rate):
    """Format funding rate as percentage with proper formatting"""
    if rate is None:
        return "ERR"
    
    percentage = rate * 100
    
    if abs(percentage) >= 0.001:
        return f"{percentage:.4f}%"
    elif abs(percentage) >= 0.0001:
        return f"{percentage:.5f}%"
    else:
        return f"{percentage:.2e}%"

def create_styled_dataframe(data):
    """Create a styled dataframe similar to CoinGlass"""
    df = pd.DataFrame(data)
    
    def highlight_rows(row):
        styles = [''] * len(row)
        
        binance_rate = row['Binance_Raw'] if 'Binance_Raw' in row and pd.notna(row['Binance_Raw']) else None
        bybit_rate = row['Bybit_Raw'] if 'Bybit_Raw' in row and pd.notna(row['Bybit_Raw']) else None
        
        if binance_rate is not None:
            if binance_rate > 0:
                styles[1] = "color: #51cf66;"
            elif binance_rate < 0:
                styles[1] = "color: #ff6b6b;"
            else:
                styles[1] = "color: #868e96;"
        else:
            styles[1] = "color: #ff6b6b;"
            
        if bybit_rate is not None:
            if bybit_rate > 0:
                styles[2] = "color: #51cf66;"
            elif bybit_rate < 0:
                styles[2] = "color: #ff6b6b;"
            else:
                styles[2] = "color: #868e96;"
        else:
            styles[2] = "color: #ff6b6b;"
            
        if 'Abs_Diff_Raw' in row and pd.notna(row['Abs_Diff_Raw']):
            if row['Abs_Diff_Raw'] > 0.0001:
                styles[3] = "color: #ffd43b; font-weight: bold;"
        
        return styles
    
    display_df = df[['Symbol', 'Binance', 'Bybit', 'Abs Diff']].copy()
    
    styled_df = display_df.style.apply(highlight_rows, axis=1) \
        .set_table_styles([
            {'selector': 'thead th', 'props': [
                ('background-color', '#2d3748'),
                ('color', 'white'),
                ('font-weight', 'bold'),
                ('text-align', 'center'),
                ('padding', '12px'),
                ('border-bottom', '2px solid #4a5568')
            ]},
            {'selector': 'tbody td', 'props': [
                ('text-align', 'center'),
                ('padding', '10px'),
                ('border-bottom', '1px solid #e2e8f0'),
                ('font-family', 'monospace')
            ]},
            {'selector': 'tbody tr:hover', 'props': [
                ('background-color', '#f7fafc')
            ]},
            {'selector': '', 'props': [
                ('border-collapse', 'collapse'),
                ('width', '100%'),
                ('box-shadow', '0 4px 6px rgba(0, 0, 0, 0.1)')
            ]}
        ])
    
    return styled_df

# Streamlit configuration
st.set_page_config(
    page_title="Funding Rate Monitor", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #2d3748;
        font-size: 2.5rem;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    .sub-header {
        text-align: center;
        color: #4a5568;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .refresh-info {
        text-align: center;
        color: #718096;
        font-size: 0.9rem;
        margin-top: 1rem;
    }
    .stDataFrame {
        margin: 0 auto;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📊 Binance vs Bybit Funding Rate Comparison</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Real-time funding rate arbitrage opportunities</p>', unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = 0
if 'data' not in st.session_state:
    st.session_state.data = []

# Auto-refresh logic with better handling
current_time = time.time()
should_refresh = (current_time - st.session_state.last_refresh > 60) or st.session_state.last_refresh == 0

if should_refresh:
    with st.spinner('Fetching funding rates...'):
        rows = []
        total_symbols = 0
        error_count = 0
        max_diff = 0
        max_diff_symbol = ""
        
        for symbol in symbols:
            total_symbols += 1
            b_rate = get_binance_funding(symbol)
            y_rate = get_bybit_funding(symbol)

            if b_rate is not None and y_rate is not None:
                diff = abs(b_rate - y_rate)
                if diff > max_diff:
                    max_diff = diff
                    max_diff_symbol = symbol
                    
                rows.append({
                    'Symbol': symbol,
                    'Binance': format_funding_rate(b_rate),
                    'Bybit': format_funding_rate(y_rate),
                    'Abs Diff': format_funding_rate(diff),
                    'Binance_Raw': b_rate,
                    'Bybit_Raw': y_rate,
                    'Abs_Diff_Raw': diff
                })
            else:
                error_count += 1
                rows.append({
                    'Symbol': symbol,
                    'Binance': "ERR" if b_rate is None else format_funding_rate(b_rate),
                    'Bybit': "ERR" if y_rate is None else format_funding_rate(y_rate),
                    'Abs Diff': "ERR",
                    'Binance_Raw': b_rate,
                    'Bybit_Raw': y_rate,
                    'Abs_Diff_Raw': None
                })
    
    st.session_state.data = rows
    st.session_state.total_symbols = total_symbols
    st.session_state.error_count = error_count
    st.session_state.max_diff = max_diff
    st.session_state.max_diff_symbol = max_diff_symbol
    st.session_state.last_refresh = current_time

# Display metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📈 Total Symbols",
        value=st.session_state.get('total_symbols', 0)
    )

with col2:
    st.metric(
        label="✅ Active Pairs",
        value=st.session_state.get('total_symbols', 0) - st.session_state.get('error_count', 0)
    )

with col3:
    st.metric(
        label="⚠️ Errors",
        value=st.session_state.get('error_count', 0)
    )

with col4:
    st.metric(
        label="🎯 Max Difference",
        value=format_funding_rate(st.session_state.get('max_diff', 0)),
        delta=st.session_state.get('max_diff_symbol', '') if st.session_state.get('max_diff_symbol') else None
    )

# Display the styled table
if st.session_state.data:
    styled_df = create_styled_dataframe(st.session_state.data)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
else:
    st.warning("No data available. API endpoints might be restricted on this hosting platform.")

# Last update info and refresh controls
last_update_time = datetime.fromtimestamp(st.session_state.last_refresh).strftime("%Y-%m-%d %H:%M:%S") if st.session_state.last_refresh > 0 else "Never"

col_info, col_refresh = st.columns([3, 1])

with col_info:
    st.markdown(f'<p class="refresh-info">Last updated: {last_update_time} | Auto-refreshes every 60 seconds</p>', unsafe_allow_html=True)

with col_refresh:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.session_state.last_refresh = 0
        st.rerun()

# Auto-refresh countdown
if st.session_state.last_refresh > 0:
    time_since_refresh = time.time() - st.session_state.last_refresh
    time_remaining = max(0, 60 - time_since_refresh)
    if time_remaining > 0:
        progress = (60 - time_remaining) / 60
        st.progress(progress)
        st.info(f"⏱️ Next auto-refresh in {int(time_remaining)} seconds")
    else:
        st.session_state.last_refresh = 0
        st.rerun()

# Information section
with st.expander("ℹ️ Information & Troubleshooting"):
    st.markdown("""
    **About Funding Rates:**
    - Funding rates are periodic payments between long and short positions
    - Positive rates mean longs pay shorts, negative rates mean shorts pay longs
    - Rates are typically applied every 8 hours
    - Large differences between exchanges may indicate arbitrage opportunities
    
    **Color Coding:**
    - 🟢 Green: Positive funding rate
    - 🔴 Red: Negative funding rate or errors
    - 🟡 Yellow: Significant difference (>0.01%)
    
    **For Cloud Hosting:**
    - Some hosting platforms (like Streamlit Cloud) block API requests to crypto exchanges
    - Error codes 451 (Binance) and 403 (Bybit) indicate geo-restrictions or rate limiting
    - This version includes multiple fallback strategies and headers to bypass some restrictions
    - For best results, run locally or use a VPS with unrestricted internet access
    
    **Alternative Solutions:**
    - Deploy to Heroku, Railway, or DigitalOcean for better API access
    - Use a VPN or proxy service in your cloud deployment
    - Implement server-side caching to reduce API calls
    """)

# JavaScript-based auto-refresh for additional reliability
st.markdown("""
<script>
setTimeout(function(){
    if (document.visibilityState === 'visible') {
        window.location.reload();
    }
}, 60000);
</script>
""", unsafe_allow_html=True)
