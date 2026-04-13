import os
import time
import json
import requests
from eth_account import Account
from bot.config import API_HEADERS, Config, logger
from bot.auth import sign_order, load_wallet
from bot.market import fetch_order_book, get_current_price

def place_order(market_id: str, side: str, price: float, size: float, token_id: str, wallet: Account) -> dict:
    order_params = {
        "market_id": market_id,
        "side": side.upper(),
        "price": str(price),
        "size": str(size),
        "token_id": token_id,
        "nonce": str(int(time.time() * 1000))
    }
    
    signature = sign_order(order_params, wallet)
    
    url = f"{Config.API_BASE_URL}/orders"
    payload = {
        "order": order_params,
        "signature": signature
    }
    
    try:
        response = requests.post(url, headers=API_HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Order placed: {result}")
        return {"success": True, "result": result}
    except requests.RequestException as e:
        logger.error(f"Failed to place order: {e}")
        return {"success": False, "error": str(e)}

def execute_trade(market_id: str, side: str, price: float, size: float):
    """Execute a trade on Polymarket"""
    wallet = load_wallet()
    if not wallet:
        logger.error("No wallet loaded")
        return {"success": False, "error": "No wallet"}
    
    from bot.config import GAMMA_API_URL
    
    try:
        url = f"{GAMMA_API_URL}/markets/{market_id}"
        response = requests.get(url, headers=API_HEADERS)
        market = response.json()
        
        clob_token_ids = market.get("clobTokenIds", "[]")
        token_ids = json.loads(clob_token_ids)
        
        if side.upper() == "BUY":
            token_id = token_ids[0] if len(token_ids) > 0 else None
        else:
            token_id = token_ids[1] if len(token_ids) > 1 else None
        
        if not token_id:
            return {"success": False, "error": "No token ID"}
        
        result = place_order(market_id, side, price, size, token_id, wallet)
        return result
        
    except Exception as e:
        logger.error(f"Trade error: {e}")
        return {"success": False, "error": str(e)}

def buy_token(market_id: str, token_id: str, amount: float, wallet: Account):
    """Buy a specific token"""
    return place_order(market_id, "BUY", 0.5, amount, token_id, wallet)

def sell_token(market_id: str, token_id: str, amount: float, wallet: Account):
    """Sell a specific token"""
    return place_order(market_id, "SELL", 0.5, amount, token_id, wallet)
