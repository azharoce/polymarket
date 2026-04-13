import json
import requests
from bot.config import API_HEADERS, Config, logger

def fetch_markets(closed=False, archived=False, limit=100):
    url = f"{Config.GAMMA_API_URL}/markets"
    params = {
        "closed": str(closed).lower(),
        "archived": str(archived).lower(),
        "limit": limit
    }
    try:
        response = requests.get(url, headers=API_HEADERS, params=params)
        response.raise_for_status()
        markets = response.json()
        logger.info(f"Fetched {len(markets)} markets")
        return markets
    except requests.RequestException as e:
        logger.error(f"Failed to fetch markets: {e}")
        return []

def fetch_order_book(token_id: str):
    url = f"{Config.API_BASE_URL}/book"
    params = {"token_id": token_id}
    try:
        response = requests.get(url, headers=API_HEADERS, params=params)
        response.raise_for_status()
        order_book = response.json()
        return order_book
    except requests.RequestException as e:
        logger.error(f"Failed to fetch order book: {e}")
        return None

def get_market_details(market_id: str):
    url = f"{Config.GAMMA_API_URL}/markets/{market_id}"
    try:
        response = requests.get(url, headers=API_HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get market details: {e}")
        return None

def get_current_price(market: dict) -> dict:
    best_bid = market.get("bestBid")
    best_ask = market.get("bestAsk")
    
    if best_bid is None or best_ask is None:
        clob_token_ids_str = market.get("clobTokenIds", "")
        if not clob_token_ids_str:
            return None
        
        try:
            token_ids = json.loads(clob_token_ids_str)
        except:
            return None
        
        yes_token_id = token_ids[0] if len(token_ids) > 0 else None
        
        if yes_token_id:
            yes_book = fetch_order_book(yes_token_id)
            if not yes_book:
                return None
            
            bids = yes_book.get("bids", [])
            asks = yes_book.get("asks", [])
            best_bid = float(bids[0]["price"]) if bids else 0.0
            best_ask = float(asks[0]["price"]) if asks else 1.0
        else:
            return None
    else:
        best_bid = float(best_bid)
        best_ask = float(best_ask)
    
    clob_token_ids_str = market.get("clobTokenIds", "")
    try:
        token_ids = json.loads(clob_token_ids_str) if clob_token_ids_str else []
    except:
        token_ids = []
    
    yes_token_id = token_ids[0] if len(token_ids) > 0 else None
    no_token_id = token_ids[1] if len(token_ids) > 1 else None
    
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": (best_bid + best_ask) / 2,
        "spread": best_ask - best_bid,
        "yes_token_id": yes_token_id,
        "no_token_id": no_token_id
    }

def fetch_active_markets(min_liquidity=10000):
    markets = fetch_markets(closed=False)
    active_markets = []
    
    for market in markets:
        vol = market.get("volume", "0")
        try:
            volume = float(vol) if isinstance(vol, str) else vol
        except:
            volume = 0
        
        if volume >= min_liquidity:
            active_markets.append(market)
    
    logger.info(f"Found {len(active_markets)} active markets with min liquidity ${min_liquidity}")
    return active_markets
