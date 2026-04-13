import os
import sys
import time
import random
import argparse
import json
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.auth import load_wallet
from bot.market import fetch_markets, get_current_price

CATEGORIES = {
    "1": "Sports",
    "2": "Politics", 
    "3": "Crypto",
    "4": "Economy",
    "5": "Tech",
    "6": "Culture",
    "7": "Weather",
    "8": "Esports"
}

KEYWORDS = {
    "Sports": ["NHL", "NBA", "NFL", "FIFA", "World Cup", "Stanley Cup", "Finals", "win the"],
    "Politics": ["President", "election", "Trump", "Biden", "Congress", "Senate", "Governor"],
    "Crypto": ["Bitcoin", "Ethereum", "BTC", "ETH", "Solana"],
    "Economy": ["GDP", "inflation", "recession", "Fed", "interest rate", "economy"],
    "Tech": ["AI", "Apple", "Google", "Microsoft", "Tesla", "tech"],
    "Culture": ["album", "movie", "Rihanna", "Carti", "GTA", "music"],
    "Weather": ["hurricane", "earthquake", "storm", "weather", "rain"],
    "Esports": ["Dota", "League", "CSGO", "esports", "gaming"]
}

def analyze_historical(min_prob=0.70, min_volume=5000, category=None, initial_balance=10.0, bet_size=2.0):
    """Analyze historical data - markets that have been resolved"""
    
    print("\n" + "="*75)
    print("📊 HISTORICAL ANALYSIS - RESOLVED MARKETS".center(75))
    print("="*75)
    
    print(f"\n📊 CONFIG:")
    print(f"   Initial Balance: ${initial_balance}")
    print(f"   Bet Size: ${bet_size}")
    print(f"   Min Probability: {min_prob*100}%")
    print(f"   Min Volume: ${min_volume}")
    
    print(f"\n📥 Fetching closed/resolved markets...")
    markets = fetch_markets(closed=True, limit=300)
    
    print(f"   Total markets fetched: {len(markets)}")
    
    analyzed = []
    
    for m in markets:
        question = m.get('question', '').lower()
        group = m.get('groupItemTitle', '').lower()
        
        if category:
            keywords = KEYWORDS.get(category, [])
            if not any(kw.lower() in question for kw in keywords):
                if not any(kw.lower() in group for kw in keywords):
                    continue
        
        vol = float(m.get('volume', 0))
        if vol < min_volume:
            continue
        
        outcome_prices_str = m.get('outcomePrices', '[]')
        try:
            outcome_prices = json.loads(outcome_prices_str)
        except:
            continue
        
        if len(outcome_prices) < 2:
            continue
        
        yes_price = float(outcome_prices[0])
        no_price = float(outcome_prices[1])
        
        if yes_price == 0 and no_price == 0:
            continue
        
        won = None
        if yes_price > no_price:
            outcome = 'YES'
            if yes_price >= min_prob:
                won = True
        else:
            outcome = 'NO'
            if no_price >= min_prob:
                won = True
        
        if won is None:
            continue
        
        entry_price = yes_price
        
        detected_cat = "Other"
        for cat_name, keywords in KEYWORDS.items():
            if any(kw.lower() in question for kw in keywords):
                detected_cat = cat_name
                break
        
        profit = bet_size * (1/entry_price - 1) if won else -bet_size
        
        analyzed.append({
            'question': m.get('question', 'N/A')[:50],
            'category': detected_cat,
            'volume': vol,
            'entry_price': entry_price,
            'outcome': outcome,
            'won': won,
            'profit': profit
        })
    
    print(f"   Markets analyzed: {len(analyzed)}")
    
    if not analyzed:
        print("❌ No historical data found")
        return
    
    wins = sum(1 for m in analyzed if m['won'])
    losses = len(analyzed) - wins
    win_rate = (wins / len(analyzed) * 100) if analyzed else 0
    
    balance = initial_balance
    peak = initial_balance
    max_drawdown = 0
    daily_balances = {}
    
    for i, m in enumerate(analyzed):
        balance += m['profit']
        day = i // 10
        if day not in daily_balances:
            daily_balances[day] = []
        daily_balances[day].append(balance)
        
        if balance > peak:
            peak = balance
        drawdown = (peak - balance) / peak * 100 if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    total_profit = balance - initial_balance
    roi = (total_profit / initial_balance) * 100
    
    trades_per_day = len(analyzed) / max(1, len(daily_balances))
    avg_daily_profit = total_profit / max(1, len(daily_balances))
    
    print(f"\n{'='*75}")
    print(f"📈 RESULTS".center(75))
    print(f"{'='*75}")
    
    print(f"\n💰 FINANCIAL:")
    print(f"   Initial Balance: ${initial_balance}")
    print(f"   Final Balance: ${balance:.2f}")
    print(f"   Total Profit: ${total_profit:.2f}")
    print(f"   ROI: {roi:.1f}%")
    print(f"   Max Drawdown: {max_drawdown:.1f}%")
    
    print(f"\n📊 TRADING:")
    print(f"   Total Trades: {len(analyzed)}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Avg Trades/Day: {trades_per_day:.1f}")
    print(f"   Avg Daily Profit: ${avg_daily_profit:.2f}")
    
    cat_stats = {}
    for m in analyzed:
        cat = m['category']
        if cat not in cat_stats:
            cat_stats[cat] = {'trades': 0, 'wins': 0, 'profit': 0}
        cat_stats[cat]['trades'] += 1
        if m['won']:
            cat_stats[cat]['wins'] += 1
        cat_stats[cat]['profit'] += m['profit']
    
    print(f"\n📊 BY CATEGORY:")
    print(f"   {'Category':<12} {'Trades':<8} {'Wins':<8} {'Win%':<8} {'Profit':<10}")
    print("   " + "-"*50)
    for cat, stats in sorted(cat_stats.items()):
        wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
        print(f"   {cat:<12} {stats['trades']:<8} {stats['wins']:<8} {wr:>5.1f}%   ${stats['profit']:.2f}")
    
    print(f"\n📋 Sample Trades:")
    print(f"   {'Question':<40} {'Entry':<8} {'Outcome':<8} {'Profit'}")
    print("   " + "-"*70)
    for m in analyzed[:10]:
        profit_str = f"+${m['profit']:.2f}" if m['profit'] > 0 else f"-${abs(m['profit']):.2f}"
        print(f"   {m['question'][:40]:<40} {m['entry_price']*100:>5.1f}%   {m['outcome']:<8} {profit_str}")
    
    print(f"\n{'='*75}")
    print("📊 LIVE HIGH PROBABILITY MARKETS - READY TO TRADE".center(75))
    print(f"{'='*75}")
    
    live_markets = fetch_markets(closed=False, limit=100)
    high_prob_live = []
    
    for m in live_markets:
        prices = get_current_price(m)
        if prices:
            prob = prices['mid_price']
            vol = float(m.get('volume', 0))
            if (prob >= min_prob or prob <= (1-min_prob)) and vol > min_volume:
                action = 'YES' if prob >= min_prob else 'NO'
                high_prob_live.append({
                    'question': m.get('question', '')[:40],
                    'prob': prob,
                    'action': action,
                    'volume': vol,
                    'odds': 1/prob if prob >= min_prob else 1/(1-prob)
                })
    
    print(f"\n   Total LIVE markets with >{min_prob*100}% prob: {len(high_prob_live)}")
    print(f"\n   {'#':<3} {'Question':<40} {'Prob':<8} {'Odds':<6} {'Action'}")
    print("   " + "-"*65)
    for i, m in enumerate(high_prob_live[:20], 1):
        print(f"   {i:<3} {m['question']:<40} {m['prob']*100:>5.1f}%   {m['odds']:.2f}x   {m['action']}")

def create_log_folder():
    now = datetime.now()
    folder_name = now.strftime("%m-%d-%Y_%H-%M")
    folder_path = Path(f"backtest/{folder_name}")
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path

def log_to_file(folder, filename, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(folder / filename, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

class BacktestEngine:
    def __init__(self, initial_balance=1000.0, trade_size=None, max_position_pct=0.1, max_daily_loss_pct=0.05, max_consecutive_losses=3):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        
        if trade_size is None:
            self.trade_size = initial_balance * 0.1
        else:
            self.trade_size = min(trade_size, initial_balance * max_position_pct)
        
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        
        self.trades = []
        self.daily_stats = []
        self.consecutive_losses = 0
        self.total_wins = 0
        self.total_losses = 0
        self.daily_loss = 0
        self.log_folder = None
    
    def set_log_folder(self, folder):
        self.log_folder = folder
    
    def can_trade(self):
        if self.balance < self.trade_size:
            return False, "Insufficient balance"
        
        daily_loss_pct = abs(self.daily_loss) / self.initial_balance
        if daily_loss_pct >= self.max_daily_loss_pct:
            return False, f"Max daily loss {self.max_daily_loss_pct*100}% reached"
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Max consecutive losses {self.max_consecutive_losses} reached"
        
        return True, "OK"
    
    def execute_trade(self, market, price_change, category):
        allowed, reason = self.can_trade()
        if not allowed:
            return None
        
        entry_price = market['entry_price']
        exit_price = entry_price * (1 + price_change)
        
        size = min(self.trade_size, self.balance * self.max_position_pct)
        
        if entry_price < 0.05:
            profit = size * (exit_price / entry_price - 1)
            action = "BUY"
        elif entry_price > 0.95:
            profit = size * (1 - exit_price / entry_price)
            action = "SELL"
        else:
            return None
        
        self.balance += profit
        self.daily_loss += profit
        
        trade = {
            'day': market.get('day', 0),
            'category': category,
            'market': market['question'][:35],
            'action': action,
            'entry': entry_price,
            'exit': exit_price,
            'size': size,
            'profit': profit
        }
        
        self.trades.append(trade)
        
        if self.log_folder:
            log_to_file(self.log_folder, "trades.txt", 
                f"DAY {trade['day']} | {action} | {market['question'][:40]} | Entry: {entry_price:.4f} | Exit: {exit_price:.4f} | Size: ${size:.2f} | Profit: ${profit:.2f}")
        
        if profit > 0:
            self.consecutive_losses = 0
            self.total_wins += 1
        else:
            self.consecutive_losses += 1
            self.total_losses += 1
        
        return trade
    
    def new_day(self, day):
        self.daily_stats.append({
            'day': day,
            'balance': self.balance,
            'pnl': self.daily_loss,
            'trades': len([t for t in self.trades if t.get('day') == day])
        })
        self.daily_loss = 0

def simulate_price(mid_price, day, total_days):
    trend = (0.5 - mid_price) * 0.1
    volatility = 0.03 * (day / total_days)
    change = random.gauss(trend, volatility)
    return max(0.01, min(0.99, mid_price + change))

def run_backtest(days=90, initial_balance=1000.0, trade_size=50.0, category=None, min_prob=0.70):
    log_folder = create_log_folder()
    
    log_to_file(log_folder, "config.txt", f"Period: {days} days")
    log_to_file(log_folder, "config.txt", f"Initial Balance: ${initial_balance}")
    log_to_file(log_folder, "config.txt", f"Trade Size: ${trade_size}")
    log_to_file(log_folder, "config.txt", f"Max Position: 10%")
    log_to_file(log_folder, "config.txt", f"Max Daily Loss: 5%")
    log_to_file(log_folder, "config.txt", f"Max Consecutive Losses: 3")
    log_to_file(log_folder, "config.txt", f"Min Probability: {min_prob*100}%")
    if category:
        log_to_file(log_folder, "config.txt", f"Category: {category}")
    
    print(f"\n📁 Log folder: {log_folder}")
    
    engine = BacktestEngine(
        initial_balance=initial_balance,
        trade_size=trade_size,
        max_position_pct=0.1,
        max_daily_loss_pct=0.05,
        max_consecutive_losses=3
    )
    engine.set_log_folder(log_folder)
    
    print("\n" + "="*75)
    print("⚡ POLYMARKET BACKTEST - HIGH PROBABILITY STRATEGY".center(75))
    print("="*75)
    
    print(f"\n📊 CONFIG:")
    print(f"   Period: {days} days")
    print(f"   Initial Balance: ${initial_balance}")
    print(f"   Trade Size: ${trade_size}")
    print(f"   Min Probability: {min_prob*100}%")
    if category:
        print(f"   Category Filter: {category}")
    
    log_to_file(log_folder, "summary.txt", "="*50)
    log_to_file(log_folder, "summary.txt", "BACKTEST STARTED - HIGH PROBABILITY")
    log_to_file(log_folder, "summary.txt", f"Period: {days} days, Balance: ${initial_balance}")
    log_to_file(log_folder, "summary.txt", f"Min Probability: {min_prob*100}%")
    log_to_file(log_folder, "summary.txt", "="*50)
    
    print(f"\n📥 Loading markets from Polymarket...")
    markets = fetch_markets(limit=100)
    
    market_data = []
    high_prob_markets = []
    
    print(f"   Analyzing {len(markets)} markets...")
    
    for m in markets:
        prices = get_current_price(m)
        if not prices:
            continue
        
        question = m.get('question', '').lower()
        group = m.get('groupItemTitle', '').lower()
        
        if category:
            keywords = KEYWORDS.get(category, [])
            if not any(kw.lower() in question for kw in keywords):
                if not any(kw.lower() in group for kw in keywords):
                    continue
        
        vol = float(m.get('volume', 0))
        min_vol = 1000 if initial_balance < 500 else 5000
        if vol < min_vol:
            continue
        
        detected_cat = "Other"
        for cat_name, keywords in KEYWORDS.items():
            if any(kw.lower() in question for kw in keywords):
                detected_cat = cat_name
                break
        
        mid_price = prices['mid_price']
        prob_yes = mid_price
        
        market_info = {
            'id': m['id'],
            'question': m.get('question', 'N/A')[:40],
            'slug': m.get('slug', ''),
            'category': detected_cat,
            'entry_price': mid_price,
            'volume': vol,
            'prob_yes': prob_yes,
            'best_bid': prices['best_bid'],
            'best_ask': prices['best_ask'],
            'spread': prices['spread']
        }
        
        market_data.append(market_info)
        
        if prob_yes >= min_prob:
            market_info['action'] = 'YES'
            high_prob_markets.append(market_info)
        elif prob_yes <= (1 - min_prob):
            market_info['action'] = 'NO'
            high_prob_markets.append(market_info)
    
    print(f"   Total markets: {len(market_data)}")
    print(f"   High probability (>{min_prob*100}%): {len(high_prob_markets)}")
    log_to_file(log_folder, "config.txt", f"Total markets: {len(market_data)}")
    log_to_file(log_folder, "config.txt", f"High probability: {len(high_prob_markets)}")
    
    if not high_prob_markets:
        print("❌ No high probability markets found")
        return
    
    print(f"\n🎯 High Probability Markets Found:")
    print(f"{'#':<3} {'Question':<40} {'Prob':<8} {'Action':<6}")
    print("-"*60)
    for i, m in enumerate(high_prob_markets[:10], 1):
        print(f"{i:<3} {m['question'][:40]:<40} {m['prob_yes']*100:>5.1f}%   {m['action']}")
    
    if len(high_prob_markets) > 10:
        print(f"   ... and {len(high_prob_markets) - 10} more")
    
    print(f"\n🚀 Running backtest for {days} days...")
    print(f"   Strategy: Bet on high probability outcomes (>70%)")
    
    trades_today = 0
    
    for day in range(1, days + 1):
        daily_trades = 0
        
        for market in high_prob_markets:
            market['day'] = day
            
            price_change = random.gauss(0, 0.02)
            current_price = simulate_price(market['entry_price'], day, days)
            market['exit_price'] = current_price
            
            price_diff = current_price - market['entry_price']
            pct_change = price_diff / market['entry_price']
            
            if market['action'] == 'YES':
                if current_price >= market['entry_price']:
                    trade = engine.execute_trade(market, pct_change, market['category'])
                    if trade:
                        daily_trades += 1
            else:
                if current_price <= market['entry_price']:
                    trade = engine.execute_trade(market, pct_change, market['category'])
                    if trade:
                        daily_trades += 1
        
        trades_today += daily_trades
        engine.new_day(day)
        
        if day % 30 == 0:
            print(f"   Day {day}: Balance ${engine.balance:.2f} | Wins: {engine.total_wins} | Losses: {engine.total_losses}")
            log_to_file(log_folder, "summary.txt", f"Day {day}: Balance ${engine.balance:.2f}")
    
    print(f"\n{'='*75}")
    print("📈 BACKTEST RESULTS".center(75))
    print(f"{'='*75}")
    
    total_return = ((engine.balance - initial_balance) / initial_balance) * 100
    
    print(f"\n💰 Final Balance: ${engine.balance:.2f}")
    print(f"📈 Total Return: {total_return:.2f}%")
    print(f"📊 Total Trades: {len(engine.trades)}")
    print(f"✅ Wins: {engine.total_wins}")
    print(f"❌ Losses: {engine.total_losses}")
    
    total_trades = len(engine.trades)
    win_rate = (engine.total_wins / total_trades * 100) if total_trades > 0 else 0
    print(f"🎯 Win Rate: {win_rate:.1f}%")
    
    log_to_file(log_folder, "summary.txt", "="*50)
    log_to_file(log_folder, "summary.txt", "FINAL RESULTS")
    log_to_file(log_folder, "summary.txt", f"Final Balance: ${engine.balance:.2f}")
    log_to_file(log_folder, "summary.txt", f"Total Return: {total_return:.2f}%")
    log_to_file(log_folder, "summary.txt", f"Total Trades: {len(engine.trades)}")
    log_to_file(log_folder, "summary.txt", f"Wins: {engine.total_wins}, Losses: {engine.total_losses}")
    log_to_file(log_folder, "summary.txt", f"Win Rate: {win_rate:.1f}%")
    
    if engine.trades:
        cat_stats = {}
        for t in engine.trades:
            cat = t.get('category', 'Unknown')
            if cat not in cat_stats:
                cat_stats[cat] = {'trades': 0, 'wins': 0, 'profit': 0}
            cat_stats[cat]['trades'] += 1
            if t['profit'] > 0:
                cat_stats[cat]['wins'] += 1
            cat_stats[cat]['profit'] += t['profit']
        
        print(f"\n📊 PERFORMANCE BY CATEGORY:")
        print(f"{'Category':<15} {'Trades':<8} {'Wins':<6} {'Win%':<8} {'Profit'}")
        print("-"*50)
        
        log_to_file(log_folder, "summary.txt", "CATEGORY PERFORMANCE:")
        for cat, stats in sorted(cat_stats.items()):
            wr = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            print(f"{cat:<15} {stats['trades']:<8} {stats['wins']:<6} {wr:>5.1f}%   ${stats['profit']:.2f}")
            log_to_file(log_folder, "summary.txt", f"{cat}: {stats['trades']} trades, {wr:.1f}% win, ${stats['profit']:.2f}")
    
    print(f"\n--- Recent Trades (last 10) ---")
    if engine.trades:
        print(f"{'Day':<4} {'Category':<10} {'Market':<28} {'Act':<5} {'Entry':<6} {'Exit':<6} {'Profit'}")
        print("-"*75)
        for t in engine.trades[-10:]:
            print(f"{t['day']:<4} {t.get('category', 'N/A')[:10]:<10} {t['market']:<28} {t['action']:<5} {t['entry']:.2f}   {t['exit']:.2f}   ${t['profit']:.2f}")
    
    print(f"\n📁 Logs saved to: {log_folder}/")
    print(f"   - trades.txt (all trades)")
    print(f"   - summary.txt (results)")
    print(f"   - config.txt (configuration)")
    
    print(f"\n{'='*75}")

def main():
    parser = argparse.ArgumentParser(description='Polymarket Backtest - High Probability Strategy')
    parser.add_argument('--days', type=int, default=90)
    parser.add_argument('--balance', type=float, default=1000.0)
    parser.add_argument('--size', type=float, default=50.0)
    parser.add_argument('--category', type=str, default=None, help='Filter by category')
    parser.add_argument('--min-prob', type=float, default=0.70, help='Minimum probability threshold (0.0-1.0)')
    
    args = parser.parse_args()
    
    print("\n" + "="*75)
    print("📂 SELECT CATEGORY".center(75))
    print("="*75)
    for k, v in CATEGORIES.items():
        print(f"  [{k}] {v}")
    print(f"  [a] All Categories")
    print("-"*50)
    
    if args.category:
        cat = args.category
    else:
        cat = input("Select [1-8, a]: ").strip().lower()
    
    if cat == 'a':
        cat = None
    elif cat in CATEGORIES:
        cat = CATEGORIES[cat]
    
    try:
        run_backtest(days=args.days, initial_balance=args.balance, trade_size=args.size, category=cat, min_prob=args.min_prob)
    except KeyboardInterrupt:
        print("\n\n👋 Backtest stopped!")

if __name__ == "__main__":
    analyze_historical(min_prob=0.70, min_volume=1000)
