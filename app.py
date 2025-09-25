import requests
import pandas as pd
import streamlit as st
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# API URLs
BINANCE_PREMIUM_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
BYBIT_FUNDING_URL = "https://api.bybit.com/v5/market/funding/history"
BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers"

# Symbols to monitor
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "XRPUSDT", "DOGEUSDT", "TRXUSDT", "ALGOUSDT", "BAKEUSDT", "THETAUSDT", "SUIUSDT", "AAVEUSDT","UNIUSDT", "XLMUSDT","BCHUSDT", "LTCUSDT", "TONUSDT", "NEARUSDT", "APTUSDT", "ETCUSDT", "WLDUSDT", "POLUSDT", "ICPUSDT", "ARBUSDT", "SEIUSDT", "FILUSDT"]

def get_binance_funding(symbol):
    """
    Get current Binance funding rate from premium index endpoint (real-time data)
    Falls back to funding history if premium index doesn't work
    """
    try:
        # Primary method: Use premium index endpoint for real-time funding rate
        r = requests.get(BINANCE_PREMIUM_URL, params={"symbol": symbol}, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        if data and "lastFundingRate" in data:
            return float(data["lastFundingRate"])
        
        # Fallback: Use funding rate history endpoint
        r2 = requests.get(BINANCE_FUNDING_URL, params={"symbol": symbol, "limit": 1}, timeout=5)
        r2.raise_for_status()
        data2 = r2.json()
        
        if data2 and len(data2) > 0:
            return float(data2[0]["fundingRate"])
            
        return None
        
    except Exception as e:
        st.error(f"Binance API error for {symbol}: {str(e)}")
        return None

def get_bybit_funding(symbol):
    """
    Get current Bybit funding rate from tickers endpoint (more current data)
    Falls back to funding history if tickers doesn't have the data
    """
    try:
        # Primary method: Use tickers endpoint for most current funding rate
        r = requests.get(BYBIT_TICKERS_URL, params={
            "category": "linear", 
            "symbol": symbol
        }, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        if data["retCode"] == 0 and data["result"]["list"]:
            ticker_data = data["result"]["list"][0]
            if "fundingRate" in ticker_data and ticker_data["fundingRate"] is not None:
                return float(ticker_data["fundingRate"])
        
        # Fallback: Use funding history endpoint
        r2 = requests.get(BYBIT_FUNDING_URL, params={
            "category": "linear", 
            "symbol": symbol, 
            "limit": 1
        }, timeout=5)
        r2.raise_for_status()
        data2 = r2.json()
        
        if data2["retCode"] == 0 and data2["result"]["list"]:
            return float(data2["result"]["list"][0]["fundingRate"])
            
        return None
        
    except Exception as e:
        st.error(f"Bybit API error for {symbol}: {str(e)}")
        return None

def format_funding_rate(rate):
    """Format funding rate as percentage with proper formatting"""
    if rate is None:
        return "ERR"
    
    # Funding rates are already in decimal format (e.g., 0.0001 = 0.01%)
    # Convert to percentage by multiplying by 100
    percentage = rate * 100
    
    # Format based on magnitude
    if abs(percentage) >= 0.001:  # >= 0.001%
        return f"{percentage:.4f}%"
    elif abs(percentage) >= 0.0001:  # >= 0.0001%
        return f"{percentage:.5f}%"
    else:  # Very small values
        return f"{percentage:.2e}%"

def get_rate_color(rate):
    """Return color based on funding rate value"""
    if rate is None:
        return "color: #ff6b6b;"
    if rate > 0:
        return "color: #51cf66;"
    elif rate < 0:
        return "color: #ff6b6b;"
    else:
        return "color: #868e96;"

def create_styled_dataframe(data):
    """Create a styled dataframe similar to CoinGlass"""
    df = pd.DataFrame(data)
    
    # Apply styling
    def highlight_rows(row):
        styles = [''] * len(row)
        
        # Color code the rates
        binance_rate = row['Binance_Raw'] if 'Binance_Raw' in row and pd.notna(row['Binance_Raw']) else None
        bybit_rate = row['Bybit_Raw'] if 'Bybit_Raw' in row and pd.notna(row['Bybit_Raw']) else None
        
        if binance_rate is not None:
            styles[1] = get_rate_color(binance_rate)
        else:
            styles[1] = "color: #ff6b6b;"
            
        if bybit_rate is not None:
            styles[2] = get_rate_color(bybit_rate)
        else:
            styles[2] = "color: #ff6b6b;"
            
        # Highlight significant differences
        if 'Abs_Diff_Raw' in row and pd.notna(row['Abs_Diff_Raw']):
            if row['Abs_Diff_Raw'] > 0.0001:  # 0.01%
                styles[3] = "color: #ffd43b; font-weight: bold;"
        
        return styles
    
    # Display dataframe without raw columns
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
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
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

# Create columns for metrics
col1, col2, col3, col4 = st.columns(4)

# Placeholders for dynamic content
table_placeholder = st.empty()
last_update_placeholder = st.empty()
metrics_placeholder = st.container()

# Auto-refresh logic
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = 0
    

# Check if we need to refresh (every 30 seconds)
current_time = time.time()
if current_time - st.session_state.last_refresh > 60 or st.session_state.last_refresh == 0:
    st_autorefresh(interval=30000, key="data_refresher")
    
    with st.spinner('Fetching funding rates...'):
        rows = []
        total_symbols = 0
        error_count = 0
        max_diff = 0
        max_diff_symbol = ""
        debug_info = {}
        
        for symbol in symbols:
            total_symbols += 1
            b_rate = get_binance_funding(symbol)
            y_rate = get_bybit_funding(symbol)
            
            # Debug information
            debug_info[symbol] = {
                'binance_raw': b_rate,
                'bybit_raw': y_rate,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }

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
                    'Binance': "ERR",
                    'Bybit': "ERR",
                    'Abs Diff': "ERR",
                    'Binance_Raw': None,
                    'Bybit_Raw': None,
                    'Abs_Diff_Raw': None
                })
    
    st.session_state.data = rows
    st.session_state.debug_info = debug_info
    st.session_state.total_symbols = total_symbols
    st.session_state.error_count = error_count
    st.session_state.max_diff = max_diff
    st.session_state.max_diff_symbol = max_diff_symbol
    st.session_state.last_refresh = current_time
    
    

# Display metrics
with metrics_placeholder:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📈 Total Symbols",
            value=st.session_state.total_symbols
        )
    
    with col2:
        st.metric(
            label="✅ Active Pairs",
            value=st.session_state.total_symbols - st.session_state.error_count
        )
    
    with col3:
        st.metric(
            label="⚠️ Errors",
            value=st.session_state.error_count
        )
    
    with col4:
        st.metric(
            label="🎯 Max Difference",
            value=format_funding_rate(st.session_state.max_diff),
            delta=st.session_state.max_diff_symbol if st.session_state.max_diff_symbol else None
        )

# Display the styled table
with table_placeholder.container():
    if st.session_state.data:
        styled_df = create_styled_dataframe(st.session_state.data)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.error("No data available")

# Last update info
last_update_time = datetime.fromtimestamp(st.session_state.last_refresh).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f'<p class="refresh-info">Last updated: {last_update_time} | Auto-refreshes every 30 seconds</p>', unsafe_allow_html=True)

# Manual refresh button
if st.button("🔄 Refresh Now", use_container_width=True):
    st.session_state.last_refresh = 0
    st.rerun()


# Add information section
with st.expander("ℹ️ Information"):
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
    
    **Data Sources:**
    - Binance Futures API: `/fapi/v1/fundingRate` (Current funding rate)
    - Bybit API: `/v5/market/tickers` + `/v5/market/funding/history` (Hybrid approach)
    
    **Note:** Bybit funding rate fetching uses a dual approach for accuracy:
    1. First tries the tickers endpoint for current rates
    2. Falls back to funding history if needed
    """)

# Debug information (can be enabled during testing)
if st.checkbox("🔍 Show Debug Info"):
    st.markdown("**Debug Information:**")
    if 'debug_info' in st.session_state:
        for symbol, info in st.session_state.debug_info.items():
            st.write(f"**{symbol}:** {info}")
    else:
        st.write("No debug information available. Refresh data to see debug info.")
