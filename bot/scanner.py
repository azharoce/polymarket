import os
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'

from dotenv import load_dotenv
load_dotenv()

from bot.market import fetch_markets, get_current_price
from bot.config import Config

CATEGORIES = {
    "Sports": ["NHL", "NBA", "NFL", "FIFA", "World Cup", "Stanley Cup", "Finals", "win the", "game", "match"],
    "Politics": ["President", "election", "Trump", "Biden", "Congress", "Senate", "Governor", "political"],
    "Crypto": ["Bitcoin", "Ethereum", "BTC", "ETH", "Solana", "crypto", "token"],
    "Economy": ["GDP", "inflation", "recession", "Fed", "interest rate", "economy", "market"],
    "Tech": ["AI", "Apple", "Google", "Microsoft", "Tesla", "tech", "launch"],
    "Culture": ["album", "movie", "Rihanna", "Carti", "GTA", "music", "release"],
    "Weather": ["hurricane", "earthquake", "storm", "weather", "rain", "temperature"],
    "Esports": ["Dota", "League", "CSGO", "esports", "gaming", "tournament"]
}

def get_category(question, group=''):
    q = question.lower()
    g = group.lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw.lower() in q or kw.lower() in g for kw in keywords):
            return cat
    return "Other"

def scan_markets(min_prob=0.70, min_volume=1000):
    """Scan all markets and categorize them"""
    
    print("\n" + "="*80)
    print("🔍 POLYMARKET LIVE SCANNER".center(80))
    print("="*80)
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Min Prob: {min_prob*100}% | Min Volume: ${min_volume:,}")
    
    print(f"\n📥 Fetching markets...")
    all_markets = fetch_markets(closed=False, limit=100)
    closed_markets = fetch_markets(closed=True, limit=50)
    
    print(f"   Active: {len(all_markets)} | Resolved: {len(closed_markets)}")
    
    high_prob = []
    upcoming = []
    resolved = []
    
    for m in all_markets:
        prices = get_current_price(m)
        if not prices:
            continue
        
        vol = float(m.get('volume', 0))
        if vol < min_volume:
            continue
        
        prob = prices['mid_price']
        end_date = m.get('endDate', '')
        
        cat = get_category(m.get('question', ''), m.get('groupItemTitle', ''))
        
        is_high = prob >= min_prob or prob <= (1 - min_prob)
        
        market_info = {
            'id': m['id'],
            'question': m.get('question', '')[:50],
            'prob': prob,
            'volume': vol,
            'category': cat,
            'end_date': end_date,
            'url': f"https://polymarket.com/market/{m.get('slug', m['id'])}"
        }
        
        if is_high:
            action = 'YES' if prob >= min_prob else 'NO'
            market_info['action'] = action
            market_info['odds'] = round(1/prob if prob >= min_prob else 1/(1-prob), 2)
            high_prob.append(market_info)
        else:
            upcoming.append(market_info)
    
    for m in closed_markets:
        vol = float(m.get('volume', 0))
        if vol < min_volume:
            continue
        
        outcome_prices_str = m.get('outcomePrices', '[]')
        try:
            outcome_prices = json.loads(outcome_prices_str)
        except:
            continue
        
        if len(outcome_prices) < 2:
            continue
        
        yes_price = float(outcome_prices[0])
        no_price = float(outcome_prices[1])
        
        if yes_price == 0 and no_price == 0:
            continue
        
        cat = get_category(m.get('question', ''), m.get('groupItemTitle', ''))
        
        outcome = 'YES' if yes_price > no_price else 'NO'
        final_price = yes_price if outcome == 'YES' else no_price
        
        resolved.append({
            'question': m.get('question', '')[:50],
            'outcome': outcome,
            'final_prob': f"{final_price*100:.0f}%",
            'volume': vol,
            'category': cat,
            'url': f"https://polymarket.com/market/{m.get('slug', m['id'])}"
        })
    
    return high_prob, upcoming, resolved

def print_signals(high_prob, upcoming, resolved):
    print(f"\n{'='*80}")
    print("🎯 HIGH PROBABILITY - READY TO TRADE".center(80))
    print(f"{'='*80}")
    
    if not high_prob:
        print("   ❌ No high probability markets found")
    else:
        by_category = {}
        for m in high_prob:
            cat = m['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(m)
        
        print(f"\n   Total: {len(high_prob)} opportunities across {len(by_category)} categories")
        
        for cat, markets in sorted(by_category.items()):
            print(f"\n   📌 {cat.upper()} ({len(markets)} trades)")
            print(f"   {'#':<3} {'Question':<42} {'Prob':<8} {'Odds':<6}")
            print("   " + "-"*65)
            for i, m in enumerate(markets[:10], 1):
                print(f"   {i:<3} {m['question'][:42]:<42} {m['prob']*100:>5.1f}%   {m['odds']:.2f}x")
            
            print(f"\n   🔗 URLs:")
            for m in markets[:3]:
                print(f"   {m['action']} {m['odds']}x: {m['url']}")
    
    print(f"\n{'='*80}")
    print("📅 UPCOMING EVENTS (50-50, Hot Markets)".center(80))
    print(f"{'='*80}")
    
    if not upcoming:
        print("   ❌ No upcoming markets")
    else:
        by_cat_upcoming = {}
        for m in upcoming:
            cat = m['category']
            if cat not in by_cat_upcoming:
                by_cat_upcoming[cat] = []
            by_cat_upcoming[cat].append(m)
        
        print(f"\n   {len(upcoming)} markets in play:")
        
        for cat, markets in sorted(by_cat_upcoming.items()):
            print(f"\n   📌 {cat.upper()}")
            for m in markets:
                print(f"   • {m['question'][:50]} | {m['prob']*100:.1f}% | ${m['volume']:,.0f}")
    
    print(f"\n{'='*80}")
    print("✅ RESOLVED MARKETS (This Week)".center(80))
    print(f"{'='*80}")
    
    if not resolved:
        print("   ❌ No resolved markets")
    else:
        by_cat_resolved = {}
        for m in resolved:
            cat = m['category']
            if cat not in by_cat_resolved:
                by_cat_resolved[cat] = []
            by_cat_resolved[cat].append(m)
        
        print(f"\n   {len(resolved)} markets resolved:")
        
        for cat, markets in sorted(by_cat_resolved.items()):
            print(f"\n   📌 {cat.upper()} ({len(markets)} resolved)")
            print(f"   {'Question':<45} {'Outcome':<8} {'Final':<6}")
            print("   " + "-"*65)
            for m in markets[:10]:
                print(f"   {m['question'][:45]:<45} {m['outcome']:<8} {m['final_prob']:<6}")

def save_daily_signal(high_prob, upcoming, resolved):
    now = datetime.now()
    folder = Path("signals")
    folder.mkdir(exist_ok=True)
    
    filename = f"signal_{now.strftime('%Y-%m-%d')}.txt"
    
    with open(folder / filename, 'w') as f:
        f.write(f"POLYMARKET DAILY SIGNAL - {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        
        f.write("🎯 HIGH PROBABILITY - READY TO TRADE\n")
        f.write("-"*70 + "\n")
        
        by_category = {}
        for m in high_prob:
            cat = m['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(m)
        
        for cat, markets in sorted(by_category.items()):
            f.write(f"\n📌 {cat.upper()} ({len(markets)} trades)\n")
            for m in markets:
                f.write(f"  [{m['action']}] {m['odds']}x - {m['question']}\n")
                f.write(f"     URL: {m['url']}\n")
        
        f.write("\n\n📅 UPCOMING EVENTS (50-50)\n")
        f.write("-"*70 + "\n")
        
        by_cat_upcoming = {}
        for m in upcoming:
            cat = m['category']
            if cat not in by_cat_upcoming:
                by_cat_upcoming[cat] = []
            by_cat_upcoming[cat].append(m)
        
        for cat, markets in sorted(by_cat_upcoming.items()):
            f.write(f"\n📌 {cat.upper()}\n")
            for m in markets:
                f.write(f"  • {m['question']} | {m['prob']*100:.1f}%\n")
        
        f.write("\n\n✅ RESOLVED MARKETS\n")
        f.write("-"*70 + "\n")
        
        by_cat_resolved = {}
        for m in resolved:
            cat = m['category']
            if cat not in by_cat_resolved:
                by_cat_resolved[cat] = []
            by_cat_resolved[cat].append(m)
        
        for cat, markets in sorted(by_cat_resolved.items()):
            f.write(f"\n📌 {cat.upper()}\n")
            for m in markets:
                f.write(f"  [{m['outcome']}] {m['question']}\n")
    
    print(f"\n📁 Signal saved to: signals/{filename}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Polymarket Live Scanner')
    parser.add_argument('--min-prob', type=float, default=0.70)
    parser.add_argument('--min-vol', type=float, default=1000)
    parser.add_argument('--loop', action='store_true', help='Loop every 60 seconds')
    parser.add_argument('--save', action='store_true', help='Save daily signal')
    
    args = parser.parse_args()
    
    if args.loop:
        print("🔄 Running in loop mode (Ctrl+C to stop)...")
        while True:
            try:
                high_prob, upcoming, resolved = scan_markets(args.min_prob, args.min_vol)
                print_signals(high_prob, upcoming, resolved)
                if args.save:
                    save_daily_signal(high_prob, upcoming, resolved)
                print("\n⏳ Next scan in 60 seconds...")
                time.sleep(60)
            except KeyboardInterrupt:
                print("\n👋 Stopped")
                break
    else:
        high_prob, upcoming, resolved = scan_markets(args.min_prob, args.min_vol)
        print_signals(high_prob, upcoming, resolved)
        if args.save:
            save_daily_signal(high_prob, upcoming, resolved)

if __name__ == "__main__":
    main()