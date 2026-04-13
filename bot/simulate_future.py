import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.trading_utils import (
    BettingSession, filter_markets, get_high_probability_markets, 
    simulate_future_price, KEYWORDS, CATEGORIES
)
from bot.market import fetch_markets

SIMULATION_LOG_PATH = Path("simulation")
REAL_LOG_PATH = Path("trading")

def get_last_balance():
    """Load last balance from file"""
    balance_file = SIMULATION_LOG_PATH / "balance.txt"
    if balance_file.exists():
        try:
            with open(balance_file, 'r') as f:
                val = f.read().strip()
                if val:
                    return float(val)
        except:
            return None
    return None

def mark_stopping():
    """Mark simulation as stopping"""
    stop_file = SIMULATION_LOG_PATH / "stopping.flag"
    with open(stop_file, 'w') as f:
        f.write(str(datetime.now().timestamp()))

def was_stopping():
    """Check if simulation was stopped via signal"""
    stop_file = SIMULATION_LOG_PATH / "stopping.flag"
    if stop_file.exists():
        stop_file.unlink()
        save_last_balance(_sim_instance.balance if _sim_instance else 0)
        return True
    return False

def reset_balance():
    """Reset balance and history to start fresh"""
    balance_file = SIMULATION_LOG_PATH / "balance.txt"
    if balance_file.exists():
        balance_file.unlink()
    
    hourly_file = SIMULATION_LOG_PATH / "hourly_stats.json"
    if hourly_file.exists():
        hourly_file.unlink()
    
    for item in SIMULATION_LOG_PATH.iterdir():
        if item.is_dir():
            for f in item.iterdir():
                if f.name in ['trades.txt', 'open_bets.json', 'summary.txt']:
                    f.unlink()

def save_last_balance(balance):
    """Save current balance to file"""
    balance_file = SIMULATION_LOG_PATH / "balance.txt"
    with open(balance_file, 'w') as f:
        f.write(str(balance))

def create_log_folder(mode='simulation'):
    """Create log folder for simulation or real trading"""
    date_str = datetime.now().strftime("%d-%m-%Y")
    folder_path = (SIMULATION_LOG_PATH if mode == 'simulation' else REAL_LOG_PATH) / date_str
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path

def log_trade(folder, trade):
    """Log trade to file"""
    timestamp = trade.get('timestamp', datetime.now())
    if hasattr(timestamp, 'strftime'):
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = str(timestamp)
    
    profit = trade['profit']
    profit_str = f"+${profit:.2f}" if profit >= 0 else f"-${abs(profit):.2f}"
    odds_str = f"{trade['odds']:.2f}x"
    result_str = "WIN" if trade['won'] else "LOSE"
    
    with open(folder / "trades.txt", "a") as f:
        f.write(f"[{time_str}] {trade['action']} {odds_str} | Bet: ${trade['bet_size']:.2f} | {result_str} | Profit: {profit_str} | Balance: ${trade['balance']:.2f} | Category: {trade['category']} | URL: {trade['url']}\n")
    
    lose_file = folder / "loses.txt"
    if not trade['won']:
        with open(lose_file, "a") as f:
            f.write(f"[{time_str}] {trade['action']} {odds_str} | Bet: ${trade['bet_size']:.2f} | LOSE | Profit: {profit_str} | Balance: ${trade['balance']:.2f} | Category: {trade['category']} | URL: {trade['url']}\n")
    
    with open(folder / "trades.txt", "r") as f:
        lines = f.readlines()
    if len(lines) > 30:
        with open(folder / "trades.txt", "w") as f:
            f.writelines(lines[-30:])

def log_summary(folder, stats):
    """Log session summary"""
    with open(folder / "summary.txt", "a") as f:
        f.write(f"Session completed at {datetime.now().strftime('%H:%M:%S')} - Balance: ${stats['balance']:.2f} | Trades: {stats['total_trades']} | Wins: {stats['wins']} | Profit: ${stats['total_profit']:.2f}\n")


class SimulationSession(BettingSession):
    """Simulation betting session"""
    
    def __init__(self, **kwargs):
        log_folder = create_log_folder('simulation')
        kwargs['log_folder'] = log_folder
        kwargs.setdefault('bet_size_pct', 0.02)
        
        last_balance = get_last_balance()
        if last_balance is not None:
            kwargs['initial_balance'] = last_balance
            print(f"\n📊 Loaded last balance: ${last_balance:.2f}")
        
        super().__init__(**kwargs)
        self.log_folder = log_folder
        self.open_bets_file = self.log_folder / "open_bets.json"
        self._load_open_bets()
    
    def stop(self):
        """Stop simulation and save balance"""
        save_last_balance(self.balance)
        print(f"\n💾 Saved balance: ${self.balance:.2f}")
    
    def _load_open_bets(self):
        """Load open bets from file"""
        if self.open_bets_file.exists():
            try:
                import json
                with open(self.open_bets_file, 'r') as f:
                    data = json.load(f)
                    for bet in data:
                        if 'opened_at' in bet and isinstance(bet['opened_at'], str):
                            bet['opened_at'] = datetime.strptime(bet['opened_at'], '%Y-%m-%d %H:%M:%S')
                    self.open_bets = data
            except:
                self.open_bets = []
    
    def _save_open_bets(self):
        """Save open bets to file"""
        import json
        data = []
        for bet in self.open_bets:
            bet_copy = bet.copy()
            if 'opened_at' in bet_copy and hasattr(bet_copy['opened_at'], 'isoformat'):
                bet_copy['opened_at'] = bet_copy['opened_at'].isoformat()
            data.append(bet_copy)
        with open(self.open_bets_file, 'w') as f:
            json.dump(data, f)
    
    def open_bet(self, market):
        """Open a new bet"""
        allowed, reason = self.can_open_bet()
        if not allowed:
            return None
        
        action, entry_prob = self.should_bet(market['prob_yes'])
        if not action or entry_prob is None or entry_prob == 0:
            return None
        
        if self.balance < self.bet_size:
            return None
        
        odds = 1/entry_prob if action == 'YES' else 1/(1-entry_prob) if entry_prob < 1 else 1
        
        bet = {
            'market_id': market.get('id', ''),
            'question': market['question'],
            'action': action,
            'entry_price': market.get('entry_price', 0.5),
            'entry_prob': entry_prob,
            'amount': self.bet_size,
            'odds': odds,
            'opened_at': datetime.now(),
            'category': market.get('category', 'Other'),
            'url': market.get('url', '')
        }
        
        self.open_bets.append(bet)
        self._save_open_bets()
        return bet
    
    def resolve_all_bets(self, minutes=1):
        """Resolve all open bets"""
        resolved = []
        
        for bet in self.open_bets:
            exit_price = simulate_future_price(bet['entry_price'], minutes)
            trade = self.resolve_bet(bet, exit_price)
            resolved.append(trade)
        
        self.open_bets = []
        self._save_open_bets()
        return resolved


def run_live_simulation(minutes=60, initial_balance=100.0, bet_size=2.0, bet_size_pct=0.02, min_prob=0.70, 
                        category=None, max_open_bets=10, max_open_pct=0.30):
    """Run live simulation"""
    
    print("\n" + "="*70)
    print("🎯 FUTURE PRICE SIMULATION - LIVE MARKETS".center(70))
    print("="*70)
    
    print(f"\n📊 CONFIG:")
    print(f"   Duration: {minutes} minutes")
    print(f"   Initial Balance: ${initial_balance}")
    print(f"   Bet Size: ${bet_size} (fixed) + {bet_size_pct*100}% (compound)")
    print(f"   Min Probability: {min_prob*100}%")
    print(f"   Max Open Bets: {max_open_bets}")
    print(f"   Max Open %: {max_open_pct*100}%")
    print(f"   Category: {category if category else 'all'}")
    
    print(f"\n📥 Fetching live markets...")
    markets = fetch_markets(closed=False, limit=200)
    print(f"   Total markets: {len(markets)}")
    
    eligible = filter_markets(markets, category=category, min_volume=1000)
    print(f"   Eligible markets: {len(eligible)}")
    
    high_prob = get_high_probability_markets(eligible, min_prob=min_prob)
    print(f"   High probability (>{min_prob*100}% or <{(1-min_prob)*100}%): {len(high_prob)}")
    
    if not high_prob:
        print("\n❌ No high probability markets found")
        return None
    
    print(f"\n🎯 High Probability Markets (top 10):")
    print(f"   {'Question':<40} {'Prob':<8} {'Action'}")
    print("   " + "-"*55)
    for m in high_prob[:10]:
        print(f"   {m['question'][:40]:<40} {m['prob_yes']*100:>5.1f}%   {m['action']}")
    
    sim = SimulationSession(
        initial_balance=initial_balance,
        bet_size=bet_size,
        bet_size_pct=bet_size_pct,
        min_prob=min_prob,
        max_open_bets=max_open_bets,
        max_open_pct=max_open_pct,
        category=category
    )
    
    global _sim_instance
    _sim_instance = sim
    
    print(f"\n🚀 Running simulation... (press Ctrl+C to stop)")
    
    import random
    import time
    random.shuffle(high_prob)
    
    i = 0
    market_idx = 0
    wait_minutes = minutes if minutes else 1
    
    def get_open_amount():
        return sum(b['amount'] for b in sim.open_bets)
    
    def fill_open_bets():
        """Fill open bets to maintain target %"""
        nonlocal market_idx
        target_amount = sim.balance * max_open_pct
        filled = 0
        
        while get_open_amount() < target_amount and high_prob:
            market = high_prob[market_idx % len(high_prob)]
            
            current_bet_size = sim.get_current_bet_size()
            
            if sim.balance < current_bet_size:
                break
            
            # Use market's action from high_prob (not hardcoded to NO)
            action = market.get('action', 'NO')
            entry_prob = market.get('action_prob', 0.5)
            
            bet = {
                'market_id': market.get('id', ''),
                'question': market['question'],
                'action': action,
                'entry_price': market.get('entry_price', 0.5),
                'entry_prob': entry_prob,
                'amount': current_bet_size,
                'odds': 1/entry_prob if entry_prob > 0 else 1,
                'opened_at': datetime.now(),
                'category': market.get('category', 'Other'),
                'url': market.get('url', '')
            }
            
            allowed, reason = sim.can_open_bet()
            if not allowed:
                break
            
            sim.open_bets.append(bet)
            sim._save_open_bets()
            print(f"   Opened: {bet['action']} ${bet['amount']:.2f} @ {bet['entry_prob']*100:.1f}% - {bet['question'][:35]}")
            filled += 1
            market_idx += 1
        
        return filled
    
    fill_open_bets()
    
    def save_hourly_stats():
        """Save hourly stats for chart"""
        stats = sim.get_stats()
        hourly_file = SIMULATION_LOG_PATH / "hourly_stats.json"
        
        hourly_data = []
        if hourly_file.exists():
            try:
                import json
                with open(hourly_file, 'r') as f:
                    hourly_data = json.load(f)
            except:
                hourly_data = []
        
        import json
        hourly_data.append({
            'timestamp': datetime.now().isoformat(),
            'balance': sim.balance,
            'total_profit': stats['balance'] - stats['initial_balance'],
            'trades': stats['total_trades'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'open_amount': get_open_amount(),
            'initial_balance': stats['initial_balance']
        })
        
        with open(hourly_file, 'w') as f:
            json.dump(hourly_data, f)
    
    while True:
        time.sleep(wait_minutes)
        
        if sim.open_bets:
            resolved = sim.resolve_all_bets(minutes=wait_minutes)
            for r in resolved:
                log_trade(sim.log_folder, r)
            save_last_balance(sim.balance)
        
        fill_open_bets()
        
        i += 1
        if i % 10 == 0:
            stats = sim.get_stats()
            save_hourly_stats()
            print(f"   Loop {i}: Balance ${stats['balance']:.2f} | Trades: {stats['total_trades']} | Wins: {stats['wins']} | Open: {len(sim.open_bets)} (${get_open_amount():.2f})")
    
    stats = sim.get_stats()
    sim.stop()
    
    print(f"\n" + "="*70)
    print("📈 SIMULATION RESULTS".center(70))
    print("="*70)
    
    print(f"\n💰 FINANCIAL:")
    print(f"   Initial Balance: ${stats['initial_balance']}")
    print(f"   Final Balance: ${stats['balance']:.2f}")
    print(f"   Total Profit: ${stats['total_profit']:.2f}")
    print(f"   ROI: {stats['roi']:.1f}%")
    
    print(f"\n📊 TRADING:")
    print(f"   Total Trades: {stats['total_trades']}")
    print(f"   Wins: {stats['wins']}")
    print(f"   Losses: {stats['losses']}")
    print(f"   Win Rate: {stats['win_rate']:.1f}%")
    
    if simulation_results:
        print(f"\n📋 Recent Trades:")
        print(f"   {'Time':<8} {'Question':<30} {'Act':<4} {'Entry':<6} {'Exit':<6} {'Profit'}")
        print("   " + "-"*70)
        for t in simulation_results[-15:]:
            profit_str = f"+${t['profit']:.2f}" if t['profit'] > 0 else f"-${abs(t['profit']):.2f}"
            entry_pct = t['entry_price'] * 100
            exit_pct = t['exit_price'] * 100
            ts = t.get('timestamp', '')
            time_str = ts.strftime('%H:%M:%S') if hasattr(ts, 'strftime') else '00:00:00'
            print(f"   {time_str:<8} {t['question'][:30]:<30} {t['action']:<4} {entry_pct:>5.1f}%  {exit_pct:>5.1f}%  {profit_str}")
    
    log_summary(sim.log_folder, stats)
    print(f"\n📁 Logs saved to: {sim.log_folder}")
    
    return sim


import signal
import sys

_sim_instance = None

def signal_handler(sig, frame):
    print("\n\n🛑 Stopping simulation...")
    if _sim_instance is not None:
        _sim_instance.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def main():
    global _sim_instance
    
    parser = argparse.ArgumentParser(description='Polymarket Simulation')
    parser.add_argument('--mode', type=str, default='live', choices=['live', 'batch'], help='Simulation mode')
    parser.add_argument('--minutes', type=int, default=60, help='Minutes to simulate')
    parser.add_argument('--balance', type=float, default=100.0, help='Initial balance')
    parser.add_argument('--bet', type=float, default=2.0, help='Bet size per trade')
    parser.add_argument('--prob', type=float, default=0.70, help='Minimum probability threshold')
    parser.add_argument('--category', type=str, default='all', help='Filter by category')
    parser.add_argument('--max-open', type=int, default=10, help='Maximum open bets')
    parser.add_argument('--max-pct', type=float, default=0.30, help='Maximum open amount percentage')
    
    args = parser.parse_args()
    
    cat = args.category if args.category and args.category != 'a' else None
    
    if args.mode == 'live':
        run_live_simulation(
            minutes=args.minutes,
            initial_balance=args.balance,
            bet_size=args.bet,
            min_prob=args.prob,
            category=cat,
            max_open_bets=args.max_open,
            max_open_pct=args.max_pct
        )


if __name__ == "__main__":
    main()