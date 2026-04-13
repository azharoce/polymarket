import os
import sys
import time
import requests
import signal
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.auth import load_wallet
from bot.market import fetch_markets, get_current_price
from bot.risk import initialize_risk, can_trade, get_risk_stats, record_trade
from bot.trading import execute_trade
from bot.config import API_HEADERS, Config

LOG_FILE = Path("bot_trading.log")
SIMULATION_LOG = Path("bot_simulation.log")
REAL_TRADE_LOG = Path("bot_real_trades.log")

SIMULATION_FOLDER = Path("simulation")

def ensure_simulation_folder():
    """Create simulation folder with timestamp"""
    if not SIMULATION_FOLDER.exists():
        SIMULATION_FOLDER.mkdir()
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sim_folder = SIMULATION_FOLDER / timestamp
    sim_folder.mkdir(exist_ok=True)
    return sim_folder

sim_folder = None
initial_balance = 1000.0
sim_trades = []
sim_balance = initial_balance
sim_start_time = None

def shutdown_handler(signum, frame):
    """Handle shutdown for background mode"""
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run and sim_folder:
        update_simulation_summary()
    print("\n\n👋 Bot stopped (signal)!")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)

def init_simulation():
    """Initialize simulation session"""
    global sim_folder, sim_balance, sim_start_time, sim_trades, initial_balance
    
    sim_folder = ensure_simulation_folder()
    sim_start_time = datetime.now()
    sim_balance = initial_balance
    sim_trades = []
    
    write_sim_log("config.txt", "="*50)
    write_sim_log("config.txt", "SIMULATION SESSION STARTED")
    write_sim_log("config.txt", f"Start Time: {sim_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    write_sim_log("config.txt", f"Initial Balance: ${initial_balance:.2f}")
    write_sim_log("config.txt", f"Max Position: {Config.MAX_POSITION_SIZE * 100:.1f}%")
    write_sim_log("config.txt", f"Max Daily Loss: {Config.MAX_DAILY_LOSS * 100:.1f}%")
    write_sim_log("config.txt", f"Stop Loss: {Config.STOP_LOSS_PERCENTAGE * 100:.1f}%")
    write_sim_log("config.txt", "="*50)
    write_sim_log("config.txt", "")
    
    write_sim_log("trades.txt", "="*70)
    write_sim_log("trades.txt", f"SIMULATION TRADES - Started {sim_start_time.strftime('%Y-%m-%d %H:%M')}")
    write_sim_log("trades.txt", f"Initial Balance: ${initial_balance:.2f}")
    write_sim_log("trades.txt", "="*70)
    write_sim_log("trades.txt", f"{'Time':<20} | {'Market':<25} | {'Side':<4} | {'Size':<8} | {'Price':<8} | {'P/L':<10}")
    write_sim_log("trades.txt", "-"*70)

def write_sim_log(filename, message):
    """Write to simulation log file"""
    if sim_folder:
        with open(sim_folder / filename, "a") as f:
            f.write(message + "\n")

def log_simulation_trade(trade_info):
    """Log a simulation trade"""
    global sim_balance, sim_trades
    
    if not sim_folder:
        return
    
    trade_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    market_name = trade_info.get("market", "N/A")[:25]
    side = trade_info.get("side", "")
    size = trade_info.get("size", 0)
    price = trade_info.get("price", 0)
    pnl = trade_info.get("pnl", 0)
    
    sim_balance += pnl
    sim_trades.append({
        "time": trade_time,
        "market": trade_info.get("market", ""),
        "side": side,
        "size": size,
        "price": price,
        "pnl": pnl,
        "balance_after": sim_balance
    })
    
    pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
    line = f"{trade_time:<20} | {market_name:<25} | {side:<4} | ${size:<7.2f} | ${price:.4f} | {pnl_str:>10}"
    write_sim_log("trades.txt", line)

def update_simulation_summary():
    """Update simulation summary"""
    if not sim_folder or not sim_start_time:
        return
    
    duration = datetime.now() - sim_start_time
    wins = sum(1 for t in sim_trades if t["pnl"] > 0)
    losses = sum(1 for t in sim_trades if t["pnl"] < 0)
    total_return = ((sim_balance - initial_balance) / initial_balance) * 100
    
    write_sim_log("summary.txt", "="*50)
    write_sim_log("summary.txt", "SIMULATION SUMMARY")
    write_sim_log("summary.txt", f"Start Time: {sim_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    write_sim_log("summary.txt", f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    write_sim_log("summary.txt", f"Duration: {duration}")
    write_sim_log("summary.txt", "-"*50)
    write_sim_log("summary.txt", f"Initial Balance: ${initial_balance:.2f}")
    write_sim_log("summary.txt", f"Final Balance: ${sim_balance:.2f}")
    write_sim_log("summary.txt", f"Total Return: {total_return:.2f}%")
    write_sim_log("summary.txt", "-"*50)
    write_sim_log("summary.txt", f"Total Trades: {len(sim_trades)}")
    write_sim_log("summary.txt", f"Wins: {wins} | Losses: {losses}")
    if len(sim_trades) > 0:
        win_rate = (wins / len(sim_trades)) * 100
        write_sim_log("summary.txt", f"Win Rate: {win_rate:.1f}%")
    write_sim_log("summary.txt", "="*50)

def log_to_file(message, mode="general"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")
    
    if mode == "simulation":
        with open(SIMULATION_LOG, "a") as f:
            f.write(msg + "\n")
        if sim_folder:
            write_sim_log("daily.log", msg)
    elif mode == "real":
        with open(REAL_TRADE_LOG, "a") as f:
            f.write(msg + "\n")
    
    print(message)

def log(message, mode="general"):
    log_to_file(message, mode)

POLYMARKET_BASE = "https://polymarket.com"

def get_link(m):
    slug = m.get('slug', '')
    if slug:
        return f"{POLYMARKET_BASE}/event/{slug}"
    return m.get('conditionId', '')

def get_positions(wallet_address):
    """Fetch open positions from Polymarket API"""
    try:
        url = f"{Config.GAMMA_API_URL}/positions?address={wallet_address}"
        response = requests.get(url, headers=API_HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"   ⚠️ Error fetching positions: {e}")
    return []

def show_positions(wallet_address):
    print(f"\n{'='*85}")
    print("💼 YOUR OPEN POSITIONS".center(85))
    print(f"{'='*85}")
    
    positions = get_positions(wallet_address)
    
    if not positions:
        print("   📭 No open positions")
        print("   💡 Bot akan otomatis open posisi quando ada sinyal")
    else:
        total_value = 0
        print(f"\n   {'Market':<40} {'Side':<6} {'Qty':<10} {'Entry':<8} {'Value'}")
        print("   " + "-"*85)
        
        for p in positions[:10]:
            market = p.get('marketQuestion', 'N/A')[:38]
            side = p.get('side', 'N/A')
            qty = float(p.get('size', 0))
            entry = float(p.get('avgPrice', 0))
            value = qty * entry
            
            print(f"   {market:<40} {side:<6} {qty:<10.2f} {entry:<8.2f} ${value:.2f}")
            total_value += value
        
        print("   " + "-"*85)
        print(f"   💰 Total Position Value: ${total_value:.2f}")
        print(f"   🌐 View all: {POLYMARKET_BASE}/portfolio")
    
    print(f"{'='*85}")

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

def detect_category(question):
    question = question.lower()
    for cat_name, keywords in KEYWORDS.items():
        if any(kw.lower() in question for kw in keywords):
            return cat_name
    return "Other"

def get_category_filter():
    category = os.getenv("CATEGORY", "").strip().lower()
    if category and category != "all" and category != "none":
        return category
    return None

def scan(dry_run=True, min_edge=30, category_filter=None):
    markets = fetch_markets(limit=50)
    
    opportunities = []
    
    for m in markets:
        prices = get_current_price(m)
        if not prices:
            continue
        
        mid = prices['mid_price']
        vol = float(m.get('volume', 0))
        
        if vol < 10000:
            continue
        
        question = m.get('question', '')
        category = detect_category(question)
        
        if category_filter and category.lower() != category_filter.lower():
            continue
        
        if mid < 0.10:
            sig = "BUY"
            edge = (0.90 - mid) * 100
        elif mid > 0.90:
            sig = "SELL"
            edge = (mid - 0.10) * 100
        else:
            continue
        
        if edge < min_edge:
            continue
        
        opportunities.append({
            'market': m,
            'category': category,
            'mid': mid,
            'sig': sig,
            'edge': edge,
            'volume': vol,
            'link': get_link(m)
        })
    
    opportunities.sort(key=lambda x: x['edge'], reverse=True)
    top_10 = opportunities[:10]
    
    print(f"\n{'#':<2} {'Category':<10} {'Market':<28} {'Mid':<5} {'Signal':<6} {'Edge':<7} {'Volume':<10} {'Status'}")
    print("-"*95)
    
    count = 0
    for opp in top_10:
        m = opp['market']
        count += 1
        
        status = "📋 SIGNAL"
        trade_executed = False
        
        if not dry_run:
            try:
                msg = f"🔄 Executing {opp['sig']} on {m.get('question','')[:30]}..."
                print(f"   {msg}")
                log_to_file(msg, "real")
                result = execute_trade(m['id'], opp['sig'], opp['mid'], 10)
                if result and result.get('success'):
                    record_trade(10 * opp['mid'])
                    status = "✅ DONE"
                    trade_executed = True
                    log_to_file(f"✅ REAL TRADE: {opp['sig']} ${10} at {opp['mid']:.4f} on {m.get('question','')[:40]}", "real")
                else:
                    status = f"❌ {result.get('error', 'failed')[:20]}" if result else "❌ ERROR"
                    log_to_file(f"❌ REAL FAILED: {opp['sig']} - {result}", "real")
            except Exception as e:
                status = f"❌ {str(e)[:15]}"
                log_to_file(f"❌ REAL ERROR: {e}", "real")
        else:
            sim_msg = f"🟡 [SIMULATION] Would {opp['sig']} ${10} at price {opp['mid']:.4f} on {m.get('question','')[:40]}"
            print(f"   {sim_msg}")
            log_to_file(sim_msg, "simulation")
            status = "🟡 SIMULATION"
            trade_executed = True
            
            if dry_run:
                pnl = 0
                if opp['sig'] == 'BUY':
                    pnl = 10 * (1 - opp['mid'])
                else:
                    pnl = 10 * opp['mid']
                
                log_simulation_trade({
                    "market": m.get('question', 'N/A'),
                    "side": opp['sig'],
                    "size": 10,
                    "price": opp['mid'],
                    "pnl": pnl
                })
        
        cat_emoji = {"Sports": "🏒", "Politics": "🗳️", "Crypto": "₿", "Economy": "📈", "Tech": "💻", "Culture": "🎬", "Weather": "🌤️", "Esports": "🎮", "Other": "📌"}
        cat_display = f"{cat_emoji.get(opp['category'], '📌')} {opp['category']}"
        
        line = f"  {count:<2} {cat_display:<10} {m.get('question','')[:28]:<28} {opp['mid']:.2f}   {opp['sig']:<6} {opp['edge']:>5.1f}%  ${opp['volume']:>9,.0f}  {status}"
        print(line)
        log_to_file(line, "general")
    
    return count

def main():
    global initial_balance
    
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    interval = int(os.getenv("SCAN_INTERVAL", "60"))
    category_filter = get_category_filter()
    
    mode = "🔴 REAL TRADING" if not dry_run else "🟢 DRY RUN"
    
    if dry_run:
        init_simulation()
    
    log_to_file("="*60, "general")
    log_to_file(f"🤖 Bot Started - Mode: {mode}", "general")
    if category_filter:
        log_to_file(f"📂 Category Filter: {category_filter}", "general")
    log_to_file("="*60, "general")
    
    print("\n" + "="*95)
    print("⚡ POLYMARKET AUTO SCANNER + TRADING".center(95))
    print("="*95)
    cat_info = f" | 📂 Filter: {category_filter}" if category_filter else ""
    print(f"\n🔄 Mode: {mode} | Refresh: {interval}s{cat_info} | 🛑 Ctrl+C to stop\n")
    
    print("-"*85)
    wallet = load_wallet()
    if wallet:
        print(f"  👤 Wallet: {wallet.address}")
        print(f"  🌐 Portfolio: {POLYMARKET_BASE}/portfolio")
        print(f"  💰 Deposit: Send USDC to {wallet.address}")
        log_to_file(f"Wallet: {wallet.address}", "general")
        log_to_file(f"Portfolio: {POLYMARKET_BASE}/portfolio", "general")
        show_positions(wallet.address)
    print("-"*85)
    
    initialize_risk(1000.0)
    stats = get_risk_stats()
    print(f"  💵 Balance: ${stats.get('current_balance',0):.2f}")
    print(f"  📈 Daily PnL: ${stats.get('daily_pnl',0):.2f}")
    allowed, reason = can_trade()
    print(f"  ✅ Trade: {'Allowed' if allowed else 'Blocked - ' + reason}")
    print("-"*85)
    
    if not dry_run:
        print("\n⚠️  🔴 REAL TRADING MODE - Bot will place real orders!")
        print("    Make sure you have USDC in your wallet.")
        confirm = input("    Continue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("\n👋 Cancelled!")
            return
    
    iter_num = 0
    while True:
        iter_num += 1
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*95}")
        print(f"🔍 SCAN #{iter_num} | {timestamp}")
        print(f"{'='*95}")
        
        if wallet:
            show_positions(wallet.address)
        
        count = scan(dry_run, category_filter=category_filter)
        
        print(f"\n📋 Signals: {count} | ⏰ Next: {interval}s | 🛑 Ctrl+C")
        
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
            if dry_run:
                update_simulation_summary()
            print("\n\n👋 Bot stopped!")
            break

if __name__ == "__main__":
    main()
