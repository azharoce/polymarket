#!/usr/bin/env python3
"""
Polymarket AutoBet Bot
- Connect to Polymarket CLOB API
- Auto-detect high probability markets (>70% or <30%)
- Execute real trades on Polymarket
- Risk management included
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from pathlib import Path
from decimal import Decimal

import requests
from dotenv import load_dotenv
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.exceptions import PolyApiException

load_dotenv()

POLYGON_RPC_URL = os.getenv("RPC_URL", "https://polygon-rpc.com")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
FUNDER_ADDRESS = os.getenv("FUNDER_ADDRESS", "")
POLY_API_KEY = os.getenv("POLY_API_KEY", "")
POLY_API_SECRET = os.getenv("POLY_API_SECRET", "")
POLY_API_PASSPHRASE = os.getenv("POLY_API_PASSPHRASE", "")
CLOB_HTTP_URL = "https://clob.polymarket.com"
USDC_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

CATEGORIES = {
    "Sports": ["NHL", "NBA", "NFL", "FIFA", "World Cup", "Stanley Cup", "Finals", "win the"],
    "Politics": ["President", "election", "Trump", "Biden", "Congress", "Senate", "Governor"],
    "Crypto": ["Bitcoin", "Ethereum", "BTC", "ETH", "Solana"],
    "Economy": ["GDP", "inflation", "recession", "Fed", "interest rate"],
    "Tech": ["AI", "Apple", "Google", "Microsoft", "Tesla"],
    "Culture": ["album", "movie", "Rihanna", "Carti", "GTA"],
    "Weather": ["hurricane", "earthquake", "storm", "weather"],
    "Esports": ["Dota", "League", "CSGO", "esports", "gaming"]
}

MIN_BET = 1.0
API_HEADERS = {"Content-Type": "application/json"}


def get_category(question, group=""):
    q = question.lower()
    g = group.lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw.lower() in q or kw.lower() in g for kw in keywords):
            return cat
    return "Other"


def get_odds(prob):
    """Hitung odds berdasarkan probabilitas"""
    if prob >= 0.95:
        return 1.05
    elif prob >= 0.90:
        return 1.15
    elif prob >= 0.85:
        return 1.25
    elif prob >= 0.80:
        return 1.35
    elif prob >= 0.75:
        return 1.45
    elif prob >= 0.70:
        return 1.60
    else:
        return 2.00


def load_wallet() -> LocalAccount:
    """Load wallet dari private key"""
    if not PRIVATE_KEY:
        print("❌ PRIVATE_KEY not found in .env")
        return None
    
    key_without_prefix = PRIVATE_KEY.replace("0x", "")
    
    if len(key_without_prefix) != 64:
        print(f"❌ PRIVATE_KEY invalid length: {len(key_without_prefix)} (should be 64)")
        return None
    
    try:
        account: LocalAccount = Account.from_key(key_without_prefix)
        print(f"✅ Wallet loaded: {account.address}")
        return account
    except Exception as e:
        print(f"❌ Failed to load wallet: {e}")
        return None


def get_client(wallet: "LocalAccount" = None):
    """Create CLOB client"""
    try:
        key_str = None
        if wallet:
            key_str = wallet.key.hex()
        
        if key_str and POLY_API_KEY and POLY_API_SECRET:
            from py_clob_client.clob_types import ApiCreds
            creds = ApiCreds(
                api_key=POLY_API_KEY,
                api_secret=POLY_API_SECRET,
                api_passphrase=POLY_API_PASSPHRASE
            )
            client = ClobClient(
                host=CLOB_HTTP_URL,
                chain_id=137,
                key=key_str,
                creds=creds
            )
        elif key_str:
            client = ClobClient(
                host=CLOB_HTTP_URL,
                chain_id=137,
                key=key_str
            )
        else:
            client = ClobClient(host=CLOB_HTTP_URL, chain_id=137)
        
        print(f"✅ CLOB Client connected to {CLOB_HTTP_URL}")
        return client
    except Exception as e:
        print(f"❌ Failed to create CLOB client: {e}")
        return None


GAMMA_API_URL = "https://gamma-api.polymarket.com"


def fetch_markets(closed="false", limit=100):
    """Fetch markets dari Polymarket Gamma API (has volume data)"""
    try:
        url = f"{GAMMA_API_URL}/markets"
        params = {
            "closed": closed,
            "limit": limit,
            "active": "true"
        }
        
        response = requests.get(url, params=params, headers=API_HEADERS, timeout=30)
        markets = response.json()
        
        return markets
    except Exception as e:
        print(f"❌ Failed to fetch markets: {e}")
        return []


def get_current_price(client, market):
    """Get current price dari Gamma API market data"""
    try:
        outcome_prices = market.get("outcomePrices", [])
        
        if isinstance(outcome_prices, str):
            outcome_prices = json.loads(outcome_prices)
        
        if not outcome_prices or len(outcome_prices) < 2:
            return None
        
        yes_price = float(outcome_prices[0])
        no_price = float(outcome_prices[1])
        
        mid_price = (yes_price + no_price) / 2
        
        return {
            "bid": yes_price,
            "ask": no_price,
            "mid_price": mid_price,
            "yes_price": yes_price,
            "no_price": no_price
        }
    except Exception as e:
        return None


def get_token_ids(client, market_id):
    """Get token IDs untuk market"""
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        response = requests.get(url, headers=API_HEADERS, timeout=30)
        market = response.json()
        
        clob_token_ids = market.get("clobTokenIds", "[]")
        if isinstance(clob_token_ids, str):
            token_ids = json.loads(clob_token_ids)
        else:
            token_ids = clob_token_ids
        
        return {
            "yes_token_id": token_ids[0] if len(token_ids) > 0 else None,
            "no_token_id": token_ids[1] if len(token_ids) > 1 else None
        }
    except Exception as e:
        print(f"❌ Failed to get token IDs: {e}")
        return {"yes_token_id": None, "no_token_id": None}


def execute_real_trade(client, wallet, market_id, token_id, side, price, size):
    """Execute real trade di Polymarket"""
    try:
        order_args = OrderArgs(
            token_id=token_id,
            side=side,
            price=price,
            size=size
        )
        
        response = client.create_order(order_args)
        print(f"   ✅ Order placed: {response}")
        return {"success": True, "result": response}
    except PolyApiException as e:
        print(f"   ❌ PolyApi error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"   ❌ Trade error: {e}")
        return {"success": False, "error": str(e)}


def get_balance(client, wallet):
    """Get USDC balance"""
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
        
        usdc_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT),
            abi=usdc_abi
        )
        
        balance = usdc_contract.functions.balanceOf(wallet.address).call()
        return balance / 1e6
    except Exception as e:
        print(f"⚠️ Could not fetch balance: {e}")
        return 0.0


class AutoBetBot:
    def __init__(self, initial_balance=100.0, min_prob=0.70, max_consecutive_losses=5,
                 base_bet_pct=0.1, simulate=True, min_volume=1000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.min_prob = min_prob
        self.max_consecutive_losses = max_consecutive_losses
        self.base_bet_pct = base_bet_pct
        self.simulate = simulate
        self.min_volume = min_volume
        
        self.client = None
        self.wallet = None
        self.trades = []
        self.consecutive_losses = 0
        self.consecutive_losses_today = 0
        self.total_wins = 0
        self.total_losses = 0
        self.daily_trades = 0
        self.stopped_today = False
        self.current_day = datetime.now().day
        
        self.log_folder = Path("autobet_logs")
        self.log_folder.mkdir(exist_ok=True)
    
    def initialize(self):
        """Initialize wallet dan client"""
        self.wallet = load_wallet()
        self.client = get_client(self.wallet)
        
        if not self.simulate:
            if not self.wallet:
                print("❌ Cannot run real trading without valid wallet")
                return False
            
            if not self.client:
                print("❌ Cannot connect to CLOB API")
                return False
            
            balance = get_balance(self.client, self.wallet)
            print(f"   💰 USDC Balance: ${balance:.2f}")
            self.balance = balance if balance > 0 else self.initial_balance
        
        return True
    
    def calculate_bet_size(self):
        """Hitung besar bet berdasarkan balance"""
        base_size = self.balance * self.base_bet_pct
        bet_size = max(base_size, MIN_BET)
        
        if self.balance >= self.initial_balance * 2:
            return bet_size * 2
        elif self.balance >= self.initial_balance * 1.5:
            return bet_size * 1.5
        else:
            return bet_size
    
    def should_stop(self):
        """Cek apakah harus stop"""
        return self.consecutive_losses_today >= self.max_consecutive_losses
    
    def log_trade(self, trade):
        """Log trade ke file"""
        now = datetime.now()
        date_str = now.strftime('%d-%m-%Y')
        hour_str = now.strftime('%H')
        
        log_path = self.log_folder / date_str / hour_str
        log_path.mkdir(parents=True, exist_ok=True)
        
        minute_str = now.strftime('%M')
        filename = f"{minute_str}.txt"
        
        with open(log_path / filename, "a") as f:
            sim_id = f" #{trade.get('simulation_id', '')}" if trade.get('simulation_id') else ""
            trade_str = f"{trade['action']} {trade['odds']}x | Bet: ${trade['bet_size']:.2f} | {trade['result']} | Profit: ${trade['profit']:.2f} | Balance: ${trade['balance']:.2f}"
            f.write(f"[{now.strftime('%H:%M:%S')}{sim_id}] {trade_str}\n")
    
    def execute_trade(self, market, bet_size, action, odds, simulation_id=None):
        """Execute trade (simulate atau real)"""
        if self.should_stop() or self.stopped_today:
            return None
        
        if bet_size > self.balance:
            bet_size = self.balance
        
        prob = market["prob"]
        market_id = market["id"]
        
        if self.simulate:
            won = True
        else:
            try:
                token_ids = get_token_ids(self.client, market_id)
                token_id = token_ids["yes_token_id"] if action == "YES" else token_ids["no_token_id"]
                
                if not token_id:
                    print(f"   ❌ No token ID for {action}")
                    return None
                
                price = prob if action == "YES" else (1 - prob)
                result = execute_real_trade(
                    self.client, self.wallet, market_id, token_id,
                    "BUY" if action == "YES" else "SELL",
                    price, bet_size
                )
                
                won = result.get("success", False)
                
                if not won:
                    print(f"   ❌ Trade failed: {result.get('error')}")
                    return None
                    
            except Exception as e:
                print(f"   ❌ Trade error: {e}")
                won = False
        
        if won:
            profit = bet_size * (odds - 1)
            self.balance += profit
            self.consecutive_losses = 0
            self.total_wins += 1
            self.daily_trades += 1
            result = "WIN"
        else:
            profit = -bet_size
            self.balance -= bet_size
            self.consecutive_losses += 1
            self.consecutive_losses_today += 1
            self.total_losses += 1
            self.daily_trades += 1
            result = "LOSE"
            
            if self.consecutive_losses_today >= self.max_consecutive_losses:
                self.stopped_today = True
        
        trade = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "question": market["question"],
            "category": market["category"],
            "action": action,
            "prob": f"{prob*100:.1f}%",
            "odds": odds,
            "bet_size": bet_size,
            "profit": profit,
            "balance": self.balance,
            "result": result,
            "url": market.get("url", ""),
            "simulation_id": simulation_id
        }
        
        self.trades.append(trade)
        
        trade_for_logging = trade.copy()
        trade_for_logging["simulation_id"] = simulation_id
        self.log_trade(trade_for_logging)
        
        return trade
    
    def new_day(self):
        """Mulai hari baru"""
        day = datetime.now().day
        if day != self.current_day:
            self.current_day = day
            self.daily_trades = 0
            self.consecutive_losses_today = 0
            self.stopped_today = False


def scan_and_trade(bot, min_volume=1000, simulation_id=None):
    """Scan markets dan execute trades"""
    print(f"\n📥 Scanning markets...")
    markets = fetch_markets(closed=False, limit=100)
    
    if not markets:
        print("   ❌ No markets found")
        return
    
    high_prob_opportunities = []
    
    for m in markets:
        prices = get_current_price(bot.client, m) if bot.client else None
        
        if not prices:
            continue
        
        vol = float(m.get("volume24hr", m.get("volume", 0)))
        if vol < min_volume:
            continue
        
        yes_price = prices["yes_price"]
        no_price = prices["no_price"]
        
        if yes_price >= bot.min_prob:
            action = "YES"
            prob = yes_price
            odds = get_odds(prob)
        elif no_price >= bot.min_prob:
            action = "NO"
            prob = no_price
            odds = get_odds(prob)
        else:
            continue
        
        cat = get_category(m.get("question", ""), m.get("groupItemTitle", ""))
        
        high_prob_opportunities.append({
            "id": m.get("conditionId") or m.get("id"),
            "question": m.get("question", "")[:50],
            "category": cat,
            "volume": vol,
            "prob": prob,
            "action": action,
            "odds": odds,
            "url": f"https://polymarket.com/market/{m.get('slug', m.get('conditionId', m.get('id')))}"
        })
    
    print(f"   Found {len(high_prob_opportunities)} high probability opportunities")
    
    if not high_prob_opportunities:
        print("   ❌ No opportunities found")
        return
    
    print(f"\n🎯 TOP OPPORTUNITIES:")
    print(f"   {'#':<3} {'Question':<30} {'Prob':<6} {'Odds':<6} {'Vol':<12}")
    print("   " + "-" * 80)
    
    sorted_opps = sorted(high_prob_opportunities, key=lambda x: x["volume"], reverse=True)
    for i, opp in enumerate(sorted_opps[:10], 1):
        question_truncated = opp["question"][:30]
        print(f"   {i:<3} {question_truncated:<30} {opp['prob']*100:>5.1f}%   {opp['odds']:.2f}x   ${opp['volume']:>10,.0f}")
    
    print(f"\n🚀 EXECUTING TRADES (Mode: {'SIMULATE' if bot.simulate else 'REAL'})")
    print(f"   Current Balance: ${bot.balance:.2f}")
    
    if bot.stopped_today:
        print("   ⚠️ STOPPED - Max consecutive losses reached today")
        return
    
    trades_executed = 0
    
    for opp in sorted_opps[:10]:
        if bot.should_stop() or bot.stopped_today:
            break
        
        bet_size = bot.calculate_bet_size()
        
        trade = bot.execute_trade(opp, bet_size, opp["action"], opp["odds"], simulation_id=simulation_id)
        
        if trade:
            trades_executed += 1
            result_icon = "✅" if trade["result"] == "WIN" else "❌"
            print(f"   {result_icon} {trade['action']} {trade['odds']}x | Bet: ${trade['bet_size']:.2f} | Profit: ${trade['profit']:.2f}")
    
    print(f"\n   ✅ Executed {trades_executed} trades")
    print(f"   💰 Balance: ${bot.balance:.2f}")


def run_autobet(balance=100.0, min_prob=0.70, max_losses=5,
                bet_pct=0.1, simulate=True, loop=False, interval=60, min_vol=1000):
    """Run AutoBet bot"""
    
    print("\n" + "=" * 80)
    print("🤖 POLYMARKET AUTOBET BOT".center(80))
    print("=" * 80)
    
    print(f"\n📊 CONFIG:")
    print(f"   Initial Balance: ${balance}")
    print(f"   Min Probability: {min_prob*100}%")
    print(f"   Max Consecutive Losses: {max_losses}")
    print(f"   Base Bet: {bet_pct*100}% of balance")
    print(f"   Mode: {'SIMULATE' if simulate else 'REAL'}")
    
    bot = AutoBetBot(
        initial_balance=balance,
        min_prob=min_prob,
        max_consecutive_losses=max_losses,
        base_bet_pct=bet_pct,
        simulate=simulate,
        min_volume=min_vol
    )
    
    if not bot.initialize():
        return
    
    if loop:
        print(f"\n🔄 Running in loop mode (Ctrl+C to stop)...")
        print(f"   Scan interval: {interval} seconds\n")
        
        scan_count = 0
        
        while True:
            try:
                scan_count += 1
                scan_and_trade(bot, min_volume=min_vol, simulation_id=scan_count)
                
                today_str = datetime.now().strftime("%d-%m-%Y")
                summary_path = bot.log_folder / today_str / "summary.txt"
                summary_path.parent.mkdir(parents=True, exist_ok=True)
                with open(summary_path, "a") as f:
                    f.write(f"Run #{scan_count} at {datetime.now().strftime('%H:%M:%S')} - Balance: ${bot.balance:.2f}\n")
                
                bot.new_day()
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n👋 Stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(10)
    else:
        scan_and_trade(bot, min_volume=min_vol, simulation_id=None)
    
    print(f"\n{'='*80}")
    print("📈 SESSION SUMMARY".center(80))
    print(f"{'='*80}")
    print(f"   Total Trades: {len(bot.trades)}")
    print(f"   Wins: {bot.total_wins}")
    print(f"   Losses: {bot.total_losses}")
    print(f"   Final Balance: ${bot.balance:.2f}")
    print(f"   Profit: ${bot.balance - balance:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Polymarket AutoBet Bot")
    parser.add_argument("--balance", type=float, default=100.0, help="Initial balance")
    parser.add_argument("--min-prob", type=float, default=0.70, help="Min probability threshold")
    parser.add_argument("--max-losses", type=int, default=5, help="Max consecutive losses")
    parser.add_argument("--bet-pct", type=float, default=0.1, help="Bet as percentage of balance")
    parser.add_argument("--simulate", action="store_true", default=True, help="Simulate mode")
    parser.add_argument("--real", action="store_true", help="Use real trading")
    parser.add_argument("--loop", action="store_true", help="Run in loop mode")
    parser.add_argument("--interval", type=int, default=60, help="Loop interval in seconds")
    parser.add_argument("--min-vol", type=float, default=1000, help="Min volume")
    
    args = parser.parse_args()
    
    simulate = not args.real
    
    if args.real and not PRIVATE_KEY:
        print("❌ Cannot run real trading without PRIVATE_KEY in .env")
        print("   Add your private key to .env file")
        return
    
    run_autobet(
        balance=args.balance,
        min_prob=args.min_prob,
        max_losses=args.max_losses,
        bet_pct=args.bet_pct,
        simulate=simulate,
        loop=args.loop,
        interval=args.interval,
        min_vol=args.min_vol
    )


if __name__ == "__main__":
    main()
