import os
import sys
import time
from bot.auth import load_wallet, get_account_info
from bot.market import fetch_markets, get_current_price, fetch_active_markets
from bot.risk import initialize_risk, can_trade, calculate_position_size, get_risk_stats
from bot.trading import execute_trade

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def show_wallet_info():
    print_header("WALLET INFO")
    wallet = load_wallet()
    if wallet:
        print(f"Address: {wallet.address}")
        print(f"Network: Polygon")
        print(f"\n⚠️  Saldo: $0.00 - Deposit USDC untuk trading")
    else:
        print("❌ Wallet tidak loaded")

def show_markets(limit=20):
    print_header(f"MARKETS (Top {limit})")
    markets = fetch_markets(limit=limit)
    
    if not markets:
        print("❌ Tidak ada market")
        return
    
    print(f"{'No':<4} {'Market':<45} {'Bid':<8} {'Ask':<8} {'Volume':<12}")
    print("-" * 85)
    
    for i, m in enumerate(markets, 1):
        prices = get_current_price(m)
        q = m.get("question", "N/A")[:43]
        
        if prices:
            bid = f"{prices['best_bid']:.2f}"
            ask = f"{prices['best_ask']:.2f}"
        else:
            bid = "N/A"
            ask = "N/A"
        
        vol = m.get("volume", "0")
        try:
            volume = f"${float(vol):,.0f}" if isinstance(vol, str) else f"${vol:,.0f}"
        except:
            volume = "$0"
        
        print(f"{i:<4} {q:<45} {bid:<8} {ask:<8} {volume:<12}")

def select_market():
    print_header("PILIH MARKET")
    markets = fetch_markets(limit=50)
    
    if not markets:
        print("❌ Tidak ada market")
        return None
    
    print(f"{'No':<4} {'Market':<50} {'Volume':<12}")
    print("-" * 70)
    
    for i, m in enumerate(markets, 1):
        q = m.get("question", "N/A")[:48]
        vol = m.get("volume", "0")
        try:
            volume = f"${float(vol):,.0f}" if isinstance(vol, str) else f"${vol:,.0f}"
        except:
            volume = "$0"
        
        print(f"{i:<4} {q:<50} {volume:<12}")
    
    print("\n" + "-"*70)
    try:
        choice = input("Pilih nomor market (0 untuk cancel): ").strip()
        idx = int(choice) - 1
        if idx < 0 or idx >= len(markets):
            return None
        return markets[idx]
    except:
        return None

def analyze_selected_market(market):
    print_header("ANALISA MARKET")
    q = market.get("question", "Unknown")
    print(f"Question: {q}")
    print(f"Market ID: {market.get('id')}")
    
    prices = get_current_price(market)
    if prices:
        print(f"\n💰 HARGA:")
        print(f"   Bid:  {prices['best_bid']:.4f}")
        print(f"   Ask:  {prices['best_ask']:.4f}")
        print(f"   Mid:  {prices['mid_price']:.4f}")
        print(f"   Spread: {prices['spread']:.4f}")
        
        mid = prices['mid_price']
        print(f"\n📊 SIGNAL:")
        if mid < 0.05:
            print(f"   SIGNAL: BUY (probability {mid:.2%} < 5%)")
        elif mid > 0.95:
            print(f"   SIGNAL: SELL (probability {mid:.2%} > 95%)")
        else:
            print(f"   SIGNAL: HOLD (probability {mid:.2%} antara 5%-95%)")
    else:
        print("❌ Gagal mengambil harga")
    
    vol = market.get("volume", "0")
    try:
        volume = float(vol) if isinstance(vol, str) else vol
    except:
        volume = 0
    print(f"\n📈 Volume: ${volume:,.0f}")

def place_order_interactive():
    market = select_market()
    if not market:
        print("❌ Canceled")
        return
    
    analyze_selected_market(market)
    
    print("\n" + "-"*70)
    try:
        confirm = input("Lanjut untuk trading? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Canceled")
            return
    except:
        print("❌ Canceled")
        return
    
    prices = get_current_price(market)
    if not prices:
        print("❌ Gagal mengambil harga")
        return
    
    print_header("EXECUTE TRADE")
    
    wallet = load_wallet()
    if not wallet:
        print("❌ Wallet tidak tersedia")
        return
    
    mid = prices['mid_price']
    side = "BUY" if mid < 0.05 else "SELL" if mid > 0.95 else None
    
    if not side:
        print("❌ Probability tidak memenuhi criteria untuk trading")
        return
    
    account_info = get_account_info(wallet)
    balance = float(account_info.get("usdcBalance", "1000")) / 1e6
    
    if balance < 1:
        print("❌ Saldo tidak mencukupi")
        return
    
    initialize_risk(balance)
    allowed, reason = can_trade()
    if not allowed:
        print(f"❌ Tidak bisa trading: {reason}")
        return
    
    position_size = calculate_position_size(balance, 0.8)
    print(f"\n📝 DETAIL ORDER:")
    print(f"   Market: {market.get('question', 'N/A')[:50]}")
    print(f"   Side: {side}")
    print(f"   Price: {mid:.4f}")
    print(f"   Size: ${position_size:.2f}")
    
    try:
        confirm = input("\nKonfirmasi execute? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Canceled")
            return
    except:
        print("❌ Canceled")
        return
    
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run:
        print(f"\n✅ [DRY RUN] Would {side} ${position_size:.2f} at {mid:.4f}")
    else:
        result = execute_trade(market['id'], side, mid, position_size)
        if result and result.get('success'):
            print(f"\n✅ Order placed successfully!")
        else:
            print(f"\n❌ Order failed: {result}")

def run_scan():
    print_header("SCANNING MARKETS")
    markets = fetch_active_markets(min_liquidity=10000)
    
    if not markets:
        print("❌ Tidak ada market aktif")
        return
    
    print(f"Ditemukan {len(markets)} market dengan liquidity > $10,000\n")
    
    signals = []
    for m in markets[:20]:
        prices = get_current_price(m)
        if not prices:
            continue
        
        mid = prices['mid_price']
        q = m.get("question", "N/A")[:40]
        
        if mid < 0.05:
            signal = "BUY"
            conf = 1.0 - mid
        elif mid > 0.95:
            signal = "SELL"
            conf = mid
        else:
            continue
        
        signals.append({
            "market": q,
            "mid": mid,
            "signal": signal,
            "confidence": conf
        })
    
    if not signals:
        print("Tidak ada sinyal trading found")
        return
    
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"{'Market':<42} {'Mid':<8} {'Signal':<8} {'Confidence'}")
    print("-" * 70)
    for s in signals:
        print(f"{s['market']:<42} {s['mid']:.4f}   {s['signal']:<8} {s['confidence']:.2%}")

def show_menu():
    print("\n" + "="*60)
    print("  ⚡ POLYMARKET TRADING BOT")
    print("="*60)
    print("""
  [1] 📊 Wallet Info
  [2] 📈 View Markets 
  [3] 🔍 Scan Trading Signals
  [4] 🎯 Pilih Market & Trade
  [5] 📋 Risk Stats
  [0] ❌ Keluar
  """)

def main():
    while True:
        show_menu()
        try:
            choice = input("Pilih menu: ").strip()
        except:
            print("❌ Invalid input")
            continue
        
        if choice == '0':
            print("\n👋 Terima kasih!")
            break
        elif choice == '1':
            show_wallet_info()
        elif choice == '2':
            show_markets()
        elif choice == '3':
            run_scan()
        elif choice == '4':
            place_order_interactive()
        elif choice == '5':
            print_header("RISK STATS")
            stats = get_risk_stats()
            for k, v in stats.items():
                print(f"  {k}: {v}")
        else:
            print("❌ Menu tidak valid")

if __name__ == "__main__":
    main()
