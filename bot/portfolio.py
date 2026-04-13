#!/usr/bin/env python3
"""
Polymarket Portfolio Dashboard
Cek balance, risk, pnl release, pnl floating, dan open positions
"""

import os
import sys
import requests
from datetime import datetime
from tabulate import tabulate

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.config import API_HEADERS, Config
from bot.auth import load_wallet


DATA_API_URL = "https://data-api.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"


def get_client():
    """Get authenticated CLOB client"""
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.constants import POLYGON
        from py_clob_client.clob_types import BalanceAllowanceParams
        
        private_key = os.getenv("PRIVATE_KEY", "")
        if not private_key:
            return None, 0.0
        
        client = ClobClient(
            host=CLOB_API_URL,
            key=private_key,
            chain_id=POLYGON,
        )
        
        client.set_api_creds(client.create_or_derive_api_creds())
        
        balance_result = client.get_balance_allowance(
            BalanceAllowanceParams(asset_type="COLLATERAL")
        )
        
        balance = float(balance_result.get("balance", "0")) / 1e6 if balance_result else 0.0
        
        return client, balance
    except Exception as e:
        print(f"   Warning: CLOB client error - {str(e)[:80]}")
        return None, 0.0


def get_trades_from_api(wallet_address: str, limit: int = 100) -> list:
    """Get trade history from Data API using address parameter"""
    try:
        url = f"{DATA_API_URL}/trades"
        params = {"address": wallet_address, "limit": limit}
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            processed_trades = []
            for t in data:
                # Use title directly from API, fallback to conditionId
                title = t.get("title", "N/A")
                condition_id = t.get("conditionId", "")
                
                processed_trades.append({
                    "market": condition_id,
                    "asset_id": t.get("asset_id", ""),
                    "title": title,
                    "slug": t.get("slug", ""),
                    "side": t.get("side", ""),
                    "outcome": t.get("outcome", ""),
                    "size": float(t.get("size", 0)),
                    "price": float(t.get("price", 0)),
                    "timestamp": t.get("timestamp", ""),
                    "transaction_hash": t.get("transactionHash", ""),
                })
            return processed_trades
    except Exception as e:
        print(f"   Error fetching trades: {e}")
    return []


def get_market_info(asset_id: str = None, condition_id: str = None, market_id: str = None, cached: dict = None) -> dict:
    """Get market info from Gamma API using asset_id, condition_id, or market_id"""
    if cached is None:
        cached = {}
    
    # Try cache first
    if asset_id and asset_id in cached:
        return cached[asset_id]
    if condition_id and condition_id in cached:
        return cached[condition_id]
    if market_id and market_id in cached:
        return cached[market_id]
    
    if not asset_id and not condition_id and not market_id:
        return {"question": "N/A", "condition_id": "", "market_id": ""}
    
    # Try asset_id first (clobTokenId) - most reliable
    if asset_id:
        try:
            url = f"{GAMMA_API_URL}/markets"
            params = {"clobTokenId": asset_id}
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    info = {
                        "question": data[0].get("question", "N/A"),
                        "condition_id": data[0].get("conditionId", ""),
                        "market_id": data[0].get("id", "")
                    }
                    cached[asset_id] = info
                    return info
        except:
            pass
    
    # Try market_id directly (the numeric ID like "540816")
    if market_id:
        try:
            url = f"{GAMMA_API_URL}/markets/{market_id}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                info = {
                    "question": data.get("question", "N/A"),
                    "condition_id": data.get("conditionId", ""),
                    "market_id": data.get("id", "")
                }
                cached[market_id] = info
                return info
        except:
            pass
    
    # Fallback: try conditionId
    if condition_id:
        try:
            url = f"{GAMMA_API_URL}/markets"
            params = {"conditionId": condition_id}
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    info = {
                        "question": data[0].get("question", "N/A"),
                        "condition_id": data[0].get("conditionId", ""),
                        "market_id": data[0].get("id", "")
                    }
                    cached[condition_id] = info
                    return info
        except:
            pass
    
    info = {"question": "N/A", "condition_id": "", "market_id": ""}
    if asset_id:
        cached[asset_id] = info
    if condition_id:
        cached[condition_id] = info
    if market_id:
        cached[market_id] = info
    return info


def get_positions_from_trades(trades: list, market_cache: dict = None) -> list:
    """Calculate open positions from trades"""
    if market_cache is None:
        market_cache = {}
    
    position_by_market = {}
    
    for t in trades:
        market = t.get("market", "")
        title = t.get("title", "")
        if not market:
            continue
        
        side = t.get("side", "").upper()
        size = t.get("size", 0)
        price = t.get("price", 0)
        
        if market not in position_by_market:
            position_by_market[market] = {
                "market": market,
                "title": title,
                "buys": [],
                "sells": [],
            }
        
        if side == "BUY":
            position_by_market[market]["buys"].append({"size": size, "price": price})
        else:
            position_by_market[market]["sells"].append({"size": size, "price": price})
    
    positions = []
    for market, data in position_by_market.items():
        total_buy = sum(b["size"] for b in data["buys"])
        total_sell = sum(s["size"] for s in data["sells"])
        
        avg_buy_price = sum(b["size"] * b["price"] for b in data["buys"]) / total_buy if total_buy > 0 else 0
        avg_sell_price = sum(s["size"] * s["price"] for s in data["sells"]) / total_sell if total_sell > 0 else 0
        
        net_qty = total_buy - total_sell
        
        # Get title from data
        title = data.get("title", market)
        
        if net_qty > 0:
            positions.append({
                "market": market,
                "title": title,
                "side": "BUY",
                "qty": net_qty,
                "avg_price": avg_buy_price,
                "cost": net_qty * avg_buy_price,
            })
        elif net_qty < 0:
            positions.append({
                "market": market,
                "title": title,
                "side": "SELL",
                "qty": abs(net_qty),
                "avg_price": avg_sell_price,
                "cost": abs(net_qty) * avg_sell_price,
            })
    
    return positions


def get_current_price(asset_id: str) -> float:
    """Get current price from order book"""
    if not asset_id:
        return 0.0
    try:
        url = f"{CLOB_API_URL}/book"
        params = {"token_id": asset_id}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            if bids:
                return float(bids[0].get("price", 0))
            elif asks:
                return float(asks[0].get("price", 0))
    except:
        pass
    return 0.0


def calculate_pnl(trades: list, market_cache: dict = None) -> tuple[float, float, float, list]:
    """Calculate PnL from trades"""
    if market_cache is None:
        market_cache = {}
    
    total_cost = 0.0
    total_value = 0.0
    total_fees = 0.0
    
    trade_by_market = {}
    for t in trades:
        market = t.get("market", "")
        if not market:
            continue
        
        title = t.get("title", "")
        
        if market not in trade_by_market:
            trade_by_market[market] = {"buys": [], "sells": [], "title": title}
        
        side = t.get("side", "").upper()
        size = t.get("size", 0)
        price = t.get("price", 0)
        fee_rate = t.get("fee", 0)
        
        trade_value = size * price
        fee = trade_value * fee_rate
        total_fees += fee
        
        if side == "BUY":
            trade_by_market[market]["buys"].append({"size": size, "price": price, "fee": fee})
            total_cost += trade_value
        else:
            trade_by_market[market]["sells"].append({"size": size, "price": price, "fee": fee})
            total_value += trade_value
    
    market_summaries = []
    for market, data in trade_by_market.items():
        buy_cost = sum(b["size"] * b["price"] for b in data["buys"])
        sell_value = sum(s["size"] * s["price"] for s in data["sells"])
        
        # Use title directly from trade data if available
        market_name = data.get("title", market)[:35] if data.get("title") else market[:35]
        
        market_summaries.append({
            "market": market_name,
            "buys": len(data["buys"]),
            "sells": len(data["sells"]),
            "cost": buy_cost,
            "value": sell_value,
            "pnl": sell_value - buy_cost
        })
    
    realized_pnl = total_value - total_cost - total_fees
    
    return realized_pnl, total_cost, total_fees, market_summaries


def get_risk_info() -> dict:
    """Get risk info from config"""
    return {
        "max_daily_loss": f"{Config.MAX_DAILY_LOSS * 100:.1f}%",
        "max_position": f"{Config.MAX_POSITION_SIZE * 100:.1f}%",
        "stop_loss": f"{Config.STOP_LOSS_PERCENTAGE * 100:.1f}%",
        "max_consecutive_losses": Config.MAX_CONSECUTIVE_LOSSES,
    }


def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:,.2f}"


def main():
    print("\n" + "=" * 85)
    print("📊 POLYMARKET PORTFOLIO DASHBOARD".center(85))
    print("=" * 85 + "\n")
    
    wallet = load_wallet()
    
    if not wallet:
        print("❌ No wallet loaded. Please check your PRIVATE_KEY in .env")
        return
    
    wallet_address = wallet.address
    
    print(f"👤 Wallet: {wallet_address}")
    print(f"🌐 View: https://polymarket.com/portfolio\n")
    
    print("-" * 85)
    
    # Get balance and trades from Data API
    client, balance = get_client()
    trades = get_trades_from_api(wallet_address, limit=100)
    risk_info = get_risk_info()
    
    market_cache = {}
    realized_pnl, total_cost, total_fees, market_summaries = calculate_pnl(trades, market_cache)
    positions = get_positions_from_trades(trades, market_cache)
    
    total_pnl = balance - 1000 + realized_pnl
    
    print(f"\n💰 BALANCE")
    print(f"   USDC Balance:        {format_currency(balance)}")
    
    print(f"\n⚠️  RISK SETTINGS")
    print(f"   Max Daily Loss:      {risk_info['max_daily_loss']}")
    print(f"   Max Position Size:   {risk_info['max_position']}")
    print(f"   Stop Loss:           {risk_info['stop_loss']}")
    print(f"   Max Consecutive:     {risk_info['max_consecutive_losses']} trades")
    
    print(f"\n📈 PnL SUMMARY")
    print(f"   Total Cost:          {format_currency(total_cost)}")
    print(f"   Total Sales:        {format_currency(sum(m['value'] for m in market_summaries))}")
    print(f"   Total Fees:         {format_currency(total_fees)}")
    print(f"   Realized PnL:       {format_currency(realized_pnl)}")
    print(f"   Total PnL:          {format_currency(total_pnl)}")
    
    print(f"\n📋 OPEN POSITIONS ({len(positions)} open)")
    print("-" * 85)
    
    if positions:
        table_data = []
        for p in positions:
            # Use title directly if available
            market_name = p.get("title", p.get("market", "N/A"))[:40]
            table_data.append([
                market_name,
                p["side"],
                f"{p['qty']:.2f}",
                f"${p['avg_price']:.4f}",
                f"${p['cost']:.2f}"
            ])
        
        print(tabulate(table_data,
            headers=["Market", "Side", "Qty", "Avg Price", "Cost"],
            tablefmt="simple",
            maxcolwidths=[40, 5, 10, 12, 12]
        ))
    else:
        print("   📭 No open positions")
    
    print(f"\n📜 TRADE HISTORY ({len(trades)} trades)")
    print("-" * 85)
    
    if trades:
        table_data = []
        for t in trades[:20]:
            market_id = t.get("market", "")
            side = t.get("side", "")
            size = t.get("size", 0)
            price = t.get("price", 0)
            
            table_data.append([
                f"...{market_id[:8]}",
                side,
                f"{size:.2f}",
                f"${price:.4f}"
            ])
        
        print(tabulate(table_data,
            headers=["Market ID", "Side", "Size", "Price"],
            tablefmt="simple",
            maxcolwidths=[12, 5, 10, 12]
        ))
    else:
        print("   📭 No trade history")
    
    print(f"\n📊 SUMMARY BY MARKET ({len(market_summaries)} markets)")
    print("-" * 85)
    
    if market_summaries:
        table_data = []
        for m in market_summaries:
            table_data.append([
                m["market"],
                m["buys"],
                m["sells"],
                f"${m['cost']:.2f}",
                f"${m['value']:.2f}",
                f"${m['pnl']:.2f}"
            ])
        
        print(tabulate(table_data,
            headers=["Market", "Buys", "Sells", "Cost", "Value", "PnL"],
            tablefmt="simple",
            maxcolwidths=[35, 5, 5, 12, 12, 12]
        ))
    
    print("\n" + "=" * 85)
    print(f"🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    main()