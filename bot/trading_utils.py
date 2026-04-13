"""
Shared trading utilities for Polymarket
Used by both simulation and real trading
"""
import os
import sys
import random
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.market import fetch_markets, get_current_price


CATEGORIES = {
    "1": "Sports", "2": "Politics", "3": "Crypto",
    "4": "Economy", "5": "Tech", "6": "Culture",
    "7": "Weather", "8": "Esports"
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


def get_category_from_question(question, group):
    """Detect category from question and group"""
    question = question.lower()
    group = group.lower()
    
    for cat_name, keywords in KEYWORDS.items():
        if any(kw.lower() in question for kw in keywords):
            return cat_name
        if any(kw.lower() in group for kw in keywords):
            return cat_name
    return "Other"


def filter_markets(markets, category=None, min_volume=1000):
    """Filter markets by category and volume"""
    eligible = []
    
    for m in markets:
        prices = get_current_price(m)
        if not prices:
            continue
        
        question = m.get('question', '')
        group = m.get('groupItemTitle', '')
        
        if category and category not in ['all', 'a']:
            keywords = KEYWORDS.get(category, [])
            if keywords:
                q_lower = question.lower()
                g_lower = group.lower()
                if not any(kw.lower() in q_lower for kw in keywords):
                    if not any(kw.lower() in g_lower for kw in keywords):
                        continue
        
        vol = float(m.get('volume', 0))
        if vol < min_volume:
            continue
        
        mid_price = prices['mid_price']
        detected_cat = get_category_from_question(question, group)
        
        eligible.append({
            'id': m['id'],
            'question': question,
            'slug': m.get('slug', ''),
            'category': detected_cat,
            'entry_price': mid_price,
            'prob_yes': mid_price,
            'volume': vol,
            'best_bid': prices['best_bid'],
            'best_ask': prices['best_ask'],
            'spread': prices.get('spread', 0),
            'url': f"https://polymarket.com/market/{m.get('slug', m['id'])}"
        })
    
    return eligible


def get_high_probability_markets(markets, min_prob=0.70):
    """Get markets with high probability"""
    high_prob = []
    min_prob_value = min_prob
    max_prob_value = 1 - min_prob
    
    for m in markets:
        if m['prob_yes'] >= min_prob_value:
            m['action'] = 'YES'
            m['action_prob'] = m['prob_yes']
            high_prob.append(m)
        elif m['prob_yes'] <= max_prob_value:
            m['action'] = 'NO'
            m['action_prob'] = 1 - m['prob_yes']
            high_prob.append(m)
    
    return high_prob


def simulate_future_price(current_price, minutes_ahead, volatility=0.003):
    """Simulate future price movement - realistic market simulation"""
    # Less mean reversion, more random walk with slight upward bias for high prob
    drift = 0.0005  # Small positive drift (markets tend up slightly)
    total_change = 0
    for _ in range(minutes_ahead):
        change = random.gauss(drift, volatility)
        total_change += change
    return max(0.01, min(0.99, current_price + total_change))


class BettingSession:
    """Base class for betting sessions"""
    
    def __init__(self, initial_balance=100.0, bet_size=2.0, bet_size_pct=0.02, min_prob=0.70, 
                 max_open_bets=10, max_open_pct=0.30, category=None, log_folder=None):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.bet_size = bet_size
        self.bet_size_pct = bet_size_pct
        self.min_prob = min_prob
        self.category = category
        self.log_folder = log_folder
        
        self.max_open_bets = max_open_bets
        self.max_open_pct = max_open_pct
        
        self.trades = []
        self.open_bets = []
        self.wins = 0
        self.losses = 0
    
    def get_max_open_amount(self):
        """Get max open amount based on current balance"""
        return self.balance * self.max_open_pct
    
    def get_current_bet_size(self):
        """Calculate current bet size based on compound percentage"""
        return max(self.bet_size, self.balance * self.bet_size_pct)
    
    def can_open_bet(self):
        """Check if we can open a new bet - only based on percentage"""
        total_open = sum(b['amount'] for b in self.open_bets)
        max_allowed = self.get_max_open_amount()
        if total_open >= max_allowed:
            return False, "Max open amount reached"
        
        return True, "OK"
    
    def should_bet(self, prob_yes):
        """Check if probability is high enough to bet"""
        if prob_yes >= self.min_prob:
            return 'YES', prob_yes
        elif prob_yes <= (1 - self.min_prob):
            return 'NO', 1 - prob_yes
        return None, 0
    
    def open_bet(self, market):
        """Open a new bet - override in subclass for real trading"""
        allowed, reason = self.can_open_bet()
        if not allowed:
            return None
        
        action, entry_prob = self.should_bet(market['prob_yes'])
        if not action:
            return None
        
        current_bet_size = self.get_current_bet_size()
        if self.balance < current_bet_size:
            return None
        
        bet = {
            'market_id': market.get('id', ''),
            'question': market['question'],
            'action': action,
            'entry_price': market['entry_price'],
            'entry_prob': entry_prob,
            'amount': current_bet_size,
            'odds': 1/entry_prob if action == 'YES' else 1/(1-entry_prob),
            'opened_at': datetime.now(),
            'category': market.get('category', 'Other'),
            'url': market.get('url', '')
        }
        
        self.open_bets.append(bet)
        return bet
    
    def resolve_bet(self, bet, exit_price):
        """Resolve a single bet - override in subclass for real trading"""
        won = False
        if bet['action'] == 'YES':
            won = exit_price > bet['entry_price']
        else:
            won = exit_price < (1 - bet['entry_price'])
        
        if won:
            profit = bet['amount'] * (1/bet['entry_prob'] - 1)
            self.wins += 1
        else:
            profit = -bet['amount']
            self.losses += 1
        
        self.balance += profit
        
        trade = {
            'timestamp': datetime.now(),
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
            'url': bet['url'],
            'market_id': bet['market_id']
        }
        
        self.trades.append(trade)
        return trade
    
    def resolve_all_bets(self, minutes=1):
        """Resolve all open bets after waiting period"""
        resolved = []
        
        for bet in self.open_bets:
            exit_price = simulate_future_price(bet['entry_price'], minutes)
            trade = self.resolve_bet(bet, exit_price)
            resolved.append(trade)
        
        self.open_bets = []
        return resolved
    
    def get_stats(self):
        """Get session statistics"""
        total_trades = len(self.trades)
        win_rate = (self.wins / total_trades * 100) if total_trades > 0 else 0
        total_profit = self.balance - self.initial_balance
        
        released_pnl = sum(t['profit'] for t in self.trades)
        floating_pnl = 0
        for bet in self.open_bets:
            if bet['action'] == 'YES':
                unrealized = bet['amount'] * (1 - bet['entry_prob'])
            else:
                unrealized = bet['amount'] * (bet['entry_prob'])
            floating_pnl += unrealized
        
        roi = (total_profit / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'balance': self.balance,
            'total_profit': total_profit,
            'released_pnl': released_pnl,
            'floating_pnl': floating_pnl,
            'running_pnl': released_pnl + floating_pnl,
            'roi': roi,
            'total_trades': total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'open_bets': len(self.open_bets)
        }