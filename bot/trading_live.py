"""
Live Trading Bot - Real-time High Probability Trading
- Fetch live markets from Polymarket
- Auto-detect high probability (>70% or <30%)
- Execute trades (simulate mode or real trading)
- Compound betting with risk management
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.market import fetch_markets, get_current_price
from bot.config import Config
from bot.auth import load_wallet
from bot.trading import execute_trade

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

def get_category(question, group=''):
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

class LiveTradingBot:
    def __init__(self, initial_balance=100.0, min_prob=0.70, max_consecutive_losses=5,
                 base_bet_pct=0.1, simulate=True, min_volume=1000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.min_prob = min_prob
        self.max_consecutive_losses = max_consecutive_losses
        self.base_bet_pct = base_bet_pct
        self.simulate = simulate
        self.min_volume = min_volume
        
        self.trades = []
        self.daily_stats = []
        self.consecutive_losses = 0
        self.consecutive_losses_today = 0
        self.total_wins = 0
        self.total_losses = 0
        self.daily_trades = 0
        self.stopped_today = False
        self.current_day = datetime.now().day
        
        self.log_folder = Path("simulation")
        self.log_folder.mkdir(exist_ok=True)
    
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
        """Log trade ke file dengan struktur /simulation/tanggal-bulan-tahun/jam/menit.txt"""
        now = datetime.now()
        # Create path: simulation/DD-MM-YYYY/HH/MM.txt
        date_str = now.strftime('%d-%m-%Y')
        hour_str = now.strftime('%H')
        minute_str = now.strftime('%M')
        
        log_path = self.log_folder / date_str / hour_str
        log_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{minute_str}.txt"
        with open(log_path / filename, "a") as f:
            sim_id = f" #{trade.get('simulation_id', '')}" if trade.get('simulation_id') is not None and trade.get('simulation_id') != "" else ""
            # Format the trade as a nice string instead of printing the dict
            trade_str = f"{trade['action']} {trade['odds']}x | Bet: ${trade['bet_size']:.2f} | {trade['result']} | Profit: ${trade['profit']:.2f} | Balance: ${trade['balance']:.2f} | Category: {trade['category']} | URL: {trade['url']}"
            f.write(f"[{now.strftime('%H:%M:%S')}{sim_id}] {trade_str}\n")
    
    def execute_trade(self, market, bet_size, action, odds, simulation_id=None):
        """Execute trade (simulate atau real)"""
        if self.should_stop() or self.stopped_today:
            return None
        
        if bet_size > self.balance:
            bet_size = self.balance
        
        prob = market['prob']
        
        if self.simulate:
            won = True
        else:
            print(f"   ⚠️ REAL TRADING NOT IMPLEMENTED - Skipping")
            return None
        
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
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'question': market['question'],
            'category': market['category'],
            'action': action,
            'prob': f"{prob*100:.1f}%",
            'odds': odds,
            'bet_size': bet_size,
            'profit': profit,
            'balance': self.balance,
            'result': result,
            'url': market.get('url', ''),
            'simulation_id': simulation_id
        }
        
        self.trades.append(trade)
        
        # Prepare trade dict with simulation_id for logging
        trade_for_logging = trade.copy()
        trade_for_logging['simulation_id'] = simulation_id
        self.log_trade(trade_for_logging)
        
        return trade
    
    def new_day(self):
        """Mulai hari baru"""
        day = datetime.now().day
        if day != self.current_day:
            self.daily_stats.append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'balance': self.balance,
                'trades': self.daily_trades,
                'wins': self.total_wins,
                'stopped': self.stopped_today
            })
            self.current_day = day
            self.daily_trades = 0
            self.consecutive_losses_today = 0
            self.stopped_today = False


def scan_and_trade(bot, min_volume=1000, simulation_id=None):
    """Scan markets dan execute trades"""
    print(f"\n📥 Scanning markets...")
    markets = fetch_markets(closed=False, limit=100)
    
    high_prob_opportunities = []
    
    for m in markets:
        prices = get_current_price(m)
        if not prices:
            continue
        
        vol = float(m.get('volume', 0))
        if vol < min_volume:
            continue
        
        prob = prices['mid_price']
        
        if prob >= bot.min_prob:
            action = 'YES'
            entry_prob = prob
            odds = get_odds(prob)
        elif prob <= (1 - bot.min_prob):
            action = 'NO'
            entry_prob = 1 - prob
            odds = get_odds(1 - prob)
        else:
            continue
        
        cat = get_category(m.get('question', ''), m.get('groupItemTitle', ''))
        
        high_prob_opportunities.append({
            'id': m['id'],
            'question': m.get('question', '')[:50],
            'category': cat,
            'volume': vol,
            'prob': prob,
            'action': action,
            'odds': odds,
            'url': f"https://polymarket.com/market/{m.get('slug', m['id'])}"
        })
    
    print(f"   Found {len(high_prob_opportunities)} high probability opportunities")
    
    if not high_prob_opportunities:
        print("   ❌ No opportunities found")
        return
    
    print(f"\n🎯 TOP OPPORTUNITIES:")
    print(f"   {'#':<3} {'Question':<30} {'Prob':<6} {'Odds':<6} {'Vol':<12} {'URL'}")
    print("   " + "-"*90)
    
    sorted_opps = sorted(high_prob_opportunities, key=lambda x: x['volume'], reverse=True)
    for i, opp in enumerate(sorted_opps[:10], 1):
        question_truncated = opp['question'][:30]
        url_short = opp['url'][-30:] if len(opp['url']) > 30 else opp['url']
        print(f"   {i:<3} {question_truncated:<30} {opp['prob']*100:>5.1f}%   {opp['odds']:.2f}x   ${opp['volume']:>10,.0f}   {url_short}")
    
    print(f"\n🚀 EXECUTING TRADES (Simulate: {bot.simulate})")
    print(f"   Current Balance: ${bot.balance:.2f}")
    
    if bot.stopped_today:
        print("   ⚠️ STOPPED - Max consecutive losses reached today")
        return
    
    trades_executed = 0
    
    for opp in sorted_opps[:10]:
        if bot.should_stop() or bot.stopped_today:
            break
        
        bet_size = bot.calculate_bet_size()
        
        trade = bot.execute_trade(opp, bet_size, opp['action'], opp['odds'], simulation_id=simulation_id)
        
        if trade:
            trades_executed += 1
            result_icon = "✅" if trade['result'] == "WIN" else "❌"
            print(f"   {result_icon} {trade['action']} {trade['odds']}x | Bet: ${trade['bet_size']:.2f} | Profit: ${trade['profit']:.2f}")
    
    print(f"\n   ✅ Executed {trades_executed} trades")
    print(f"   💰 Balance: ${bot.balance:.2f}")


def get_last_balance():
    """Get the last balance from simulation summary"""
    sim_path = Path("simulation")
    if not sim_path.exists():
        return None
    
    today_str = datetime.now().strftime('%d-%m-%Y')
    summary_path = sim_path / today_str / "summary.txt"
    
    if not summary_path.exists():
        return None
    
    try:
        with open(summary_path, 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                # Parse: "Simulation #X completed at HH:MM:SS - Balance: $Y.YY"
                import re
                match = re.search(r'Balance: \$([\d.]+)', last_line)
                if match:
                    return float(match.group(1))
    except:
        pass
    
    return None


def run_live_trading(balance=100.0, min_prob=0.70, max_losses=5, 
                      bet_pct=0.1, simulate=True, loop=False, interval=60):
    """Run live trading"""
    
    print("\n" + "="*80)
    print("🤖 POLYMARKET LIVE TRADING BOT".center(80))
    print("="*80)
    
    # Check for existing balance to continue
    last_balance = get_last_balance()
    if last_balance and loop:
        balance = last_balance
        print(f"\n📊 Continuing from previous balance: ${balance:.2f}")
    else:
        print(f"\n📊 CONFIG:")
        print(f"   Initial Balance: ${balance}")
    
    print(f"   Min Probability: {min_prob*100}%")
    print(f"   Max Consecutive Losses: {max_losses}")
    print(f"   Base Bet: {bet_pct*100}% of balance")
    print(f"   Mode: {'SIMULATE' if simulate else 'REAL'}")
    
    bot = LiveTradingBot(
        initial_balance=balance,
        min_prob=min_prob,
        max_consecutive_losses=max_losses,
        base_bet_pct=bet_pct,
        simulate=simulate
    )
    
    # Override balance with loaded one if continuing
    if last_balance and loop:
        bot.balance = balance
    
    if loop:
        print(f"\n🔄 Running in loop mode (Ctrl+C to stop)...")
        print(f"   Scan interval: {interval} seconds\n")
        
        scan_count = 0
        today_str = datetime.now().strftime('%d-%m-%Y')
        
        while True:
            try:
                scan_count += 1
                scan_and_trade(bot, simulation_id=scan_count)
                # Update summary file
                summary_path = bot.log_folder / today_str / "summary.txt"
                summary_path.parent.mkdir(parents=True, exist_ok=True)
                with open(summary_path, "a") as f:
                    f.write(f"Simulation #{scan_count} completed at {datetime.now().strftime('%H:%M:%S')} - Balance: ${bot.balance:.2f}\n")
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n👋 Stopped")
                break
    else:
        scan_and_trade(bot, simulation_id=None)
    
    print(f"\n{'='*80}")
    print("📈 SESSION SUMMARY".center(80))
    print(f"{'='*80}")
    print(f"   Total Trades: {len(bot.trades)}")
    print(f"   Wins: {bot.total_wins}")
    print(f"   Losses: {bot.total_losses}")
    print(f"   Final Balance: ${bot.balance:.2f}")
    print(f"   Profit: ${bot.balance - balance:.2f}")


def main():
    parser = argparse.ArgumentParser(description='Polymarket Live Trading Bot')
    parser.add_argument('--balance', type=float, default=100.0, help='Initial balance')
    parser.add_argument('--min-prob', type=float, default=0.70, help='Min probability threshold')
    parser.add_argument('--max-losses', type=int, default=5, help='Max consecutive losses')
    parser.add_argument('--bet-pct', type=float, default=0.1, help='Bet as %% of balance')
    parser.add_argument('--simulate', action='store_true', default=True, help='Simulate mode (default: True)')
    parser.add_argument('--real', action='store_true', help='Use real trading (not recommended)')
    parser.add_argument('--loop', action='store_true', help='Run in loop mode')
    parser.add_argument('--interval', type=int, default=60, help='Loop interval in seconds')
    parser.add_argument('--min-vol', type=float, default=1000, help='Min volume')
    
    args = parser.parse_args()
    
    simulate = not args.real
    
    if args.real:
        print("⚠️ WARNING: Real trading mode not implemented yet!")
        return
    
    run_live_trading(
        balance=args.balance,
        min_prob=args.min_prob,
        max_losses=args.max_losses,
        bet_pct=args.bet_pct,
        simulate=simulate,
        loop=args.loop,
        interval=args.interval
    )

if __name__ == "__main__":
    main()