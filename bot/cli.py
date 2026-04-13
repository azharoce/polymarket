import os
import sys
import time
from datetime import datetime
from bot.auth import load_wallet
from bot.market import fetch_markets, get_current_price, fetch_active_markets
from bot.risk import initialize_risk, can_trade, calculate_position_size, get_risk_stats
from bot.trading import execute_trade
from dotenv import load_dotenv

load_dotenv()

class InteractiveBot:
    def __init__(self):
        self.wallet = None
        self.balance = 0.0
        self.positions = []
        self.trade_history = []
        self.current_tab = "markets"
        
    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self, title):
        print(f"\n╔{'='*78}╗")
        print(f"║ {title:^76} ║")
        print(f"╚{'='*78}╝")
    
    def print_tabs(self):
        tabs = {
            "markets": "📊 Markets",
            "signals": "🔍 Signals", 
            "trading": "🎯 Trading",
            "positions": "💼 Positions",
            "history": "📜 History",
            "wallet": "👛 Wallet",
            "risk": "⚠️ Risk"
        }
        
        print("\n┌" + "─"*20 + "┬" + "─"*15 + "┬" + "─"*12 + "┬" + "─"*10 + "┐")
        
        tab_str = ""
        for i, (key, label) in enumerate(tabs.items()):
            if key == self.current_tab:
                tab_str += f"│ {label:^18} "
            else:
                tab_str += f"│ {label:^18} "
        
        tab_str = tab_str[:-1] + "│"
        print(tab_str)
        print("└" + "─"*20 + "┴" + "─"*15 + "┴" + "─"*12 + "┴" + "─"*10 + "┘")
    
    def print_status_bar(self):
        if self.wallet:
            addr = f"{self.wallet.address[:6]}...{self.wallet.address[-4:]}"
        else:
            addr = "Not connected"
        
        print(f"\n💰 Balance: ${self.balance:.2f} | 📍 {addr} | 🕐 {datetime.now().strftime('%H:%M:%S')}")
        print("─"*80)
    
    def init_wallet(self):
        self.wallet = load_wallet()
        if self.wallet:
            from bot.backtest import get_wallet_balance
            info = get_wallet_balance()
            if info:
                self.balance = info.get('usdc_balance', 0)
        else:
            self.balance = 1000.0
    
    def tab_markets(self):
        self.print_header("ACTIVE MARKETS")
        markets = fetch_markets(limit=30)
        
        print(f"\n{'No':<4} {'Market':<50} {'Bid':<8} {'Ask':<8} {'Volume':<12}")
        print("─"*90)
        
        for i, m in enumerate(markets[:25], 1):
            prices = get_current_price(m)
            q = m.get("question", "N/A")[:48]
            
            if prices:
                bid = f"{prices['best_bid']:.2f}"
                ask = f"{prices['best_ask']:.2f}"
            else:
                bid = "N/A"
                ask = "N/A"
            
            vol = m.get("volume", "0")
            try:
                volume = f"${float(vol):,.0f}"
            except:
                volume = "$0"
            
            print(f"{i:<4} {q:<50} {bid:<8} {ask:<8} {volume:<12}")
    
    def tab_signals(self):
        self.print_header("TRADING SIGNALS")
        markets = fetch_active_markets(min_liquidity=10000)
        
        signals = []
        for m in markets:
            prices = get_current_price(m)
            if not prices:
                continue
            
            mid = prices['mid_price']
            q = m.get("question", "N/A")[:40]
            
            if mid < 0.05:
                signal = "BUY 🟢"
                conf = 1.0 - mid
            elif mid > 0.95:
                signal = "SELL 🔴"
                conf = mid
            else:
                continue
            
            signals.append({
                "market": q,
                "mid": mid,
                "signal": signal,
                "confidence": conf,
                "id": m.get("id")
            })
        
        if not signals:
            print("\n⚠️  Tidak ada sinyal trading ditemukan")
            return
        
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        print(f"\n{'Market':<45} {'Mid':<8} {'Signal':<15} {'Confidence'}")
        print("─"*80)
        
        for s in signals[:15]:
            print(f"{s['market']:<45} {s['mid']:.4f}   {s['signal']:<15} {s['confidence']:.2%}")
    
    def tab_trading(self):
        self.print_header("PLACE ORDER")
        
        markets = fetch_markets(limit=20)
        
        print("\nPilih market untuk trade:")
        print(f"{'No':<4} {'Market':<60} {'Volume'}")
        print("─"*80)
        
        for i, m in enumerate(markets, 1):
            q = m.get("question", "N/A")[:58]
            vol = m.get("volume", "0")
            try:
                volume = f"${float(vol):,.0f}"
            except:
                volume = "$0"
            print(f"{i:<4} {q:<60} {volume}")
        
        try:
            choice = input("\nPilih nomor market (Enter cancel): ").strip()
            if not choice:
                return
            idx = int(choice) - 1
            if idx < 0 or idx >= len(markets):
                return
            market = markets[idx]
        except:
            return
        
        prices = get_current_price(market)
        if not prices:
            print("❌ Gagal mengambil harga")
            return
        
        print(f"\n📌 Market: {market.get('question')}")
        print(f"💰 Bid: {prices['best_bid']:.4f} | Ask: {prices['best_ask']:.4f} | Mid: {prices['mid_price']:.4f}")
        
        mid = prices['mid_price']
        if mid < 0.05:
            side = "BUY"
        elif mid > 0.95:
            side = "SELL"
        else:
            side = "HOLD"
        
        print(f"📊 Signal: {side}")
        
        if side == "HOLD":
            print("⚠️  Probability tidak memenuhi criteria trading")
            return
        
        try:
            size = input(f"\nMasukkan amount USDC (default 10): ").strip()
            size = float(size) if size else 10.0
        except:
            size = 10.0
        
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        
        if dry_run:
            print(f"\n✅ [DRY RUN] Would {side} ${size:.2f} at {mid:.4f}")
        else:
            print(f"\n⏳ Executing {side} order...")
            result = execute_trade(market['id'], side, mid, size)
            if result and result.get('success'):
                print(f"✅ Order placed successfully!")
                self.trade_history.append({
                    "market": market.get('question')[:40],
                    "side": side,
                    "price": mid,
                    "size": size,
                    "time": datetime.now()
                })
            else:
                print(f"❌ Order failed")
    
    def tab_positions(self):
        self.print_header("OPEN POSITIONS")
        
        if not self.positions:
            print("\n📭 Tidak ada open positions")
            return
        
        print(f"\n{'Market':<45} {'Side':<6} {'Entry':<8} {'Size':<10} {'PnL'}")
        print("─"*85)
        
        for p in self.positions:
            print(f"{p['market']:<45} {p['side']:<6} {p['entry']:.4f}   ${p['size']:.2f}    ${p['pnl']:.2f}")
    
    def tab_history(self):
        self.print_header("TRADE HISTORY")
        
        if not self.trade_history:
            print("\n📭 Tidak ada trade history")
            return
        
        print(f"\n{'Time':<20} {'Market':<35} {'Side':<6} {'Price':<8} {'Size'}")
        print("─"*85)
        
        for t in self.trade_history[-10:]:
            time_str = t['time'].strftime('%Y-%m-%d %H:%M')
            print(f"{time_str:<20} {t['market']:<35} {t['side']:<6} {t['price']:.4f}   ${t['size']:.2f}")
    
    def tab_wallet(self):
        self.print_header("WALLET INFO")
        
        if self.wallet:
            print(f"\n📍 Address: {self.wallet.address}")
            print(f"💰 USDC Balance: ${self.balance:.2f}")
            print(f"🌐 Network: Polygon")
            print(f"\n⚠️  Deposit USDC ke address di atas untuk trading")
        else:
            print("\n❌ Wallet tidak terhubung")
    
    def tab_risk(self):
        self.print_header("RISK MANAGEMENT")
        
        stats = get_risk_stats()
        
        print(f"\n💵 Current Balance: ${stats.get('current_balance', 0):.2f}")
        print(f"📈 Daily PnL: ${stats.get('daily_pnl', 0):.2f}")
        print(f"📊 Daily Trades: {stats.get('daily_trades', 0)}")
        print(f"📋 Total Trades: {stats.get('total_trades', 0)}")
        print(f"🎯 Win Rate: {stats.get('win_rate', '0%')}")
        print(f"🔢 Consecutive Losses: {stats.get('consecutive_losses', 0)}")
        
        print("\n" + "─"*40)
        print("📋 Risk Parameters:")
        print(f"  Max Daily Loss: 5%")
        print(f"  Max Position: 10%")
        print(f"  Max Consecutive Losses: 3")
        
        allowed, reason = can_trade()
        if allowed:
            print(f"\n✅ Trading Allowed")
        else:
            print(f"\n❌ Trading Blocked: {reason}")
    
    def show_help(self):
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              COMMANDS                                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  1-7         : Switch tabs                                                     ║
║  m           : Markets tab                                                    ║
║  s           : Signals tab                                                    ║
║  t           : Trading tab                                                    ║
║  p           : Positions tab                                                  ║
║  h           : History tab                                                    ║
║  w           : Wallet tab                                                     ║
║  r           : Risk tab                                                      ║
║  q/quit/exit : Exit program                                                  ║
║  help        : Show this help                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
    
    def run(self):
        self.init_wallet()
        
        commands = {
            "1": "markets",
            "2": "signals", 
            "3": "trading",
            "4": "positions",
            "5": "history",
            "6": "wallet",
            "7": "risk",
            "m": "markets",
            "s": "signals",
            "t": "trading",
            "p": "positions",
            "h": "history",
            "w": "wallet",
            "r": "risk"
        }
        
        while True:
            self.clear_screen()
            self.print_header("⚡ POLYMARKET TRADING BOT")
            self.print_tabs()
            self.print_status_bar()
            
            if self.current_tab == "markets":
                self.tab_markets()
            elif self.current_tab == "signals":
                self.tab_signals()
            elif self.current_tab == "trading":
                self.tab_trading()
            elif self.current_tab == "positions":
                self.tab_positions()
            elif self.current_tab == "history":
                self.tab_history()
            elif self.current_tab == "wallet":
                self.tab_wallet()
            elif self.current_tab == "risk":
                self.tab_risk()
            
            print("\n" + "─"*80)
            try:
                cmd = input("Command (1-7, m/s/t/p/h/w/r, help, q): ").strip().lower()
            except EOFError:
                break
            
            if cmd in commands:
                self.current_tab = commands[cmd]
            elif cmd in ["q", "quit", "exit"]:
                print("\n👋 Terima kasih!")
                break
            elif cmd == "help":
                self.show_help()
                input("\nPress Enter to continue...")
            else:
                print("❌ Command tidak valid. Ketik 'help' untuk melihat semua commands.")

if __name__ == "__main__":
    bot = InteractiveBot()
    bot.run()
