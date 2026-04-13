"""
Polymarket API - Provides data for external UI
"""

import os
import sys
import json
from pathlib import Path
from functools import wraps

try:
    import requests
except ImportError:
    requests = None

from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# Load env
env_path = Path(__file__).parent.parent / "real-bot" / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Configuration
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
FUNDER_ADDRESS = os.getenv("FUNDER_ADDRESS", "")
POLY_API_KEY = os.getenv("POLY_API_KEY", "")
POLY_API_SECRET = os.getenv("POLY_API_SECRET", "")
POLY_API_PASSPHRASE = os.getenv("POLY_API_PASSPHRASE", "")
RPC_URL = os.getenv("RPC_URL", "https://polygon-mainnet.g.alchemy.com/v2/vU4_GtkDPUFPLhuR-e8-X")
CLOB_HTTP_URL = os.getenv("CLOB_HTTP_URL", "https://clob.polymarket.com")
USDC_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
GAMMA_API_URL = "https://gamma-api.polymarket.com"


def get_wallet_address():
    if not PRIVATE_KEY:
        return None
    try:
        return Account.from_key(PRIVATE_KEY.replace("0x", "")).address
    except:
        return None


def get_balances():
    """Get USDC and MATIC balances from both addresses"""
    wallet_addr = get_wallet_address()
    funder_addr = FUNDER_ADDRESS
    
    if not wallet_addr and not funder_addr:
        return {"wallet": {"usdc": 0, "matic": 0}, "polymarket": {"usdc": 0, "matic": 0}}
    
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        usdc_abi = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]
        usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_CONTRACT), abi=usdc_abi)
        
        result = {"wallet": {"usdc": 0, "matic": 0}, "polymarket": {"usdc": 0, "matic": 0}}
        
        if wallet_addr:
            result["wallet"]["usdc"] = usdc.functions.balanceOf(wallet_addr).call() / 1e6
            result["wallet"]["matic"] = w3.eth.get_balance(wallet_addr) / 1e18
            result["wallet"]["address"] = wallet_addr
        
        if funder_addr:
            result["polymarket"]["usdc"] = usdc.functions.balanceOf(funder_addr).call() / 1e6
            result["polymarket"]["matic"] = w3.eth.get_balance(funder_addr) / 1e18
            result["polymarket"]["address"] = funder_addr
        
        return result
    except Exception as e:
        return {"error": str(e), "wallet": {"usdc": 0, "matic": 0}, "polymarket": {"usdc": 0, "matic": 0}}


def get_markets(limit=50):
    """Get active markets"""
    try:
        r = requests.get(f"{GAMMA_API_URL}/markets", params={"closed": False, "limit": limit, "active": "true"}, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_trade_history():
    """Get user's trade history"""
    if not POLY_API_KEY:
        return {"error": "No API credentials"}
    
    try:
        key = PRIVATE_KEY.replace("0x", "") if PRIVATE_KEY else None
        creds = ApiCreds(api_key=POLY_API_KEY, api_secret=POLY_API_SECRET, api_passphrase=POLY_API_PASSPHRASE)
        client = ClobClient(host=CLOB_HTTP_URL, chain_id=137, key=key, creds=creds)
        trades = client.get_trades()
        
        # Get market names
        markets = get_markets(limit=200)
        market_map = {}
        for m in markets:
            cid = m.get('conditionId') or m.get('id')
            market_map[cid] = m.get('question', 'Unknown')
        
        result = []
        for t in trades:
            if isinstance(t, dict):
                market_id = t.get('market', '')
                market_name = market_map.get(market_id, 'Unknown')
                
                result.append({
                    "id": t.get('id', ''),
                    "market": market_name,
                    "market_id": market_id,
                    "side": t.get('side', ''),
                    "size": float(t.get('size', 0)),
                    "price": float(t.get('price', 0)),
                    "total": float(t.get('size', 0)) * float(t.get('price', 0)),
                    "status": t.get('status', ''),
                    "time": t.get('match_time', ''),
                    "outcome": t.get('outcome', '')
                })
        return {"trades": result, "count": len(result)}
    except Exception as e:
        return {"error": str(e), "trades": []}


def get_positions():
    """Get user's current positions"""
    if not POLY_API_KEY:
        return {"error": "No API credentials"}
    
    try:
        key = PRIVATE_KEY.replace("0x", "") if PRIVATE_KEY else None
        creds = ApiCreds(api_key=POLY_API_KEY, api_secret=POLY_API_SECRET, api_passphrase=POLY_API_PASSPHRASE)
        client = ClobClient(host=CLOB_HTTP_URL, chain_id=137, key=key, creds=creds)
        
        # Get open orders as positions
        orders = client.get_orders()
        return {"positions": orders or [], "count": len(orders) if orders else 0}
    except Exception as e:
        return {"error": str(e), "positions": []}


def place_order(condition_id, side='YES', amount=1, yes_price=0.5):
    """Place an order on Polymarket"""
    if not POLY_API_KEY:
        return {"success": False, "error": "No API credentials"}
    
    try:
        key = PRIVATE_KEY.replace("0x", "") if PRIVATE_KEY else None
        creds = ApiCreds(api_key=POLY_API_KEY, api_secret=POLY_API_SECRET, api_passphrase=POLY_API_PASSPHRASE)
        client = ClobClient(host=CLOB_HTTP_URL, chain_id=137, key=key, creds=creds)
        
        # Get market info from gamma API
        markets = get_markets(None)
        market = None
        for m in markets:
            if m.get('conditionId') == condition_id:
                market = m
                break
        
        if not market:
            return {"success": False, "error": "Market not found"}
        
        # Parse clobTokenIds
        token_ids = market.get('clobTokenIds', '[]')
        try:
            token_ids = json.loads(token_ids) if isinstance(token_ids, str) else token_ids
        except:
            token_ids = []
        
        token_id = token_ids[0] if token_ids else None
        if not token_id:
            return {"success": False, "error": "Token ID not found"}
        
        from py_clob_client.clob_types import OrderArgs
        
        # Use price as yes_price or (1 - no_price)
        price = yes_price if side.upper() == "YES" else (1 - yes_price)
        
        # Convert YES/NO to BUY/SELL
        order_side = "BUY" if side.upper() == "YES" else "SELL"
        
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=amount,
            side=order_side
        )
        
        result = client.create_order(order_args)
        
        return {"success": True, "order_id": str(result), "result": str(result)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def sync_trades_from_polymarket():
    """Sync trades from Polymarket API for the founder address"""
    if not POLY_API_KEY:
        return 0
    
    try:
        key = PRIVATE_KEY.replace("0x", "") if PRIVATE_KEY else None
        creds = ApiCreds(api_key=POLY_API_KEY, api_secret=POLY_API_SECRET, api_passphrase=POLY_API_PASSPHRASE)
        client = ClobClient(host=CLOB_HTTP_URL, chain_id=137, key=key, creds=creds)
        
        # Get ALL trade history from Polymarket with cursor
        all_trades = []
        cursor = None
        while True:
            if cursor:
                trades = client.get_trades(next_cursor=cursor)
            else:
                trades = client.get_trades()
            
            if not trades:
                break
            
            all_trades.extend(trades)
            
            # Check for more pages
            if hasattr(trades, 'next_cursor') and trades.next_cursor:
                cursor = trades.next_cursor
            else:
                break
        
        if not all_trades:
            return 0
        
        # Fetch multiple pages of markets to build complete map
        market_map = {}
        category_map = {}
        
        for offset in [0, 200, 400, 600, 800]:
            try:
                markets = get_markets(limit=200, offset=offset)
                for m in markets:
                    cid = m.get('conditionId') or m.get('id')
                    market_map[cid] = m.get('question', 'Unknown')
                    category_map[cid] = m.get('groupItemTitle', 'Other')
            except:
                pass
        
        # Map market names to trades
        result = []
        for t in all_trades:
            if isinstance(t, dict):
                market_id = t.get('market', '')
                market_name = market_map.get(market_id, 'Unknown')
                category = category_map.get(market_id, 'Other')
                
                # Try to get market name from assets endpoint if not found
                if market_name == 'Unknown':
                    asset_id = t.get('asset_id', '')
                    if asset_id:
                        try:
                            # Try gamma API with asset_id
                            import requests as req
                            r = req.get(f"https://gamma-api.polymarket.com/markets?clobTokenIds={asset_id}")
                            if r.status_code == 200:
                                data = r.json()
                                if data:
                                    market_name = data[0].get('question', 'Unknown')
                                    category = data[0].get('groupItemTitle', 'Other')
                        except:
                            pass
                
                result.append({
                    "id": t.get('id', ''),
                    "market": market_name,
                    "market_id": market_id,
                    "category": category,
                    "side": t.get('side', ''),
                    "size": float(t.get('size', 0)),
                    "price": float(t.get('price', 0)),
                    "total": float(t.get('size', 0)) * float(t.get('price', 0)),
                    "status": t.get('status', ''),
                    "time": t.get('match_time', ''),
                    "outcome": t.get('outcome', '')
                })
        
        # Save to local file
        trades_file = Path(__file__).parent / "trades" / "polymarket_trades.json"
        trades_file.parent.mkdir(exist_ok=True)
        
        with open(trades_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return len(result) if result else 0
        
    except Exception as e:
        print(f"Error syncing trades: {e}")
        return 0


# JSON API output for external UI
def to_json(data):
    return json.dumps(data, indent=2)


# Test endpoints
if __name__ == "__main__":
    print("=== Balances ===")
    print(to_json(get_balances()))
    
    print("\n=== Trade History ===")
    print(to_json(get_trade_history())[:1000])
