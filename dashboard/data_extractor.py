"""
Data extraction module for Polymarket Trading Bot Dashboard
Handles parsing of trade log files and summary files
"""
import os
import re
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional


class TradeLogExtractor:
    """Extracts trade data from log files"""
    
    def __init__(self, base_path: str = "simulation"):
        self.base_path = Path(base_path)
        self.log_pattern = re.compile(
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] '
            r'(YES|NO) ([\d.]+)x \| '
            r'Bet: \$([\d.]+) \| '
            r'(WIN|LOSE) \| '
            r'Profit: ([^\|]+) \| '
            r'Balance: \$([\d.]+) \| '
            r'Category: ([^|]+) \| '
            r'URL: (.+)'
        )
    
    def extract_from_file(self, filepath: Path) -> List[dict]:
        """Extract trade data from a single log file"""
        trades = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    match = self.log_pattern.match(line.strip())
                    if match:
                        timestamp_str, action, odds, bet, result, profit, balance, category, url = match.groups()
                        profit_clean = profit.replace('+', '').replace('$', '').strip()
                        question = url.split('/')[-1].replace('-', ' ').replace('.', ' ')[:50] if url else 'N/A'
                        trades.append({
                            'timestamp': datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S'),
                            'question': question,
                            'action': action,
                            'odds': float(odds),
                            'bet': float(bet),
                            'result': result,
                            'profit': float(profit_clean),
                            'balance': float(balance),
                            'category': category.strip(),
                            'url': url.strip(),
                            'won': result == 'WIN',
                            'entry_price': 0.5,
                            'exit_price': 0.5
                        })
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
        return trades
    
    def extract_all_trades(self) -> pd.DataFrame:
        """Extract all trade data from simulation directory"""
        all_trades = []
        
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file.endswith('.txt') and file not in ['summary.txt', 'config.txt', 'daily.log', 'open_bets.json']:
                    filepath = Path(root) / file
                    trades = self.extract_from_file(filepath)
                    all_trades.extend(trades)
        
        if not all_trades:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_trades)
        df = df.sort_values('timestamp').reset_index(drop=True)
        df['cumulative_profit'] = df['profit'].cumsum()
        df['trade_number'] = range(1, len(df) + 1)
        
        return df
    
    def extract_daily_summary(self, date_str: Optional[str] = None) -> pd.DataFrame:
        """Extract daily summary data - returns trade data for visualization"""
        if date_str is None:
            date_str = datetime.now().strftime('%d-%m-%Y')
        
        trades_path = self.base_path / date_str / "trades.txt"
        if not trades_path.exists():
            return pd.DataFrame()
        
        trades = self.extract_from_file(trades_path)
        if not trades:
            return pd.DataFrame()
        
        df = pd.DataFrame(trades)
        df = df.sort_values('timestamp').reset_index(drop=True)
        df['cumulative_profit'] = df['profit'].cumsum()
        df['trade_number'] = range(1, len(df) + 1)
        
        return df
    
    def extract_simulation_trades(self, date_str: Optional[str] = None) -> pd.DataFrame:
        """Extract trades from trades.txt file"""
        return self.extract_daily_summary(date_str)
    
    def get_open_bets(self, date_str: Optional[str] = None) -> List[dict]:
        """Get open simulation bets"""
        if date_str is None:
            date_str = datetime.now().strftime('%d-%m-%Y')
        
        open_bets_path = self.base_path / date_str / "open_bets.json"
        if not open_bets_path.exists():
            return []
        
        try:
            with open(open_bets_path, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def save_open_bets(self, open_bets: List[dict], date_str: Optional[str] = None):
        """Save open bets to file"""
        if date_str is None:
            date_str = datetime.now().strftime('%d-%m-%Y')
        
        folder = self.base_path / date_str
        folder.mkdir(parents=True, exist_ok=True)
        
        open_bets_path = folder / "open_bets.json"
        with open(open_bets_path, 'w') as f:
            json.dump(open_bets, f)
    
    def get_bet_history(self, date_str: Optional[str] = None) -> pd.DataFrame:
        """Get all bet history"""
        return self.extract_simulation_trades(date_str)


def get_latest_balance(df: pd.DataFrame) -> float:
    """Get the latest balance from trade data"""
    if df.empty:
        return 100.0
    return float(df['balance'].iloc[-1])


def get_total_profit(df: pd.DataFrame) -> float:
    """Get total profit from trade data"""
    if df.empty:
        return 0.0
    return float(df['profit'].sum())


def get_win_rate(df: pd.DataFrame) -> float:
    """Calculate win rate percentage"""
    if df.empty:
        return 0.0
    wins = (df['result'] == 'WIN').sum()
    total = len(df)
    return float((wins / total) * 100) if total > 0 else 0.0


def get_daily_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Get daily statistics from trade data"""
    if df.empty:
        return pd.DataFrame()
    
    df_copy = df.copy()
    df_copy['date'] = pd.to_datetime(df_copy['timestamp']).dt.date
    
    daily = df_copy.groupby('date').agg({
        'profit': 'sum',
        'result': 'count'
    }).reset_index()
    
    daily.columns = ['date', 'total_profit', 'trade_count']
    daily['cumulative_profit'] = daily['total_profit'].cumsum()
    
    return daily