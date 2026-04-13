"""
Simulation API - Simulation logic as API functions
Based on bot/simulate_future.py and bot/trading_utils.py
"""

import os
import sys
import json
import random
import threading
import time
import requests
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SIMULATION_PATH = Path("/Users/azharuddinarrosis/Developments/polymarket/simulation")
SIM_STATE_FILE = SIMULATION_PATH / "state.json"
HOURLY_STATS_FILE = SIMULATION_PATH / "hourly_stats.json"

GAMMA_API_URL = "https://gamma-api.polymarket.com"

POLYMARKET_FEE = 0.02  # 2% fee on winnings

def fetch_market_price(market_id):
    """Fetch real-time price for a market"""
    try:
        r = requests.get(f"{GAMMA_API_URL}/markets/{market_id}", timeout=10)
        if r.status_code == 200:
            market = r.json()
            best_bid = market.get("bestBid")
            best_ask = market.get("bestAsk")
            if best_bid is not None and best_ask is not None:
                return (float(best_bid) + float(best_ask)) / 2
        return None
    except Exception as e:
        print(f"Error fetching price for {market_id}: {e}")
        return None

def fetch_full_market_data(market_id):
    """Fetch full market data including bid-ask spread"""
    try:
        r = requests.get(f"{GAMMA_API_URL}/markets/{market_id}", timeout=10)
        if r.status_code == 200:
            market = r.json()
            best_bid = market.get("bestBid")
            best_ask = market.get("bestAsk")
            if best_bid is not None and best_ask is not None:
                return {
                    'mid_price': (float(best_bid) + float(best_ask)) / 2,
                    'best_bid': float(best_bid),
                    'best_ask': float(best_ask)
                }
        return None
    except Exception as e:
        print(f"Error fetching market data for {market_id}: {e}")
        return None

def save_sim_state(running):
    """Save simulation running state"""
    with open(SIM_STATE_FILE, 'w') as f:
        json.dump({"running": running}, f)

def load_sim_state():
    """Load simulation running state"""
    if SIM_STATE_FILE.exists():
        try:
            with open(SIM_STATE_FILE, 'r') as f:
                return json.load(f).get("running", False)
        except:
            pass
    return False

class SimulationSession:
    """Simulation betting session"""
    
    def __init__(self, initial_balance=100.0, bet_size=2.0, bet_size_pct=0.02, 
                 min_prob=0.70, max_open_bets=10, max_open_pct=0.30, category=None):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.bet_size = bet_size
        self.bet_size_pct = bet_size_pct
        self.min_prob = min_prob
        self.category = category
        
        self.max_open_bets = max_open_bets
        self.max_open_pct = max_open_pct
        
        self.trades = []
        self.open_bets = []
        self.wins = 0
        self.losses = 0
        
        self.log_folder = self._create_log_folder()
        self._load_open_bets()
        self._load_balance()
    
    def _create_log_folder(self):
        date_str = datetime.now().strftime("%d-%m-%Y")
        folder = SIMULATION_PATH / date_str
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    
    def _load_balance(self):
        balance_file = SIMULATION_PATH / "balance.txt"
        if balance_file.exists():
            try:
                with open(balance_file, 'r') as f:
                    val = f.read().strip()
                    if val:
                        saved_balance = float(val)
                        # Only load saved balance if we didn't specify a new initial balance
                        # This allows user to start fresh with custom balance
                        self.balance = saved_balance
                        self.initial_balance = saved_balance
            except:
                pass
    
    def _save_balance(self):
        balance_file = SIMULATION_PATH / "balance.txt"
        with open(balance_file, 'w') as f:
            f.write(str(self.balance))
    
    def _load_open_bets(self):
        open_file = self.log_folder / "open_bets.json"
        if open_file.exists():
            try:
                with open(open_file, 'r') as f:
                    self.open_bets = json.load(f)
            except:
                self.open_bets = []
    
    def _save_open_bets(self):
        open_file = self.log_folder / "open_bets.json"
        with open(open_file, 'w') as f:
            json.dump(self.open_bets, f)
    
    def get_max_open_amount(self):
        return self.balance * self.max_open_pct
    
    def get_current_bet_size(self):
        return max(self.bet_size, self.balance * self.bet_size_pct)
    
    def can_open_bet(self):
        total_open = sum(b['amount'] for b in self.open_bets)
        max_allowed = self.get_max_open_amount()
        if total_open >= max_allowed:
            return False, "Max open amount reached"
        return True, "OK"
    
    def should_bet(self, prob_yes):
        if prob_yes >= self.min_prob:
            return 'YES', prob_yes
        elif prob_yes <= (1 - self.min_prob):
            return 'NO', 1 - prob_yes
        return None, 0
    
    def simulate_future_price(self, current_price, minutes_ahead, volatility=None, category=None):
        """Simulate future price movement with market-specific volatility"""
        # Volatility based on category (higher for volatile markets)
        if volatility is None:
            if category in ['Crypto', 'Politics']:
                volatility = 0.008  # Higher volatility
            elif category in ['Sports', 'Esports']:
                volatility = 0.004  # Medium volatility
            elif category in ['Economy', 'Weather']:
                volatility = 0.003
            else:
                volatility = 0.003  # Default
        
        # Drift: slight mean reversion for high probability bets
        if current_price > 0.7:
            drift = -0.0002  # Mean reversion for high prices
        elif current_price < 0.3:
            drift = 0.0002   # Mean reversion for low prices
        else:
            drift = 0.0001   # Neutral for mid-range
        
        total_change = 0
        for _ in range(minutes_ahead):
            change = random.gauss(drift, volatility)
            total_change += change
        
        return max(0.01, min(0.99, current_price + total_change))
    
    def open_bet(self, market):
        """Open a new bet with realistic bid-ask spread"""
        allowed, reason = self.can_open_bet()
        if not allowed:
            return None
        
        action, entry_prob = self.should_bet(market['prob_yes'])
        if not action or entry_prob is None or entry_prob == 0:
            return None
        
        if self.balance < self.bet_size:
            return None
        
        # Get real bid-ask from market data
        best_bid = market.get('best_bid', entry_prob)
        best_ask = market.get('best_ask', entry_prob)
        
        # Apply spread: buy at ask, sell at bid
        if action == 'YES':
            entry_price = best_ask  # Pay ask when buying YES
        else:
            entry_price = 1 - best_ask  # Pay ask for NO (which is 1 - ask of YES)
        
        # Adjust entry_prob based on actual paid price
        entry_prob = entry_price if action == 'YES' else (1 - entry_price)
        
        odds = 1/entry_prob if entry_prob > 0 else 1
        
        bet = {
            'market_id': market.get('id', ''),
            'question': market['question'],
            'action': action,
            'entry_price': entry_price,
            'entry_prob': entry_prob,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'amount': self.get_current_bet_size(),
            'odds': odds,
            'opened_at': datetime.now().isoformat(),
            'category': market.get('category', 'Other'),
            'url': market.get('url', '')
        }
        
        self.open_bets.append(bet)
        self._save_open_bets()
        return bet
    
    def resolve_bet(self, bet, exit_price, include_spread=True, slippage_pct=0.01):
        """Resolve a single bet with realistic bid-ask spread and slippage"""
        # Apply slippage to exit price
        if slippage_pct > 0:
            slippage = random.uniform(-slippage_pct, slippage_pct) * exit_price
            exit_price = max(0.01, min(0.99, exit_price + slippage))
        
        # Apply bid-ask spread at exit (selling at bid)
        if include_spread and 'best_bid' in bet:
            # When closing YES, we sell at bid
            if bet['action'] == 'YES':
                exit_price = bet.get('best_bid', exit_price)
            # When closing NO, we sell at bid (which is 1 - bid of YES)
            else:
                bid_for_yes = 1 - bet.get('best_bid', 1 - exit_price)
                exit_price = 1 - bid_for_yes
        
        won = False
        if bet['action'] == 'YES':
            won = exit_price > bet['entry_price']
        else:
            won = exit_price < (1 - bet['entry_price'])
        
        if won:
            gross_payout = bet['amount'] * (1/bet['entry_prob'] - 1)
            profit = gross_payout * (1 - POLYMARKET_FEE)  # 2% fee on winnings
            self.wins += 1
        else:
            profit = -bet['amount']
            self.losses += 1
        
        self.balance += profit
        
        trade = {
            'timestamp': datetime.now().isoformat(),
            'question': bet['question'][:40],
            'action': bet['action'],
            'odds': bet['odds'],
            'entry_price': bet['entry_prob'],
            'exit_price': exit_price,
            'bet_size': bet['amount'],
            'profit': profit,
            'balance': self.balance,
            'won': won,
            'category': bet['category'],
            'conditionId': bet.get('market_id', ''),
            'url': bet['url']
        }
        
        self.trades.append(trade)
        self._save_balance()
        self._log_trade(trade)
        return trade
    
    def resolve_all_bets(self, use_real_price=True, include_spread=True, slippage_pct=0.01):
        """Resolve all open bets - optionally fetch real price with spread and slippage"""
        resolved = []
        
        for bet in self.open_bets:
            market_id = bet.get('market_id', '')
            
            if use_real_price and market_id:
                market_data = fetch_full_market_data(market_id)
                if market_data:
                    exit_price = market_data.get('mid_price', bet['entry_price'])
                    # Update best_bid/ask in bet for spread calculation
                    bet['best_bid'] = market_data.get('best_bid', bet.get('best_bid'))
                    bet['best_ask'] = market_data.get('best_ask', bet.get('best_ask'))
                else:
                    print(f"⚠️ Could not fetch real price for {market_id[:20]}..., using last known")
                    exit_price = bet['entry_price']
            else:
                exit_price = bet['entry_price']
            
            trade = self.resolve_bet(bet, exit_price, include_spread=include_spread, slippage_pct=slippage_pct)
            resolved.append(trade)
        
        self.open_bets = []
        self._save_open_bets()
        return resolved
    
    def _log_trade(self, trade):
        """Log trade to file in structured JSON format for easy analysis"""
        # Log to human-readable file (keeping existing format for backwards compatibility)
        time_str = trade['timestamp']
        profit = trade['profit']
        profit_str = f"+${profit:.2f}" if profit >= 0 else f"-${abs(profit):.2f}"
        odds_str = f"{trade['odds']:.2f}x"
        result_str = "WIN" if trade['won'] else "LOSE"
        
        with open(self.log_folder / "trades.txt", "a") as f:
            f.write(f"[{time_str}] {trade['action']} {odds_str} | Bet: ${trade['bet_size']:.2f} | {result_str} | Profit: {profit_str} | Balance: ${trade['balance']:.2f} | Category: {trade['category']}\n")
        
        if not trade['won']:
            with open(self.log_folder / "loses.txt", "a") as f:
                f.write(f"[{time_str}] {trade['action']} {odds_str} | Bet: ${trade['bet_size']:.2f} | LOSE | Profit: {profit_str}\n")
        
        # ALSO log to structured JSON file for easy parsing and graphing
        structured_log = {
            "timestamp": trade['timestamp'],
            "trade_id": len(self.trades),  # Sequential ID
            "action": trade['action'],
            "category": trade['category'],
            "question": trade['question'],
            "odds": trade['odds'],
            "bet_size": trade['bet_size'],
            "entry_price": trade['entry_price'],
            "exit_price": trade['exit_price'],
            "profit": trade['profit'],
            "balance_after": trade['balance'],
            "won": trade['won'],
            "result": "WIN" if trade['won'] else "LOSE",
            "url": trade.get('url', '')
        }
        
        # Append to structured trades log
        structured_file = self.log_folder / "trades_structured.json"
        try:
            if structured_file.exists() and structured_file.stat().st_size > 10:
                try:
                    with open(structured_file, 'r') as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    print(f"⚠️ Corrupted JSON file, backing up and starting fresh")
                    backup_file = self.log_folder / f"trades_structured_backup_{datetime.now().strftime('%H%M%S')}.json"
                    structured_file.rename(backup_file)
                    data = []
            else:
                data = []
            
            data.append(structured_log)
            
            with open(structured_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing structured trade log: {e}")
    
    def _save_balance_snapshot(self):
        """Save periodic balance snapshot for time-series analysis"""
        try:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "balance": self.balance,
                "initial_balance": self.initial_balance,
                "total_profit": self.balance - self.initial_balance,
                "total_trades": len(self.trades),
                "wins": self.wins,
                "losses": self.losses,
                "win_rate": (self.wins / len(self.trades) * 100) if self.trades else 0,
                "open_bets_count": len(self.open_bets),
                "open_bets_value": sum(b['amount'] for b in self.open_bets)
            }
            
            # Append to balance history
            balance_file = SIMULATION_PATH / "balance_history.json"
            try:
                if balance_file.exists():
                    with open(balance_file, 'r') as f:
                        data = json.load(f)
                else:
                    data = []
                
                data.append(snapshot)
                
                # Keep only last 1000 entries to prevent file from growing too large
                if len(data) > 1000:
                    data = data[-1000:]
                
                with open(balance_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error writing balance snapshot: {e}")
        except Exception as e:
            print(f"Error in _save_balance_snapshot: {e}")
    
    def get_stats(self):
        """Get session statistics"""
        total_trades = len(self.trades)
        win_rate = (self.wins / total_trades * 100) if total_trades > 0 else 0
        total_profit = self.balance - self.initial_balance
        roi = (total_profit / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'balance': self.balance,
            'total_profit': total_profit,
            'roi': roi,
            'total_trades': total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'open_bets': len(self.open_bets),
            'open_amount': sum(b['amount'] for b in self.open_bets)
        }


_global_sim_session = None
_sim_thread = None
_sim_running = False
_sim_markets = []

def init_simulation(markets):
    """Initialize simulation with markets"""
    global _sim_markets
    _sim_markets = markets

def start_simulation(config):
    """Start simulation with given config"""
    global _global_sim_session, _sim_thread, _sim_running
    
    if _sim_running:
        return {"error": "Simulation already running"}
    
    sim = SimulationSession(
        initial_balance=config.get('initial_balance', 100.0),
        bet_size=config.get('bet_size', 2.0),
        bet_size_pct=config.get('bet_size_pct', 0.02),
        min_prob=config.get('min_prob', 0.70),
        max_open_bets=config.get('max_open_bets', 10),
        max_open_pct=config.get('max_open_pct', 0.30),
        category=config.get('category', None)
    )
    
    _global_sim_session = sim
    _sim_running = True
    save_sim_state(True)
    
    _sim_thread = threading.Thread(target=_run_simulation_loop, args=(config,))
    _sim_thread.daemon = True
    _sim_thread.start()
    
    return {
        "status": "started",
        "initial_balance": sim.initial_balance,
        "balance": sim.balance
    }

def stop_simulation():
    """Stop simulation"""
    global _sim_running, _global_sim_session
    
    if not _sim_running:
        return {"error": "Simulation not running"}
    
    _sim_running = False
    save_sim_state(False)
    
    if _global_sim_session:
        _global_sim_session._save_balance()
    
    return {"status": "stopped"}

def _run_simulation_loop(config):
    """Run simulation in background"""
    global _global_sim_session, _sim_running
    
    if not _global_sim_session:
        return
    
    sim = _global_sim_session
    minutes = config.get('minutes', 1)
    max_bets = config.get('max_bets', 10)
    
    markets = _sim_markets
    market_idx = 0
    
    def fill_open_bets():
        nonlocal market_idx
        target = sim.balance * sim.max_open_pct
        filled = 0
        
        while sum(b['amount'] for b in sim.open_bets) < target and markets:
            market = markets[market_idx % len(markets)]
            
            if sim.balance < sim.get_current_bet_size():
                break
            
            bet = sim.open_bet(market)
            if bet:
                filled += 1
                market_idx += 1
                
                if filled >= max_bets:
                    break
            
            if filled >= 10:
                break
        
        return filled
    
    last_snapshot_time = time.time()
    snapshot_interval = 10  # Save balance snapshot every 10 seconds
    
    # Save initial snapshot immediately
    sim._save_balance_snapshot()
    
    while _sim_running:
        try:
            if sim.open_bets:
                resolved = sim.resolve_all_bets(use_real_price=True, include_spread=True, slippage_pct=0.01)
            
            fill_open_bets()
            
            # Periodically save balance snapshot for time-series analysis
            current_time = time.time()
            if current_time - last_snapshot_time >= snapshot_interval:
                sim._save_balance_snapshot()
                last_snapshot_time = current_time
                
        except Exception as e:
            print(f"Error in simulation loop: {e}")
        
        time.sleep(minutes * 60 if minutes > 1 else 1)
    
    # Final balance snapshot when simulation stops
    sim._save_balance_snapshot()
    sim._save_balance()

def get_simulation_status():
    """Get current simulation status"""
    if _sim_running and _global_sim_session:
        return {
            "running": True,
            "balance": _global_sim_session.balance,
            "stats": _global_sim_session.get_stats(),
            "open_bets": _global_sim_session.open_bets,
            "trades": _global_sim_session.trades[-20:]
        }
    
    # Try to load from files
    balance = 0
    stats = {}
    
    balance_file = SIMULATION_PATH / "balance.txt"
    if balance_file.exists():
        try:
            with open(balance_file, 'r') as f:
                balance = float(f.read().strip())
        except:
            pass
    
    hourly_file = SIMULATION_PATH / "hourly_stats.json"
    if hourly_file.exists():
        try:
            with open(hourly_file, 'r') as f:
                hourly_data = json.load(f)
                if hourly_data:
                    latest = hourly_data[-1]
                    stats = {
                        'initial_balance': latest.get('initial_balance', 100),
                        'balance': latest.get('balance', balance),
                        'total_profit': latest.get('total_profit', 0),
                        'total_trades': latest.get('trades', 0),
                        'wins': latest.get('wins', 0),
                        'losses': latest.get('losses', 0),
                    }
                    if stats.get('total_trades', 0) > 0:
                        stats['win_rate'] = (stats['wins'] / stats['total_trades'] * 100)
        except:
            pass
    
    # Load open bets
    open_bets = []
    today = datetime.now().strftime('%d-%m-%Y')
    open_file = SIMULATION_PATH / today / "open_bets.json"
    if open_file.exists():
        try:
            with open(open_file, 'r') as f:
                open_bets = json.load(f)
        except:
            pass
    
    return {
        "running": False,
        "balance": balance,
        "stats": stats,
        "open_bets": open_bets,
        "trades": []
    }

def reset_simulation():
    """Reset simulation balance and history"""
    global _sim_running, _global_sim_session
    
    # Stop simulation if running
    _sim_running = False
    _global_sim_session = None
    
    # Delete state file
    if SIM_STATE_FILE.exists():
        SIM_STATE_FILE.unlink()
    
    # Delete balance file
    balance_file = SIMULATION_PATH / "balance.txt"
    if balance_file.exists():
        balance_file.unlink()
    
    # Delete balance history for chart
    balance_history = SIMULATION_PATH / "balance_history.json"
    if balance_history.exists():
        balance_history.unlink()
    
    # Delete hourly stats
    hourly_file = SIMULATION_PATH / "hourly_stats.json"
    if hourly_file.exists():
        hourly_file.unlink()
    
    # Delete all trade logs
    if SIMULATION_PATH.exists():
        for item in SIMULATION_PATH.iterdir():
            if item.is_dir():
                for f in item.iterdir():
                    if f.name in ['trades.txt', 'open_bets.json', 'summary.txt', 'loses.txt']:
                        try:
                            f.unlink()
                        except:
                            pass
                # Remove empty directory
                try:
                    if not any(item.iterdir()):
                        item.rmdir()
                except:
                    pass
    
    return {"status": "reset", "message": "Simulation reset successfully"}


def load_simulation_from_logs():
    """Load simulation history from log files"""
    import re
    trades = []
    
    if not SIMULATION_PATH.exists():
        return trades
    
    def parse_json_file(path):
        """Try to parse JSON file, skip if corrupted"""
        if not path.exists() or path.stat().st_size < 10:
            return []
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return []
    
    # First try to load from structured JSON
    try:
        for folder in SIMULATION_PATH.iterdir():
            if not folder.is_dir():
                continue
            structured_file = folder / "trades_structured.json"
            data = parse_json_file(structured_file)
            if data:
                trades.extend(data)
    except Exception as e:
        print(f"Error loading structured simulation logs: {e}")
    
    # Fallback to text logs - parse with category
    if not trades:
        try:
            import re
            # Updated pattern to capture category
            log_pattern = re.compile(
                r'\[(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\]]*)\] '
                r'(YES|NO) ([\d.]+)x \| '
                r'Bet: \$([\d.]+) \| '
                r'(WIN|LOSE) \| '
                r'Profit: ([^\|]+)'
                r'(?: \| Category: ([^\n]+))?'
            )
            
            for folder in SIMULATION_PATH.iterdir():
                if not folder.is_dir():
                    continue
                
                trades_file = folder / "trades.txt"
                if not trades_file.exists():
                    continue
                
                with open(trades_file, 'r') as f:
                    for line in f:
                        match = log_pattern.match(line.strip())
                        if match:
                            groups = match.groups()
                            ts = groups[0]
                            action = groups[1]
                            odds = groups[2]
                            bet = groups[3]
                            result = groups[4]
                            profit = groups[5]
                            category = groups[6] if len(groups) > 6 and groups[6] else 'Other'
                            profit_val = float(profit.replace('+', '').replace('$', '').strip())
                            
                            
                            trades.append({
                                'timestamp': ts,
                                'action': action,
                                'odds': float(odds),
                                'bet_size': float(bet),
                                'result': result,
                                'profit': profit_val,
                                'won': result == 'WIN',
                                'category': category
                            })
        except Exception as e:
            print(f"Error loading simulation logs: {e}")
    
    return trades


def get_simulation_history():
    """Get all simulation history from logs"""
    return load_simulation_from_logs()