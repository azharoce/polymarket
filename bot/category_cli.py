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
from bot.category import CATEGORIES, fetch_markets_by_category, analyze_category_profit

def print_header(title, width=90):
    print(f"\n╔{'='*(width-2)}╗")
    print(f"║ {title:^{width-2}} ║")
    print(f"╚{'='*(width-2)}╝")

def print_subheader(title, width=90):
    print(f"\n{'─'*(width-1)}")
    print(f"  {title}")
    print(f"{'─'*(width-1)}")

def get_price(market):
    return get_current_price(market)

def analyze_market_opportunity(market):
    prices = get_price(market)
    if not prices:
        return None
    
    mid = prices['mid_price']
    volume = float(market.get('volume', '0'))
    q = market.get('question', 'N/A')[:40]
    
    signal = "HOLD"
    edge = 0
    
    if mid < 0.05:
        signal = "BUY 🟢"
        edge = (1.0 - mid - 0.02) * 100
    elif mid > 0.95:
        signal = "SELL 🔴"
        edge = (mid - 0.02) * 100
    elif mid < 0.10:
        signal = "BUY 💰"
        edge = (0.90 - mid - 0.02) * 100
    elif mid > 0.90:
        signal = "SELL 💰"
        edge = (mid - 0.10 - 0.02) * 100
    
    return {
        "question": q,
        "id": market.get("id"),
        "bid": prices['best_bid'],
        "ask": prices['best_ask'],
        "mid": mid,
        "spread": prices['spread'],
        "volume": volume,
        "signal": signal,
        "edge": edge,
        "roi": (1/mid - 1) * 100 if mid < 0.5 else (1/(1-mid) - 1) * 100 if mid > 0.5 else 0
    }

def show_trending():
    print_header("🔥 TRENDING MARKETS")
    
    markets = fetch_markets(limit=50)
    opportunities = []
    
    for m in markets:
        opp = analyze_market_opportunity(m)
        if opp and opp['signal'] != "HOLD" and opp['volume'] > 10000:
            opportunities.append(opp)
    
    if not opportunities:
        print("\n⚠️ No trending opportunities found")
        return
    
    opportunities.sort(key=lambda x: x['edge'], reverse=True)
    
    print(f"\n{'#':<3} {'Market':<42} {'Mid':<6} {'Volume':<12} {'Signal':<14} {'Edge':<8}")
    print("─"*90)
    
    for i, o in enumerate(opportunities[:15], 1):
        vol = f"${o['volume']:,.0f}"
        print(f"{i:<3} {o['question']:<42} {o['mid']:.2f}   {vol:<12} {o['signal']:<14} {o['edge']:.1f}%")

def show_category(cat_name, cat_id):
    print_header(f"🏷️ {cat_name.upper()}")
    
    markets = fetch_markets_by_category(cat_name, limit=50)
    
    if not markets:
        markets = fetch_markets(limit=50)
    
    opportunities = []
    
    for m in markets:
        opp = analyze_market_opportunity(m)
        if opp and opp['signal'] != "HOLD" and opp['volume'] > 5000:
            opportunities.append(opp)
    
    if not opportunities:
        print("\n⚠️ No opportunities in this category")
        return
    
    opportunities.sort(key=lambda x: x['edge'], reverse=True)
    
    print(f"\n{'#':<3} {'Market':<45} {'Bid':<6} {'Ask':<6} {'Volume':<12} {'Signal':<12}")
    print("─"*90)
    
    for i, o in enumerate(opportunities[:10], 1):
        vol = f"${o['volume']:,.0f}"
        print(f"{i:<3} {o['question']:<45} {o['bid']:.2f}  {o['ask']:.2f}   {vol:<12} {o['signal']:<12}")

def show_all_categories():
    print_header("📂 ALL CATEGORIES ANALYSIS")
    
    all_markets = fetch_markets(limit=100)
    
    prices_cache = {}
    print("📥 Loading prices...")
    for m in all_markets:
        prices_cache[m.get('id')] = get_price(m)
    
    print("\n" + "="*90)
    
    for cat_id, cat_name in CATEGORIES.items():
        opportunities = []
        
        for m in all_markets:
            if m.get('category', '').lower() != cat_name.lower():
                continue
                
            market_id = m.get('id')
            if market_id not in prices_cache:
                continue
                
            prices = prices_cache[market_id]
            if not prices:
                continue
            
            mid = prices['mid_price']
            volume = float(m.get('volume', '0'))
            q = m.get('question', 'N/A')[:35]
            
            if volume < 5000:
                continue
            
            signal = "HOLD"
            edge = 0
            
            if mid < 0.10:
                signal = "BUY"
                edge = (0.90 - mid) * 100
            elif mid > 0.90:
                signal = "SELL"
                edge = (mid - 0.10) * 100
            
            if signal != "HOLD":
                opportunities.append({
                    "market": q,
                    "mid": mid,
                    "volume": volume,
                    "signal": signal,
                    "edge": edge
                })
        
        if opportunities:
            opportunities.sort(key=lambda x: x['edge'], reverse=True)
            best = opportunities[0]
            print(f"  [{cat_id}] {cat_name:<14} | {best['signal']:<4} | {best['mid']:.2f} | Edge: {best['edge']:.1f}% | Vol: ${best['volume']:,.0f}")

def show_wallet():
    print_header("👛 WALLET INFO")
    
    wallet = load_wallet()
    if wallet:
        print(f"\n📍 Address: {wallet.address}")
        print(f"💰 USDC Balance: $0.00")
        print(f"⚠️  Deposit USDC to trade")
    else:
        print("\n❌ Wallet not connected")

def show_risk():
    print_header("⚠️ RISK MANAGEMENT")
    
    initialize_risk(1000.0)
    stats = get_risk_stats()
    
    print(f"\n  💵 Balance:       ${stats.get('current_balance', 0):.2f}")
    print(f"  📈 Daily PnL:      ${stats.get('daily_pnl', 0):.2f}")
    print(f"  📊 Total Trades:   {stats.get('total_trades', 0)}")
    print(f"  🎯 Win Rate:      {stats.get('win_rate', '0%')}")
    print(f"  🔢 Consec Losses: {stats.get('consecutive_losses', 0)}")
    
    allowed, reason = can_trade()
    status = "✅ ALLOWED" if allowed else f"❌ BLOCKED ({reason})"
    print(f"\n  📋 Trading Status: {status}")
    
    print(f"\n  📋 Parameters:")
    print(f"      Max Daily Loss:  5%")
    print(f"      Max Position:     10%")
    print(f"      Max Consec Losses: 3")

def show_commands():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              COMMANDS                                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  0          - Dashboard (all in one)                                           ║
║  1-16       - Select category                                                   ║
║  t          - Trending opportunities                                           ║
║  a          - All categories overview                                          ║
║  w          - Wallet info                                                      ║
║  r          - Risk management                                                 ║
║  q          - Quit                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

def main():
    print("\n" + "="*90)
    print("⚡ POLYMARKET TRADING BOT - CATEGORY SCANNER".center(90))
    print("="*90)
    
    show_wallet()
    show_risk()
    show_commands()
    
    while True:
        try:
            cmd = input("\nSelect: ").strip().lower()
        except:
            break
        
        if cmd == 'q':
            print("\n👋 Goodbye!")
            break
        elif cmd == '0':
            show_wallet()
            show_risk()
            show_trending()
            show_all_categories()
        elif cmd == 't':
            show_trending()
        elif cmd == 'a':
            show_all_categories()
        elif cmd == 'w':
            show_wallet()
        elif cmd == 'r':
            show_risk()
        elif cmd in CATEGORIES:
            show_category(CATEGORIES[cmd], cmd)
        else:
            print("❌ Invalid command")
            show_commands()

if __name__ == "__main__":
    main()
