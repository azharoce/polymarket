"""
Bot Controller - manages bot running state and modes
Supports persistent state across restarts + background thread execution
"""

import threading
import time
import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("bot_state.json")

class BotController:
    def __init__(self):
        self.running = False
        self.mode = "stopped"
        self.initial_balance = 100.0
        self.balance = 100.0
        self.trades = []
        self.start_time = None
        self.thread = None
        self._autobot = None
        self._stop_event = threading.Event()
        
        self._load_state()
    
    def _load_state(self):
        """Load state from file if exists"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.mode = data.get('mode', 'stopped')
                    self.initial_balance = data.get('initial_balance', 100.0)
                    self.balance = data.get('balance', 100.0)
                    self.running = data.get('running', False)
                    self.start_time = datetime.fromisoformat(data['start_time']) if data.get('start_time') else None
                    # Load bot configuration
                    bot_config = data.get('bot_config', {})
                    self._min_prob = bot_config.get('min_prob', 0.70)
                    self._max_losses = bot_config.get('max_losses', 5)
                    self._bet_pct = bot_config.get('bet_pct', 0.1)
                    self._min_volume = bot_config.get('min_volume', 1000)
                    self._interval = bot_config.get('interval', 60)
                    
                    if self.running:
                        self.running = False
                        self.mode = 'stopped'
                        print(f"⚠️ Bot was running before restart. Stopped for safety.")
                
                print(f"✅ Loaded state: mode={self.mode}, balance=${self.balance:.2f}")
            except Exception as e:
                print(f"⚠️ Failed to load state: {e}")
    
    def _save_state(self):
        """Save current state to file"""
        data = {
            'mode': self.mode,
            'initial_balance': self.initial_balance,
            'balance': self.balance,
            'running': self.running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'total_trades': len(self.trades),
            'bot_config': {
                'min_prob': getattr(self, '_min_prob', 0.70),
                'max_losses': getattr(self, '_max_losses', 5),
                'bet_pct': getattr(self, '_bet_pct', 0.1),
                'min_volume': getattr(self, '_min_volume', 1000),
                'interval': getattr(self, '_interval', 60)
            }
        }
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save state: {e}")
        
        # Also save human-readable config file
        self._save_config_file()
    
    def _save_config_file(self):
        """Save current bot config to human-readable file"""
        try:
            config_lines = [
                "# Bot Configuration File",
                f"mode={self.mode}",
                f"initial_balance={self.initial_balance}",
                f"current_balance={self.balance}",
                f"running={str(self.running).lower()}",
                "",
                "# Strategy Parameters",
                f"min_prob={getattr(self, '_min_prob', 0.70)}",
                f"max_losses={getattr(self, '_max_losses', 5)}",
                f"bet_pct={getattr(self, '_bet_pct', 0.1)}",
                f"min_volume={getattr(self, '_min_volume', 1000)}",
                f"interval={getattr(self, '_interval', 60)}",
                "",
                f"# Last updated: {datetime.now().isoformat()}"
            ]
            
            with open("bot_config.txt", "w") as f:
                f.write("\n".join(config_lines))
        except Exception as e:
            print(f"⚠️ Failed to save config file: {e}")
    
    def _run_loop(self):
        """Background loop for scan & trade"""
        from bot.autobet import AutoBetBot, scan_and_trade
        
        self._autobot = AutoBetBot(
            initial_balance=self.initial_balance,
            min_prob=getattr(self, '_min_prob', 0.70),
            max_consecutive_losses=getattr(self, '_max_losses', 5),
            base_bet_pct=getattr(self, '_bet_pct', 0.1),
            simulate=(self.mode == "simulation"),
            min_volume=getattr(self, '_min_volume', 1000)
        )
        
        if not self._autobot.initialize():
            self.running = False
            self.mode = "stopped"
            self._save_state()
            return
        
        interval = getattr(self, '_interval', 60)
        scan_count = 0
        
        while not self._stop_event.is_set():
            try:
                scan_count += 1
                print(f"\n=== SCAN #{scan_count} ===")
                
                scan_and_trade(self._autobot, min_volume=getattr(self, '_min_volume', 1000), simulation_id=scan_count)
                
                self.balance = self._autobot.balance
                
                for trade in self._autobot.trades[-5:]:
                    self.trades.append(trade)
                
                self._save_state()
                
                if self._stop_event.wait(interval):
                    break
                    
            except Exception as e:
                print(f"Error in bot loop: {e}")
                time.sleep(interval)
        
        self._autobot = None
    
    def start(self, mode="simulation", initial_balance=100.0, min_prob=0.70, 
              max_losses=5, bet_pct=0.1, min_volume=1000, interval=60):
        if self.running:
            return {"error": "Bot already running"}
        
        self.mode = mode
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.running = True
        self.start_time = datetime.now()
        
        self._min_prob = min_prob
        self._max_losses = max_losses
        self._bet_pct = bet_pct
        self._min_volume = min_volume
        self._interval = interval
        
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # Save initial state and config
        self._save_state()
        
        return {
            "status": "started",
            "mode": mode,
            "initial_balance": initial_balance,
            "balance": self.balance,
            "min_prob": min_prob,
            "max_losses": max_losses,
            "bet_pct": bet_pct,
            "min_volume": min_volume,
            "interval": interval
        }
    
    def stop(self):
        if not self.running:
            return {"error": "Bot not running"}
        
        self._stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5)
        
        self.running = False
        self.mode = "stopped"
        self._autobot = None
        self._save_state()
        
        return {
            "status": "stopped",
            "mode": "stopped"
        }
    
    def add_trade(self, trade_data):
        trade = {
            "time": datetime.now().isoformat(),
            "mode": self.mode,
            "market": trade_data.get("market", ""),
            "side": trade_data.get("side", ""),
            "size": trade_data.get("size", 0),
            "price": trade_data.get("price", 0),
            "total": trade_data.get("total", 0),
            "result": trade_data.get("result", ""),
            "profit": trade_data.get("profit", 0)
        }
        self.trades.append(trade)
        
        if self.mode == "simulation":
            self.balance += trade.get("profit", 0)
            self._save_state()
        
        return trade
    
    def update_balance(self, new_balance):
        """Update balance during bot run"""
        self.balance = new_balance
        self._save_state()
    
    def get_status(self):
        return {
            "running": self.running,
            "mode": self.mode,
            "initial_balance": self.initial_balance,
            "current_balance": self.balance,
            "total_trades": len(self.trades),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "total_profit": sum(t.get("profit", 0) for t in self.trades),
            "config": {
                "min_prob": getattr(self, '_min_prob', 0.70),
                "max_losses": getattr(self, '_max_losses', 5),
                "bet_pct": getattr(self, '_bet_pct', 0.1),
                "min_volume": getattr(self, '_min_volume', 1000),
                "interval": getattr(self, '_interval', 60)
            }
        }
    
    def get_trades(self, limit=50):
        return self.trades[-limit:] if self.trades else []

    def get_autobot(self):
        """Get the running AutoBetBot instance"""
        return self._autobot

bot = BotController()

LOG_DIR = Path("autobet_logs")
LOG_DIR.mkdir(exist_ok=True)

def save_trade_log(trade):
    """Save trade to log file"""
    now = datetime.now()
    date_str = now.strftime('%d-%m-%Y')
    hour_str = now.strftime('%H')
    
    log_path = LOG_DIR / date_str / hour_str
    log_path.mkdir(parents=True, exist_ok=True)
    
    minute_str = now.strftime('%M')
    filename = f"{minute_str}.txt"
    
    with open(log_path / filename, "a") as f:
        trade_str = f"{trade['side']} ${trade['size']:.2f} @ ${trade['price']:.2f} | {trade['result']} | Profit: ${trade['profit']:.2f}"
        f.write(f"[{now.strftime('%H:%M:%S')}] {trade_str}\n")