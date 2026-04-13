"""
Flask server with Bot Control + API + Integrated Bot Logic
"""

import threading
import time
import json
from datetime import datetime
import sys
import os

# Add parent directory to Python path so we can import bot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from flask import Flask, jsonify, send_from_directory, request

from api import get_balances, get_trade_history, get_markets, get_positions, place_order
from bot_controller import bot, save_trade_log
import simulation_api as sim_api
from simulation_api import SIMULATION_PATH

app = Flask(__name__)

# Auto bot state
_autobot_running = False
_autobot_thread = None


@app.route('/api/balances')
def api_balances():
    balances = get_balances()
    
    sim_status = sim_api.get_simulation_status()
    
    balances["simulation"] = {
        "running": sim_status.get("running", False),
        "balance": sim_status.get("balance", 0),
        "stats": sim_status.get("stats", {})
    }
    
    bot_status = bot.get_status()
    balances["bot"] = {
        "balance": bot_status["current_balance"],
        "mode": bot_status["mode"],
        "running": bot_status["running"]
    }
    
    return jsonify(balances)


@app.route('/api/trades')
def api_trades():
    return jsonify(get_trade_history())


@app.route('/api/trades/sync', methods=['POST'])
def trades_sync():
    """Sync trades from Polymarket API"""
    from api import sync_trades_from_polymarket
    count = sync_trades_from_polymarket()
    logger.info(f"Synced {count} trades from Polymarket")
    return jsonify({"count": count})


@app.route('/api/place-order', methods=['POST'])
def api_place_order():
    """Place an order on Polymarket"""
    data = request.json or {}
    result = place_order(
        condition_id=data.get('condition_id'),
        side=data.get('side', 'YES'),
        amount=float(data.get('amount', 1)),
        yes_price=float(data.get('yes_price', 0.5))
    )
    return jsonify(result)


@app.route('/api/markets')
def api_markets():
    return jsonify(get_markets())


@app.route('/api/positions')
def api_positions():
    return jsonify(get_positions())


@app.route('/api/simulation/status')
def simulation_status():
    return jsonify(sim_api.get_simulation_status())


@app.route('/api/simulation/start', methods=['POST'])
def simulation_start():
    data = request.json or {}
    
    config = {
        'initial_balance': float(data.get('balance', 100)),
        'bet_size': float(data.get('bet_size', 2)),
        'bet_size_pct': float(data.get('bet_pct', 0.02)),
        'min_prob': float(data.get('min_prob', 0.70)),
        'max_open_bets': int(data.get('max_open', 10)),
        'max_open_pct': float(data.get('max_pct', 0.30)),
        'minutes': int(data.get('minutes', 1)),
        'max_bets': int(data.get('max_bets', 10)),
        'category': data.get('category', None)
    }
    
    markets = get_markets(limit=200)
    
    from bot.trading_utils import filter_markets, get_high_probability_markets
    
    eligible = filter_markets(markets, category=config.get('category'), min_volume=1000)
    high_prob = get_high_probability_markets(eligible, min_prob=config['min_prob'])
    
    sim_api.init_simulation(high_prob)
    
    result = sim_api.start_simulation(config)
    
    return jsonify(result)


@app.route('/api/simulation/stop', methods=['POST'])
def simulation_stop():
    return jsonify(sim_api.stop_simulation())


@app.route('/api/simulation/reset', methods=['POST'])
def simulation_reset():
    return jsonify(sim_api.reset_simulation())


@app.route('/api/simulation/trades')
def simulation_trades():
    status = sim_api.get_simulation_status()
    
    in_memory_trades = status.get("trades", [])
    log_trades = sim_api.get_simulation_history()
    
    all_trades = in_memory_trades + log_trades
    
    return jsonify({
        "trades": all_trades[-50:],
        "open_bets": status.get("open_bets", []),
        "count": len(all_trades)
    })


@app.route('/api/simulation/history')
def simulation_history():
    # Get query parameters for pagination, search, and filtering
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
        
    try:
        per_page = int(request.args.get('per_page', 50))
    except (ValueError, TypeError):
        per_page = 50
    search = request.args.get('search', '').lower()
    filter_result = request.args.get('filter', '').lower()  # 'win' or 'lose'
    sort_by = request.args.get('sort_by', 'timestamp')
    sort_order = request.args.get('sort_order', 'desc')  # 'asc' or 'desc'
    
    # Get all trades
    all_trades = sim_api.get_simulation_history()
    
    # Apply search filter
    if search:
        all_trades = [
            t for t in all_trades 
            if search in t.get('question', '').lower() 
            or search in t.get('action', '').lower()
            or search in t.get('category', '').lower()
        ]
    
    # Apply win/lose filter
    if filter_result == 'win':
        all_trades = [t for t in all_trades if t.get('won', False)]
    elif filter_result == 'lose':
        all_trades = [t for t in all_trades if not t.get('won', False)]
    
    # Apply sorting
    reverse = (sort_order == 'desc')
    try:
        all_trades.sort(
            key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by, 0), (int, float)) 
                       else x.get(sort_by, '') or '',
            reverse=reverse
        )
    except Exception as e:
        # Fallback to timestamp sorting if there's an error
        all_trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Apply pagination
    total = len(all_trades)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_trades = all_trades[start_idx:end_idx]
    
    return jsonify({
        "trades": paginated_trades,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        },
        "count": len(paginated_trades),
        "total_count": total
    })


@app.route('/api/simulation/chart')
def simulation_chart():
    """Get balance history for chart visualization"""
    balance_file = SIMULATION_PATH / "balance_history.json"
    data = []
    if balance_file.exists():
        try:
            with open(balance_file, 'r') as f:
                data = json.load(f)
        except:
            pass
    return jsonify(data)


@app.route('/api/bot/status')
def bot_status():
    return jsonify(bot.get_status())


@app.route('/api/bot/start', methods=['POST'])
def bot_start():
    data = request.json or {}
    mode = data.get('mode', 'simulation')
    initial_balance = float(data.get('initial_balance', 100))
    min_prob = float(data.get('min_prob', 0.70))
    max_losses = int(data.get('max_losses', 5))
    bet_pct = float(data.get('bet_pct', 0.1))
    min_volume = int(data.get('min_volume', 1000))
    interval = int(data.get('interval', 60))
    
    result = bot.start(
        mode=mode, 
        initial_balance=initial_balance,
        min_prob=min_prob,
        max_losses=max_losses,
        bet_pct=bet_pct,
        min_volume=min_volume,
        interval=interval
    )
    return jsonify(result)


@app.route('/api/bot/stop', methods=['POST'])
def bot_stop():
    result = bot.stop()
    return jsonify(result)


@app.route('/api/autobot/start', methods=['POST'])
def autobot_start():
    """Start auto betting bot for real trading"""
    global _autobot_thread, _autobot_running
    
    if _autobot_running:
        return jsonify({"error": "Auto bot already running"})
    
    data = request.json or {}
    
    config = {
        'bet_size': float(data.get('bet_size', 2)),
        'min_prob': float(data.get('min_prob', 0.70)),
        'max_open': int(data.get('max_open', 10)),
        'max_pct': float(data.get('max_pct', 0.30)),
        'minutes': int(data.get('minutes', 1)),
        'category': data.get('category')
    }
    
    _autobot_running = True
    _autobot_thread = threading.Thread(target=_run_autobot, args=(config,))
    _autobot_thread.daemon = True
    _autobot_thread.start()
    
    logger.info(f"Started auto bot: {config}")
    return jsonify({"status": "started", "config": config})


def _run_autobot(config):
    """Run auto bot in background"""
    global _autobot_running
    
    try:
        from api import get_balances, get_markets, get_positions
        from api import place_order
    except Exception as e:
        logger.error(f"Import error: {e}")
        return
    
    minutes = config.get('minutes', 1) if isinstance(config.get('minutes'), int) else 1
    bet_size = config.get('bet_size', 2)
    min_prob = config.get('min_prob', 0.70)
    max_open = config.get('max_open', 10)
    category = config.get('category')
    
    while _autobot_running:
        try:
            balances = get_balances()
            wallet_usdc = balances.get('wallet', {}).get('usdc', 0)
            polymarket_usdc = balances.get('polymarket', {}).get('usdc', 0)
            
            if wallet_usdc < bet_size and polymarket_usdc < bet_size:
                logger.warning(f"Insufficient balance: wallet=${wallet_usdc}, polymarket=${polymarket_usdc}")
                time.sleep(minutes * 60)
                continue
            
            positions = get_positions()
            open_count = len(positions.get('positions', []))
            
            if open_count >= max_open:
                logger.info(f"Max open positions: {open_count}/{max_open}")
                time.sleep(minutes * 60)
                continue
            
            markets = get_markets(50)
            if not markets:
                time.sleep(minutes * 60)
                continue
            
            # Find best market - closest to 50% (best value)
            candidates = []
            for m in markets:
                prices = m.get('outcomePrices', [])
                if prices:
                    try:
                        prices = json.loads(prices) if isinstance(prices, str) else prices
                    except:
                        prices = [0.5, 0.5]
                    
                    yes_prob = float(prices[0]) if len(prices) > 0 else 0
                    no_prob = float(prices[1]) if len(prices) > 1 else 0
                    
                    # Skip extreme probabilities (<10% or >90%)
                    if yes_prob < 0.10 or yes_prob > 0.90: continue
                    
                    # Pick side closest to 50%
                    yes_diff = abs(0.50 - yes_prob)
                    no_diff = abs(0.50 - no_prob)
                    
                    if yes_diff <= no_diff:
                        side = 'YES'
                        prob = yes_prob
                    else:
                        side = 'NO'
                        prob = no_prob
                    
                    # Filter by category
                    m_group = m.get('groupItemTitle', '')
                    if category and category != 'all' and m_group != category:
                        continue
                    
                    candidates.append((m, side, prob, abs(0.50 - prob)))
            
            if not candidates:
                time.sleep(minutes * 60)
                continue
            
            # Sort by closest to 50%
            candidates.sort(key=lambda x: x[3])
            market, side, prob = candidates[0][0], candidates[0][1], candidates[0][2]
            
            try:
                result = place_order(
                    condition_id=market.get('conditionId'),
                    side=side,
                    amount=bet_size,
                    yes_price=prob
                )
                
                if result.get('success'):
                    logger.info(f"Placed order: {market.get('question', '')[:30]} @ {side} {prob*100:.0f}%")
                else:
                    logger.error(f"Order failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Order error: {e}")
                
        except Exception as e:
            logger.error(f"Auto bot error: {e}")
        
        time.sleep(minutes * 60)


@app.route('/api/autobot/stop', methods=['POST'])
def autobot_stop():
    """Stop auto betting bot"""
    global _autobot_running
    
    _autobot_running = False
    logger.info("Auto bot stopped")
    return jsonify({"status": "stopped"})


@app.route('/api/bot/trades')
def bot_trades():
    limit = int(request.args.get('limit', 50))
    mode_filter = request.args.get('mode', None)
    trades = bot.get_trades(limit)
    if mode_filter:
        trades = [t for t in trades if t.get('mode') == mode_filter]
    return jsonify({
        "trades": trades,
        "count": len(trades)
    })


@app.route('/api/bot/add_trade', methods=['POST'])
def bot_add_trade():
    data = request.json or {}
    trade = bot.add_trade(data)
    save_trade_log(trade)
    return jsonify(trade)


@app.route('/')
def index():
    return send_from_directory('html', 'index.html')


if __name__ == '__main__':
    print("Starting server at http://localhost:5001")
    print("Mode: Simulation (new) + Real Trading")
    app.run(host='0.0.0.0', port=5001, debug=True)