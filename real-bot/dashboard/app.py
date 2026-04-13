import streamlit as st
import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# Load env
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent.resolve()
env_path = project_root / "real-bot" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY", os.getenv("POLY_PK", ""))
FUNDER_ADDRESS = os.getenv("FUNDER_ADDRESS", "")
POLY_API_KEY = os.getenv("POLY_API_KEY", "")
POLY_API_SECRET = os.getenv("POLY_API_SECRET", "")
POLY_API_PASSPHRASE = os.getenv("POLY_API_PASSPHRASE", "")
RPC_URL = os.getenv("RPC_URL", "https://polygon-mainnet.g.alchemy.com/v2/vU4_GtkDPUFPLhuR-e8-X")
CLOB_HTTP_URL = os.getenv("CLOB_HTTP_URL", "https://clob.polymarket.com")
USDC_CONTRACT = os.getenv("USDC_CONTRACT_ADDRESS", "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

@st.cache_data(ttl=60)
def get_wallet_address():
    if not PRIVATE_KEY:
        return None
    try:
        account = Account.from_key(PRIVATE_KEY.replace("0x", ""))
        return account.address
    except:
        return None

@st.cache_data(ttl=60)
def get_balances():
    wallet_addr = get_wallet_address()
    funder_addr = FUNDER_ADDRESS
    
    if not wallet_addr and not funder_addr:
        return {"wallet_usdc": 0, "wallet_matic": 0, "funder_usdc": 0, "funder_matic": 0}
    
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        usdc_abi = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]
        usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_CONTRACT), abi=usdc_abi)
        
        result = {"wallet_usdc": 0, "wallet_matic": 0, "funder_usdc": 0, "funder_matic": 0}
        
        if wallet_addr:
            result["wallet_usdc"] = usdc.functions.balanceOf(wallet_addr).call() / 1e6
            result["wallet_matic"] = w3.eth.get_balance(wallet_addr) / 1e18
        
        if funder_addr:
            result["funder_usdc"] = usdc.functions.balanceOf(funder_addr).call() / 1e6
            result["funder_matic"] = w3.eth.get_balance(funder_addr) / 1e18
        
        return result
    except:
        return {"wallet_usdc": 0, "wallet_matic": 0, "funder_usdc": 0, "funder_matic": 0}

@st.cache_data(ttl=120)
def get_markets(limit=50):
    try:
        r = requests.get(f"{GAMMA_API_URL}/markets", params={"closed": False, "limit": limit, "active": "true"}, timeout=30)
        return r.json()
    except:
        return []

@st.cache_data(ttl=60)
def get_trade_history():
    if not POLY_API_KEY:
        return []
    try:
        key = PRIVATE_KEY.replace("0x", "") if PRIVATE_KEY else None
        creds = ApiCreds(api_key=POLY_API_KEY, api_secret=POLY_API_SECRET, api_passphrase=POLY_API_PASSPHRASE)
        client = ClobClient(host=CLOB_HTTP_URL, chain_id=137, key=key, creds=creds)
        trades = client.get_trades()
        
        # Get market info for each trade
        markets = get_markets(limit=200)
        market_map = {}
        for m in markets:
            cid = m.get('conditionId') or m.get('id')
            market_map[cid] = m.get('question', 'Unknown')
        
        result = []
        for t in trades[:30]:
            if isinstance(t, dict):
                try:
                    size = float(t.get('size', 0))
                    price = float(t.get('price', 0))
                    market_id = t.get('market', '')
                    market_name = market_map.get(market_id, 'Unknown')[:35]
                except:
                    size, price, market_name = 0, 0, 'Unknown'
                result.append({
                    'market': market_name,
                    'side': t.get('side', t.get('trader_side', '?')),
                    'size': size,
                    'price': price,
                    'total': size * price,
                    'time': t.get('match_time', ''),
                    'status': t.get('status', '')
                })
        return result
    except:
        return []

# ==============================================================================
# PAGE CONFIG
# ==============================================================================

st.set_page_config(page_title="Polymarket Bot", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    .block-container {padding: 0.5rem 1rem !important;}
    .stMetric {padding: 0.2rem !important;}
    .stMetric label {font-size: 0.6rem !important;}
    .stMetric [data-testid="stMetricValue"] {font-size: 0.85rem !important;}
    h1 {font-size: 1.1rem !important; margin: 0 !important;}
    h2, h3 {font-size: 0.9rem !important;}
    p, .stWrite {font-size: 0.75rem !important;}
    .stTabs [data-baseweb="tab"] {font-size: 0.75rem !important; padding: 0.3rem 0.8rem !important;}
    [data-testid="stHorizontalBlock"] {gap: 0.5rem !important;}
    .stDivider {margin: 0.3rem 0 !important;}
    div[data-testid="stExpander"] {border: none !important;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# HEADER
# ==============================================================================

balances = get_balances()

# Header row
h1, h2, h3, h4, h5 = st.columns([2, 1, 1, 1, 1])
with h1:
    st.markdown("### 🎯 Polymarket Bot")
with h2:
    st.metric("USDC Wallet", f"${balances['wallet_usdc']:.2f}")
with h3:
    st.metric("MATIC Wallet", f"{balances['wallet_matic']:.2f}")
with h4:
    st.metric("USDC Poly", f"${balances['funder_usdc']:.2f}")
with h5:
    st.metric("MATIC Poly", f"{balances['funder_matic']:.2f}")

st.markdown("---")

# ==============================================================================
# TABS
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💰 Active", "📜 History", "📈 Markets"])

# ========== DASHBOARD ==========
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Wallet USDC", f"${balances['wallet_usdc']:.2f}")
    with c2:
        st.metric("Wallet MATIC", f"{balances['wallet_matic']:.2f}")
    with c3:
        st.metric("Polymarket USDC", f"${balances['funder_usdc']:.2f}")
    with c4:
        st.metric("Polymarket MATIC", f"{balances['funder_matic']:.2f}")
    
    st.write("---")
    
    # Connection
    wallet = get_wallet_address()
    if wallet:
        st.success(f"✅ Wallet: `{wallet[:12]}...{wallet[-6:]}`")
    else:
        st.error("❌ Wallet not connected")

# ========== ACTIVE BETS ==========
with tab2:
    st.info("Position tracking coming soon")

# ========== HISTORY ==========
with tab3:
    trades = get_trade_history()
    if not trades:
        st.info("No history yet")
    else:
        st.write(f"**Total: {len(trades)} trades**")
        
        # Header
        hc1, hc2, hc3, hc4, hc5 = st.columns([3, 1, 1, 1, 1])
        hc1.write("**Market**")
        hc2.write("**Side**")
        hc3.write("**Size**")
        hc4.write("**Price**")
        hc5.write("**Total**")
        st.divider()
        
        for t in trades:
            try:
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
                c1.write(f"{t['market']}")
                c2.write(t['side'])
                c3.write(f"${t['size']:.2f}")
                c4.write(f"@{t['price']:.2f}")
                c5.write(f"${t['total']:.2f}")
            except:
                pass

# ========== MARKETS ==========
with tab4:
    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        min_vol = st.slider("Min Volume", 0, 50000, 1000, label_visibility="collapsed")
    with col_f2:
        st.write(f"Found: {len(get_markets())} markets")
    
    markets = get_markets(limit=100)
    if markets:
        filtered = [m for m in markets if float(m.get("volume24hr", 0) or 0) >= min_vol]
        filtered = sorted(filtered, key=lambda x: float(x.get("volume24hr", 0) or 0), reverse=True)
        
        # Header
        mc1, mc2, mc3, mc4 = st.columns([3, 1, 1, 1])
        mc1.write("**Market**")
        mc2.write("**Yes**")
        mc3.write("**No**")
        mc4.write("**Volume**")
        st.divider()
        
        for m in filtered[:25]:
            prices = m.get("outcomePrices", "[]")
            if isinstance(prices, str):
                prices = json.loads(prices)
            yes_p = float(prices[0]) if prices else 0
            no_p = float(prices[1]) if len(prices) > 1 else 0
            vol = float(m.get("volume24hr", 0) or 0)
            
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"{m.get('question', '')[:40]}")
            c2.write(f"{yes_p:.0%}")
            c3.write(f"{no_p:.0%}")
            c4.write(f"${vol:,.0f}")
    else:
        st.error("Failed to load markets")

st.markdown("---")
st.caption("🎯 Polymarket AutoBet Dashboard")
