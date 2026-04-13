import os
import time
from datetime import datetime, timedelta
from bot.config import Config, logger

class RiskManager:
    def __init__(self, starting_balance: float):
        self.starting_balance = starting_balance
        self.current_balance = starting_balance
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.last_reset = datetime.utcnow()
    
    def can_trade(self) -> tuple[bool, str]:
        now = datetime.utcnow()
        if (now - self.last_reset) > timedelta(days=1):
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset = now
            logger.info("Daily stats reset")
        
        if self.daily_pnl < 0 and abs(self.daily_pnl) >= self.starting_balance * Config.MAX_DAILY_LOSS:
            return False, "Max daily loss reached"
        
        if self.consecutive_losses >= Config.MAX_CONSECUTIVE_LOSSES:
            return False, "Max consecutive losses reached"
        
        return True, "OK"
    
    def calculate_position_size(self, balance: float, confidence: float) -> float:
        base_size = balance * Config.MAX_POSITION_SIZE
        adjusted_size = base_size * confidence
        return min(adjusted_size, balance * Config.MAX_POSITION_SIZE)
    
    def record_trade(self, profit: float):
        self.total_trades += 1
        self.daily_pnl += profit
        self.daily_trades += 1
        self.current_balance += profit
        
        if profit > 0:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1
        
        logger.info(f"Trade recorded: profit={profit}, daily_pnl={self.daily_pnl}, balance={self.current_balance}")
    
    def get_stats(self) -> dict:
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        return {
            "current_balance": self.current_balance,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "total_trades": self.total_trades,
            "win_rate": f"{win_rate:.2f}%",
            "consecutive_losses": self.consecutive_losses
        }

risk_manager = None

def initialize_risk(starting_balance: float):
    global risk_manager
    risk_manager = RiskManager(starting_balance)
    logger.info(f"Risk manager initialized with balance: {starting_balance}")

def can_trade() -> tuple[bool, str]:
    return risk_manager.can_trade()

def calculate_position_size(balance: float, confidence: float) -> float:
    return risk_manager.calculate_position_size(balance, confidence)

def record_trade(profit: float):
    risk_manager.record_trade(profit)

def get_risk_stats() -> dict:
    return risk_manager.get_stats()
