import os
import sys
import time
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from bot.config import Config, logger
from bot.auth import load_wallet, get_account_info
from bot.market import fetch_markets, fetch_order_book, get_current_price, fetch_active_markets
from bot.risk import initialize_risk, can_trade, calculate_position_size, record_trade, get_risk_stats
from bot.trading import execute_trade

def analyze_market(market: dict) -> dict:
    prices = get_current_price(market)
    if not prices:
        return None
    
    bid = prices["best_bid"]
    ask = prices["best_ask"]
    mid = prices["mid_price"]
    spread = prices["spread"]
    
    signal = {
        "market_id": market["id"],
        "question": market.get("question", "Unknown"),
        "bid": bid,
        "ask": ask,
        "mid_price": mid,
        "spread": spread,
        "action": "HOLD",
        "confidence": 0.0,
        "reason": ""
    }
    
    vol = market.get("volume", "0")
    try:
        volume = float(vol) if isinstance(vol, str) else vol
    except:
        volume = 0
    
    if volume < 10000:
        signal["reason"] = "Low volume"
        return signal
    
    if mid < Config.DEFAULT_MIN_PROBABILITY:
        signal["action"] = "BUY"
        signal["confidence"] = 1.0 - mid
        signal["reason"] = f"Probability {mid:.2%} below min threshold"
    elif mid > Config.DEFAULT_MAX_PROBABILITY:
        signal["action"] = "SELL"
        signal["confidence"] = mid
        signal["reason"] = f"Probability {mid:.2%} above max threshold"
    else:
        signal["reason"] = "Probability in normal range"
    
    return signal
    
    if mid < Config.DEFAULT_MIN_PROBABILITY:
        signal["action"] = "BUY"
        signal["confidence"] = 1.0 - mid
        signal["reason"] = f"Probability {mid:.2%} below min threshold"
    elif mid > Config.DEFAULT_MAX_PROBABILITY:
        signal["action"] = "SELL"
        signal["confidence"] = mid
        signal["reason"] = f"Probability {mid:.2%} above max threshold"
    else:
        signal["reason"] = "Probability in normal range"
    
    return signal

def scan_and_trade(wallet_balance: float, dry_run: bool = True):
    logger.info("Scanning markets...")
    markets = fetch_active_markets(min_liquidity=10000)
    
    if not markets:
        logger.warning("No active markets found")
        return
    
    logger.info(f"Found {len(markets)} active markets")
    
    for market in markets[:10]:
        signal = analyze_market(market)
        if not signal:
            continue
        
        vol = market.get("volume", "0")
        try:
            volume = float(vol) if isinstance(vol, str) else vol
        except:
            volume = 0
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Market: {signal['question']}")
        logger.info(f"ID: {signal['market_id']}")
        logger.info(f"Bid: {signal['bid']:.4f} | Ask: {signal['ask']:.4f} | Mid: {signal['mid_price']:.4f}")
        logger.info(f"Spread: {signal['spread']:.4f}")
        logger.info(f"Action: {signal['action']} | Confidence: {signal['confidence']:.2%}")
        logger.info(f"Reason: {signal['reason']}")
        
        if signal["action"] == "HOLD":
            continue
        
        allowed, reason = can_trade()
        if not allowed:
            logger.warning(f"Cannot trade: {reason}")
            continue
        
        position_size = calculate_position_size(wallet_balance, signal["confidence"])
        
        if dry_run:
            logger.info(f"[DRY RUN] Would {signal['action']} ${position_size:.2f} at ${signal['mid_price']:.4f}")
        else:
            result = execute_trade(
                market_id=signal["market_id"],
                side=signal["action"],
                price=signal["mid_price"],
                size=position_size
            )
            if result and result.get("success"):
                record_trade(position_size * signal["mid_price"])
                logger.info(f"Trade executed successfully")
            else:
                logger.error(f"Trade failed: {result}")

def main():
    logger.info("="*60)
    logger.info("Polymarket Trading Bot - Python")
    logger.info("="*60)
    
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    scan_interval = int(os.getenv("SCAN_INTERVAL", "60"))
    
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    logger.info(f"Scan interval: {scan_interval} seconds")
    
    try:
        wallet = load_wallet()
        
        if wallet:
            account_info = get_account_info(wallet)
            balance = float(account_info.get("usdcBalance", "1000")) / 1e6
            logger.info(f"Wallet: {wallet.address}")
            logger.info(f"Balance: ${balance:.2f}")
        else:
            balance = 1000.0
            logger.info("No wallet loaded - using default balance for position sizing")
        
        initialize_risk(balance)
        
        logger.info("\nStarting market scan...")
        scan_and_trade(balance, dry_run=dry_run)
        
        logger.info("\n" + "="*60)
        logger.info("Risk Statistics:")
        stats = get_risk_stats()
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
