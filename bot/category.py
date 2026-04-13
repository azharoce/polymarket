import os
import json
import requests
from bot.config import API_HEADERS, Config, logger

def fetch_markets_by_category(category=None, limit=100):
    url = f"{Config.GAMMA_API_URL}/markets"
    params = {
        "closed": "false",
        "archived": "false",
        "limit": limit
    }
    
    if category and category.lower() != "all":
        params["category"] = category
    
    try:
        response = requests.get(url, headers=API_HEADERS, params=params)
        response.raise_for_status()
        markets = response.json()
        return markets
    except requests.RequestException as e:
        logger.error(f"Failed to fetch markets: {e}")
        return []

def fetch_categories():
    url = f"{Config.GAMMA_API_URL}/categories"
    try:
        response = requests.get(url, headers=API_HEADERS)
        response.raise_for_status()
        return response.json()
    except:
        return []

CATEGORIES = {
    "1": "Trending",
    "2": "Breaking", 
    "3": "New",
    "4": "Politics",
    "5": "Sports",
    "6": "Crypto",
    "7": "Esports",
    "8": "Iran",
    "9": "Finance",
    "10": "Geopolitics",
    "11": "Tech",
    "12": "Culture",
    "13": "Economy",
    "14": "Weather",
    "15": "Mentions",
    "16": "Elections"
}

def analyze_category_profit(category_name, markets, prices_dict):
    signals = []
    
    for m in markets:
        market_id = m.get("id")
        if market_id not in prices_dict:
            continue
            
        prices = prices_dict[market_id]
        if not prices:
            continue
            
        mid = prices['mid_price']
        q = m.get("question", "N/A")[:45]
        volume = float(m.get("volume", "0"))
        
        if volume < 5000:
            continue
        
        potential_return = 0
        action = "HOLD"
        
        if mid < 0.10:
            action = "BUY"
            potential_return = (1.0 - mid) * 100
        elif mid > 0.90:
            action = "SELL"
            potential_return = mid * 100
        elif 0.10 <= mid <= 0.25:
            action = "BUY (value)"
            potential_return = (0.50 - mid) * 100
        elif 0.75 <= mid <= 0.90:
            action = "SELL (value)"  
            potential_return = (mid - 0.50) * 100
        
        if action != "HOLD":
            signals.append({
                "market": q,
                "id": market_id,
                "bid": prices['best_bid'],
                "ask": prices['best_ask'],
                "mid": mid,
                "volume": volume,
                "action": action,
                "potential_return": potential_return,
                "edge": potential_return - 5
            })
    
    signals.sort(key=lambda x: x['potential_return'], reverse=True)
    return signals

def get_all_categories_analysis():
    all_markets = fetch_markets_by_category(limit=200)
    
    prices_dict = {}
    for m in all_markets:
        from bot.market import get_current_price
        prices = get_current_price(m)
        prices_dict[m.get("id")] = prices
    
    category_signals = {}
    
    for cat_id, cat_name in CATEGORIES.items():
        cat_markets = [m for m in all_markets if m.get("category", "").lower() == cat_name.lower()]
        
        if not cat_markets:
            cat_markets = all_markets[:20]
        
        signals = analyze_category_profit(cat_name, cat_markets, prices_dict)
        
        if signals:
            category_signals[cat_name] = signals
    
    return category_signals

def print_category_analysis():
    print("\n" + "="*90)
    print("📊 CATEGORY ANALYSIS - FINDING PROFITABLE OPPORTUNITIES".center(90))
    print("="*90)
    
    all_markets = fetch_markets_by_category(limit=200)
    
    prices_dict = {}
    print("📥 Fetching prices...")
    for m in all_markets:
        from bot.market import get_current_price
        prices = get_current_price(m)
        prices_dict[m.get("id")] = prices
    
    print("\n" + "-"*90)
    
    total_opportunities = 0
    
    for cat_id, cat_name in CATEGORIES.items():
        signals = analyze_category_profit(cat_name, all_markets, prices_dict)
        
        if signals:
            print(f"\n🏷️  {cat_name.upper()}")
            print(f"   {'Market':<45} {'Mid':<6} {'Volume':<12} {'Action':<18} {'Edge'}")
            print("   " + "-"*85)
            
            for s in signals[:5]:
                vol_str = f"${s['volume']:,.0f}"
                print(f"   {s['market']:<45} {s['mid']:.2f}   {vol_str:<12} {s['action']:<18} {s['edge']:.1f}%")
            
            total_opportunities += len(signals)
    
    print("\n" + "-"*90)
    print(f"📈 Total Opportunities Found: {total_opportunities}")
    
    print("\n" + "="*90)
    print("💡 STRATEGY:".center(90))
    print("="*90)
    print("""
  • BUY when probability < 10% (underdog) - High return potential
  • SELL when probability > 90% (overwhelming favorite) - Lock in profit  
  • BUY VALUE when 10-25% (mispriced) - Edge trading
  • SELL VALUE when 75-90% - Profit taking
  
  🎯 Best opportunities: Low probability + High volume + Tight spread
    """)

def get_category_menu():
    print("\n" + "="*70)
    print("📂 SELECT CATEGORY".center(70))
    print("="*70)
    
    for cat_id, cat_name in CATEGORIES.items():
        print(f"  [{cat_id}] {cat_name}")
    
    print(f"  [a] All Categories")
    print(f"  [q] Quit")
    print("-"*70)

def run_category_scan():
    while True:
        get_category_menu()
        try:
            choice = input("Pilih category: ").strip().lower()
        except:
            break
        
        if choice == 'q':
            break
        
        if choice == 'a':
            choice = 'all'
        
        if choice.isdigit() and choice in CATEGORIES:
            category = CATEGORIES[choice]
        elif choice == 'all':
            category = None
        else:
            print("❌ Pilihan tidak valid")
            continue
        
        all_markets = fetch_markets_by_category(category, limit=100)
        
        if not all_markets:
            print("❌ Tidak ada market ditemukan")
            continue
        
        prices_dict = {}
        for m in all_markets:
            from bot.market import get_current_price
            prices_dict[m.get("id")] = get_current_price(m)
        
        signals = analyze_category_profit(category or "All", all_markets, prices_dict)
        
        print(f"\n📊 {category or 'All'} - {len(signals)} Opportunities")
        print("="*70)
        
        if not signals:
            print("⚠️ Tidak ada sinyal profitable ditemukan")
        else:
            print(f"\n{'Market':<45} {'Mid':<6} {'Volume':<12} {'Action':<18} {'Edge'}")
            print("-"*70)
            for s in signals[:15]:
                vol_str = f"${s['volume']:,.0f}"
                print(f"{s['market']:<45} {s['mid']:.2f}   {vol_str:<12} {s['action']:<18} {s['edge']:.1f}%")

if __name__ == "__main__":
    print_category_analysis()
