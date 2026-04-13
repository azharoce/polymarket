import os
import sys
import time
from datetime import datetime

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.auth import load_wallet
from bot.market import fetch_markets, get_current_price, fetch_active_markets
from bot.risk import initialize_risk, can_trade, get_risk_stats
from bot.backtest import get_wallet_balance

def print_header(title):
    print(f"\n╔{'='*78}╗")
    print(f"║ {title:^76} ║")
    print(f"╚{'='*78}╝")

def main():
    print("\n" + "="*80)
    print("⚡ POLYMARKET TRADING BOT - DASHBOARD".center(80))
    print("="*80)
    
    # Wallet Info
    print_header("👛 WALLET INFO")
    wallet = load_wallet()
    if wallet:
        print(f"📍 Address: {wallet.address}")
        print(f"💰 USDC Balance: $0.00 (need deposit)")
    else:
        print("❌ Wallet not connected")
    
    # Risk Stats
    print_header("⚠️ RISK MANAGEMENT")
    initialize_risk(1000.0)
    stats = get_risk_stats()
    print(f"💵 Balance: ${stats.get('current_balance', 0):.2f}")
    print(f"📈 Daily PnL: ${stats.get('daily_pnl', 0):.2f}")
    print(f"📊 Trades: {stats.get('total_trades', 0)} | Win Rate: {stats.get('win_rate', '0%')}")
    allowed, reason = can_trade()
    print(f"✅ Trading: {'Allowed' if allowed else 'Blocked - ' + reason}")
    
    # Active Signals
    print_header("🔍 TRADING SIGNALS")
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
        
        signals.append({"market": q, "mid": mid, "signal": signal, "confidence": conf})
    
    if signals:
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        print(f"\n{'Market':<45} {'Mid':<8} {'Signal':<15} {'Confidence'}")
        print("─"*80)
        for s in signals[:10]:
            print(f"{s['market']:<45} {s['mid']:.4f}   {s['signal']:<15} {s['confidence']:.2%}")
    else:
        print("\n⚠️ No trading signals found")
    
    # Markets
    print_header("📊 TOP MARKETS")
    all_markets = fetch_markets(limit=20)
    print(f"\n{'No':<4} {'Market':<55} {'Bid':<8} {'Ask':<8} {'Volume'}")
    print("─"*90)
    
    for i, m in enumerate(all_markets[:15], 1):
        prices = get_current_price(m)
        q = m.get("question", "N/A")[:53]
        
        if prices:
            bid = f"{prices['best_bid']:.2f}"
            ask = f"{prices['best_ask']:.2f}"
        else:
            bid = ask = "N/A"
        
        vol = m.get("volume", "0")
        try:
            volume = f"${float(vol):,.0f}"
        except:
            volume = "$0"
        
        print(f"{i:<4} {q:<55} {bid:<8} {ask:<8} {volume}")
    
    # Commands
    print_header("📋 COMMANDS")
    print("""
  python bot/cli.py        - Interactive mode (with tabs)
  python bot/main.py       - Auto scan mode
  python bot/backtest.py   - Backtest analysis
  python bot/cli.py        - Dashboard view
    """)
    
    print("\n" + "="*80)
    print("Done! Run 'python bot/cli.py' for interactive mode".center(80))
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
