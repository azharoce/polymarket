"""
Main dashboard application using Dash
Interactive visualization for Polymarket trading bot with real-time updates
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'
os.environ['DASH_SUPPRESS'] = '1'

import dash
from dash import dcc, html, callback, Output, Input, State
import pandas as pd
import plotly.graph_objects as go

from dashboard.data_extractor import TradeLogExtractor
from dashboard.visualizations import create_dashboard, create_history_table

# Initialize Dash app
app = dash.Dash(__name__, title="Polymarket Dashboard")

# Constants
INITIAL_BALANCE = 100.0

try:
    from bot.simulate_future import get_last_balance
    INITIAL_BALANCE = get_last_balance() or 100.0
except:
    pass
REFRESH_INTERVAL = 5
SIMULATION_PATH = "simulation"
TRADING_PATH = "trading"

# Global state for simulation
simulation_process = None
simulation_status = {"running": False, "started_at": None, "config": {}}
TRADING_MODE = "simulation"  # simulation or real

CLOB_API_URL = "https://clob.polymarket.com"
DATA_API_URL = "https://data-api.polymarket.com"

# Simulation config defaults
SIM_CONFIG = {
    "balance": 100.0,
    "bet_size": 2.0,
    "min_prob": 0.70,
    "max_open_bets": 10,
    "max_open_pct": 0.30,
    "minutes": 60,
    "category": "all"
}


def get_wallet_balance():
    """Get Polymarket wallet balance and positions"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from bot.auth import load_wallet
        wallet = load_wallet()
        
        if not wallet:
            return {"connected": False, "balance": 0.0, "address": None, "positions_value": 0, "positions_count": 0}
        
        # Get positions from trades
        from bot.portfolio import get_trades_from_api, get_positions_from_trades
        
        trades = get_trades_from_api(wallet.address, limit=200)
        positions = get_positions_from_trades(trades)
        
        # Calculate total position value
        positions_value = sum(p.get('cost', 0) for p in positions)
        
        return {
            "connected": True, 
            "balance": 0.0,  # Cash balance is 0
            "positions_value": positions_value,
            "positions_count": len(positions),
            "trades_count": len(trades),
            "address": wallet.address
        }
    except Exception as e:
        return {"connected": False, "balance": 0.0, "address": None}


def get_pnl_stats():
    """Get PnL stats from simulation"""
    try:
        from bot.simulate_future import get_last_balance
        from pathlib import Path
        
        balance = get_last_balance() or 100.0
        initial_balance = 100.0
        
        hourly_file = Path("simulation") / "hourly_stats.json"
        if hourly_file.exists():
            import json
            with open(hourly_file, 'r') as f:
                hourly_data = json.load(f)
            if hourly_data:
                initial_balance = hourly_data[0].get('initial_balance', 100.0)
        
        extractor = TradeLogExtractor(SIMULATION_PATH)
        df = extractor.extract_daily_summary()
        
        if df.empty:
            return balance, 0, 0, balance - 100
        
        released_pnl = df['profit'].sum()
        extractor_open = TradeLogExtractor(SIMULATION_PATH)
        open_bets = extractor_open.get_open_bets()
        
        floating_pnl = 0
        for bet in open_bets:
            if bet.get('action') == 'YES':
                floating_pnl += bet.get('amount', 0) * (1 - bet.get('entry_prob', 0.5))
            else:
                floating_pnl += bet.get('amount', 0) * bet.get('entry_prob', 0.5)
        
        running_pnl = released_pnl + floating_pnl
        
        return balance, released_pnl, floating_pnl, running_pnl
    except Exception as e:
        print(f"Error getting PnL: {e}")
        return 100.0, 0, 0, 0


def get_portfolio_history():
    """Get portfolio history from Data API"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from bot.auth import load_wallet
        wallet = load_wallet()
        
        if not wallet:
            return [], None
        
        import requests
        url = f"{DATA_API_URL}/trades"
        params = {"address": wallet.address, "limit": 200}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return data, wallet.address
        return [], None
    except Exception:
        return [], None


def get_positions():
    """Get open positions"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from bot.auth import load_wallet
        wallet = load_wallet()
        
        if not wallet:
            return []
        
        from bot.portfolio import get_trades_from_api, get_positions_from_trades
        trades = get_trades_from_api(wallet.address, limit=200)
        positions = get_positions_from_trades(trades)
        
        return positions
    except Exception:
        return []


def start_simulation(config=None):
    global simulation_process, simulation_status
    
    if config is None:
        config = SIM_CONFIG.copy()
    
    if simulation_status["running"]:
        return False, "Already running"
    
    try:
        from bot.simulate_future import get_last_balance
        last_balance = get_last_balance()
        initial_balance = last_balance if last_balance else config.get('balance', 100)
        
        cat = config.get('category', 'a')
        if cat == 'all':
            cat = 'a'
        
        cmd = [
            sys.executable, "-m", "bot.simulate_future", "--mode", "live",
            "--minutes", str(config.get('minutes', 60)),
            "--balance", str(initial_balance),
            "--bet", str(config.get('bet_size', 2)),
            "--prob", str(config.get('min_prob', 0.70)),
            "--max-open", str(config.get('max_open_bets', 10)),
            "--max-pct", str(config.get('max_open_pct', 0.30)),
            "--category", cat
        ]
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.getcwd()
        )
        simulation_process = proc
        simulation_status["running"] = True
        simulation_status["started_at"] = datetime.now().strftime("%H:%M:%S")
        simulation_status["config"] = config
        return True, "Started"
    except Exception as e:
        return False, str(e)


def stop_simulation():
    global simulation_process, simulation_status
    
    if not simulation_status["running"]:
        return False, "Not running"
    
    try:
        if simulation_process:
            simulation_process.terminate()
            simulation_process = None
        simulation_status["running"] = False
        simulation_status["started_at"] = None
        return True, "Stopped"
    except Exception as e:
        return False, str(e)


def check_simulation_status():
    global simulation_process, simulation_status
    
    if simulation_status["running"] and simulation_process:
        if simulation_process.poll() is not None:
            simulation_status["running"] = False
            return False
        return True
    
    try:
        result = subprocess.run(['pgrep', '-f', 'bot.simulate_future'], capture_output=True, text=True)
        if result.returncode == 0:
            simulation_status["running"] = True
            return True
    except:
        pass
    
    simulation_status["running"] = False
    return False


def create_portfolio_table(history):
    """Create portfolio history table"""
    if not history:
        fig = go.Figure()
        fig.add_annotation(text="No history yet", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_white', height=350, margin=dict(l=10, r=10, t=30, b=10))
        return fig
    
    # Process history data - show last 20
    history = history[:20]
    
    times = []
    markets = []
    sides = []
    prices = []
    sizes = []
    amounts = []
    
    for h in history:
        market_title = h.get('title', h.get('market', 'N/A'))[:35]
        side = h.get('side', '')
        price = h.get('price', 0)
        size = h.get('size', 0)
        timestamp = h.get('timestamp', '')
        
        try:
            dt = datetime.fromtimestamp(int(timestamp))
            time_str = dt.strftime('%m/%d %H:%M')
        except:
            time_str = ''
        
        amount = size * price
        
        times.append(time_str)
        markets.append(market_title)
        sides.append(side if side else '-')
        prices.append(f"${price:.2f}" if price else "-")
        sizes.append(f"{size:.1f}" if size else "-")
        amounts.append(f"+${amount:.2f}" if side == 'SELL' else f"-${amount:.2f}" if side == 'BUY' else "$0")
    
    colors = []
    for s in sides:
        if s == 'BUY':
            colors.append('#e74c3c')
        elif s == 'SELL':
            colors.append('#00b894')
        else:
            colors.append('#999')
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Time', 'Market', 'Side', 'Price', 'Size', 'Amount'],
            fill_color='#0984e3',
            align='center',
            font=dict(color='white', size=10, weight='bold'),
            height=28
        ),
        cells=dict(
            values=[times, markets, sides, prices, sizes, amounts],
            fill_color=[['#fff'] * 20],
            align=['center', 'left', 'center', 'right', 'right', 'right'],
            font=dict(color='#333', size=9),
            height=24
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Recent Trades ({len(history)})", font=dict(size=14)),
        template='plotly_white',
        height=350,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    return fig


def create_positions_table(positions):
    """Create open positions table"""
    if not positions:
        fig = go.Figure()
        fig.add_annotation(text="No open positions", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_white', height=250, margin=dict(l=10, r=10, t=30, b=10))
        return fig
    
    markets = [p.get('title', p.get('market', 'N/A'))[:35] for p in positions]
    sides = [p.get('side', '') for p in positions]
    qty = [f"{p.get('qty', 0):.1f}" for p in positions]
    avg_price = [f"${p.get('avg_price', 0):.2f}" for p in positions]
    cost = [f"${p.get('cost', 0):.2f}" for p in positions]
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Market', 'Side', 'Qty', 'Avg Price', 'Cost'],
            fill_color='#6c5ce7',
            align='center',
            font=dict(color='white', size=10, weight='bold'),
            height=28
        ),
        cells=dict(
            values=[markets, sides, qty, avg_price, cost],
            fill_color=[['#fff'] * len(positions)],
            align=['left', 'center', 'right', 'right', 'right'],
            font=dict(color='#333', size=9),
            height=24
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Open Positions ({len(positions)})", font=dict(size=14)),
        template='plotly_white',
        height=250,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    return fig


def create_simulation_history_table(df):
    """Create simulation bet history table"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Belum ada bet - Mulai simulasi untuk melihat riwayat", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_white', height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='white')
        return fig
    
    df = df.tail(30)
    
    times = []
    questions = []
    actions = []
    odds = []
    entries = []
    exits = []
    profits = []
    results = []
    links = []
    
    for _, row in df.iterrows():
        ts = row.get('timestamp', '')
        if ts:
            if hasattr(ts, 'strftime'):
                times.append(ts.strftime('%H:%M:%S'))
            else:
                times.append(str(ts)[:8])
        else:
            times.append('')
        
        q = row.get('question', 'N/A')[:30]
        questions.append(q)
        
        actions.append(row.get('action', ''))
        odds.append(f"{row.get('odds', 0):.2f}x")
        entries.append(f"{row.get('entry_price', 0)*100:.1f}%")
        exits.append(f"{row.get('exit_price', 0)*100:.1f}%")
        
        profit = row.get('profit', 0)
        profits.append(f"+${profit:.2f}" if profit > 0 else f"-${abs(profit):.2f}")
        
        won = row.get('won', False)
        if won:
            result = '📈 WIN'
        else:
            result = '📉 LOSE'
        results.append(result)
        
        url = row.get('url', '')
        links.append(f'<a href="{url}" target="_blank">🔗</a>' if url else '-')
    
    colors = []
    for r in results:
        if 'WIN' in r:
            colors.append('#d4edda')
        else:
            colors.append('#f8d7da')
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Waktu', 'Pertanyaan', 'Aksi', 'Odds', 'Entry', 'Exit', 'Profit', 'Hasil', 'Link'],
            fill_color='#0984e3',
            align='center',
            font=dict(color='white', size=10, weight='bold'),
            height=30
        ),
        cells=dict(
            values=[times, questions, actions, odds, entries, exits, profits, results, links],
            fill_color=[colors * 9] if colors else [['#fff'] * 9],
            align=['center', 'left', 'center', 'right', 'right', 'right', 'right', 'center', 'center'],
            font=dict(color='#333', size=9),
            height=26
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Riwayat Bet ({len(df)} bet)", font=dict(size=14)),
        template='plotly_white',
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    return fig


def create_open_trades_table(open_bets):
    """Create open trades table"""
    if not open_bets:
        fig = go.Figure()
        fig.add_annotation(text="Tidak ada posisi terbuka", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_white', height=200, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='white')
        return fig
    
    questions = []
    actions = []
    odds = []
    entries = []
    amounts = []
    opened = []
    links = []
    
    for bet in open_bets:
        q = bet.get('question', 'N/A')[:30]
        questions.append(q)
        actions.append(bet.get('action', ''))
        odds.append(f"{bet.get('odds', 0):.2f}x")
        entries.append(f"{bet.get('entry_prob', 0)*100:.1f}%")
        amounts.append(f"${bet.get('amount', 0):.2f}")
        
        ts = bet.get('opened_at', '')
        if hasattr(ts, 'strftime'):
            opened.append(ts.strftime('%H:%M:%S'))
        else:
            opened.append(str(ts)[:8])
        
        url = bet.get('url', '')
        links.append(f'<a href="{url}" target="_blank">🔗</a>' if url else '-')
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Waktu', 'Pertanyaan', 'Aksi', 'Odds', 'Entry', 'Jumlah', 'Link'],
            fill_color='#f39c12',
            align='center',
            font=dict(color='white', size=10, weight='bold'),
            height=30
        ),
        cells=dict(
            values=[opened, questions, actions, odds, entries, amounts, links],
            fill_color=[['#fff3cd'] * len(open_bets)],
            align=['center', 'left', 'center', 'right', 'right', 'right', 'center'],
            font=dict(color='#333', size=9),
            height=26
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Posisi Terbuka ({len(open_bets)})", font=dict(size=14)),
        template='plotly_white',
        height=200,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    return fig


# Layout
app.layout = html.Div([
    dcc.Store(id='simulation-state', data={"running": False, "started_at": None}),
    dcc.Store(id='sim-config', data=SIM_CONFIG.copy()),
    
    html.Div([
        # Header
        html.Div([
            html.H4("🤖 Polymarket", style={'margin': '0', 'color': '#00b894', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Span(id='simulation-status-display', style={'fontSize': '11px', 'color': '#666', 'marginLeft': '8px'}),
            html.Button("▶", id="btn-toggle", n_clicks=0, style={
                'backgroundColor': '#00b894', 'color': 'white', 'border': 'none',
                'width': '32px', 'height': '32px', 'borderRadius': '4px', 'fontSize': '14px', 'float': 'right', 'cursor': 'pointer'
            })
        ], style={'padding': '10px 15px', 'backgroundColor': 'white', 'borderRadius': '8px', 'marginBottom': '10px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'}),
        
        # Config Panel
        html.Div([
            html.Div([
                html.Div("Saldo ($)", style={'fontSize': '11px', 'color': '#666'}),
                dcc.Input(id='cfg-balance', type='number', value=100, style={'width': '90px', 'height': '32px', 'fontSize': '13px'}),
            ], style={'display': 'inline-block', 'marginRight': '12px'}),
            html.Div([
                html.Div("Bet ($)", style={'fontSize': '11px', 'color': '#666'}),
                dcc.Input(id='cfg-bet', type='number', value=2, style={'width': '70px', 'height': '32px', 'fontSize': '13px'}),
            ], style={'display': 'inline-block', 'marginRight': '12px'}),
            html.Div([
                html.Div("Min Prob", style={'fontSize': '11px', 'color': '#666'}),
                dcc.Input(id='cfg-prob', type='number', value=0.70, step=0.05, style={'width': '70px', 'height': '32px', 'fontSize': '13px'}),
            ], style={'display': 'inline-block', 'marginRight': '12px'}),
            html.Div([
                html.Div("Max Open", style={'fontSize': '11px', 'color': '#666'}),
                dcc.Input(id='cfg-max-open', type='number', value=10, style={'width': '50px', 'height': '32px', 'fontSize': '13px'}),
            ], style={'display': 'inline-block', 'marginRight': '12px'}),
            html.Div([
                html.Div("Max %", style={'fontSize': '11px', 'color': '#666'}),
                dcc.Input(id='cfg-max-pct', type='number', value=0.30, step=0.05, style={'width': '70px', 'height': '32px', 'fontSize': '13px'}),
            ], style={'display': 'inline-block', 'marginRight': '12px'}),
            html.Div([
                html.Div("Menit (jeda)", style={'fontSize': '11px', 'color': '#666'}),
                dcc.Input(id='cfg-minutes', type='number', value=1, min=1, max=60, style={'width': '70px', 'height': '32px', 'fontSize': '13px'}),
            ], style={'display': 'inline-block', 'marginRight': '12px'}),
            html.Div([
                html.Div("Kategori", style={'fontSize': '11px', 'color': '#666'}),
                dcc.Dropdown(
                    id='cfg-category',
                    options=[
                        {'label': 'Semua', 'value': 'all'},
                        {'label': 'Sports', 'value': 'Sports'},
                        {'label': 'Politics', 'value': 'Politics'},
                        {'label': 'Crypto', 'value': 'Crypto'},
                        {'label': 'Economy', 'value': 'Economy'},
                        {'label': 'Tech', 'value': 'Tech'},
                        {'label': 'Culture', 'value': 'Culture'},
                    ],
                    value='all',
                    style={'width': '120px', 'fontSize': '12px', 'height': '32px'},
                    clearable=False
                ),
            ], style={'display': 'inline-block'}),
            html.Div([
                html.Button("🔄 Reset", id="btn-reset", n_clicks=0, style={
                    'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none',
                    'padding': '6px 12px', 'borderRadius': '4px', 'fontSize': '12px', 'cursor': 'pointer', 'marginTop': '18px'
                })
            ], style={'display': 'inline-block', 'marginLeft': '10px'}),
        ], style={'padding': '12px', 'backgroundColor': 'white', 'borderRadius': '8px', 'marginBottom': '12px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'}),
        
        # Tabs - hanya simulation
        dcc.Tabs(id='dashboard-tabs', value='simulation', children=[
            dcc.Tab(label='📊 Simulation', value='simulation', style={'fontSize': '12px', 'padding': '8px'}, selected_style={'fontSize': '12px', 'fontWeight': 'bold', 'padding': '8px'}),
        ]),
        
        # Link ke real portfolio
        html.Div([
            html.A("💰 Real Portfolio →", href="http://localhost:8051", target="_blank", style={'fontSize': '12px', 'color': '#0984e3', 'textDecoration': 'none', 'marginRight': '10px'}),
            html.A("🎮 Simulation →", href="http://localhost:8050", target="_blank", style={'fontSize': '12px', 'color': '#00b894', 'textDecoration': 'none'})
        ], style={'marginBottom': '10px', 'textAlign': 'right'}),
        
        # Tab Content
        html.Div(id='tab-content'),
        dcc.Tabs(id='trade-tabs', value='wins', children=[
            dcc.Tab(label='📈 Wins', value='wins', style={'fontSize': '12px'}, selected_style={'fontSize': '12px', 'fontWeight': 'bold'}),
            dcc.Tab(label='📉 Loses', value='loses', style={'fontSize': '12px'}, selected_style={'fontSize': '12px', 'fontWeight': 'bold'}),
        ]),
        html.Div(id='trade-tab-content'),
        
    ], style={'maxWidth': '1200px', 'margin': '0 auto', 'minHeight': '100vh'}),
    
    dcc.Interval(id='refresh-interval', interval=REFRESH_INTERVAL * 1000, n_intervals=0),
    
], style={'backgroundColor': '#f5f6fa', 'minHeight': '100vh', 'padding': '10px', 'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'})


@callback(
    Output('tab-content', 'children'),
    [Input('dashboard-tabs', 'value'),
     Input('refresh-interval', 'n_intervals'),
     Input('simulation-state', 'data')]
)
def render_tab(tab_value, n, sim_state):
    check_simulation_status()
    
    if tab_value == 'simulation':
        from dashboard.data_extractor import TradeLogExtractor
        extractor = TradeLogExtractor(SIMULATION_PATH)
        df = extractor.extract_daily_summary()
        
        loses_df = pd.DataFrame()
        loses_file = Path(SIMULATION_PATH) / datetime.now().strftime('%d-%m-%Y') / "loses.txt"
        if loses_file.exists():
            try:
                loses_df = extractor.extract_from_file(loses_file)
                loses_df = pd.DataFrame(loses_df) if loses_df else pd.DataFrame()
            except:
                loses_df = pd.DataFrame()
        
        return render_simulation_tab(df, loses_df)
    return render_simulation_tab(pd.DataFrame(), pd.DataFrame())


def render_simulation_tab(df, loses_df=pd.DataFrame()):
    balance, released_pnl, floating_pnl, running_pnl = get_pnl_stats()
    initial_balance = 100.0
    
    total_profit = 0
    if df.empty:
        balance_str = f"${balance:.2f}"
        profit_str = "$0.00"
        roi_str = "0.0%"
        bets_str = "0"
        winrate_str = "0%"
    else:
        current_balance = df['balance'].iloc[-1]
        total_profit = released_pnl
        roi = ((current_balance - initial_balance) / initial_balance * 100)
        balance_str = f"${current_balance:.2f}"
        profit_str = f"${total_profit:+.2f}"
        roi_str = f"{roi:+.1f}%"
        bets_str = str(len(df))
        wins = (df['profit'] > 0).sum()
        winrate_str = f"{(wins/len(df)*100):.1f}%" if len(df) > 0 else "0%"
    
    released_str = f"${released_pnl:+.2f}"
    floating_str = f"${floating_pnl:+.2f}"
    running_str = f"${running_pnl:+.2f}"
    
    # Main chart
    main_fig = create_dashboard(df, INITIAL_BALANCE)
    main_fig.update_layout(height=250)
    
    # Get bet history
    extractor = TradeLogExtractor(SIMULATION_PATH)
    bets_df = extractor.extract_simulation_trades()
    history_fig = create_history_table(bets_df)
    history_fig.update_layout(height=300)
    
    # Get open bets
    open_bets = extractor.get_open_bets()
    open_fig = create_open_trades_table(open_bets)
    open_fig.update_layout(height=200)
    
    return html.Div([
        # Mode indicator
        html.Div([
            html.Span("🎮 MODE: SIMULASI", style={'fontSize': '14px', 'fontWeight': 'bold', 'color': '#00b894'})
        ], style={'textAlign': 'center', 'marginBottom': '10px', 'padding': '8px', 'backgroundColor': '#e8f5e9', 'borderRadius': '8px'}),
        
        # Metrics Row - with PnL breakdown
        html.Div([
            html.Div([html.Div("Saldo", style={'fontSize': '11px', 'color': '#666'}), html.Div(balance_str, style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
            html.Div([html.Div("Released PnL", style={'fontSize': '11px', 'color': '#666'}), html.Div(released_str, style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894' if released_pnl >= 0 else '#e74c3c'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
            html.Div([html.Div("Floating PnL", style={'fontSize': '11px', 'color': '#666'}), html.Div(floating_str, style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894' if floating_pnl >= 0 else '#e74c3c'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
            html.Div([html.Div("Running PnL", style={'fontSize': '11px', 'color': '#666'}), html.Div(running_str, style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894' if running_pnl >= 0 else '#e74c3c'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
            html.Div([html.Div("Win Rate", style={'fontSize': '11px', 'color': '#666'}), html.Div(winrate_str, style={'fontSize': '18px', 'fontWeight': 'bold'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(5, 1fr)', 'gap': '10px', 'marginBottom': '15px'}),
        
        # Main Chart
        html.Div([dcc.Graph(figure=main_fig, style={'height': '280px'})], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px', 'marginBottom': '15px'}),
        
        # Open Trades
        html.Div([dcc.Graph(figure=open_fig, style={'height': '220px'})], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px', 'marginBottom': '15px'}),
        
        # Bet History
        html.Div([dcc.Graph(figure=history_fig, style={'height': '320px'})], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px'}),
    ])


@callback(
    Output('trade-tab-content', 'children'),
    [Input('trade-tabs', 'value'),
     Input('refresh-interval', 'n_intervals')]
)
def render_trade_tab(tab_value, n):
    from dashboard.data_extractor import TradeLogExtractor
    from dashboard.visualizations import create_history_table
    
    extractor = TradeLogExtractor(SIMULATION_PATH)
    
    if tab_value == 'wins':
        df = extractor.extract_daily_summary()
        df = df[df['profit'] > 0] if not df.empty else df
        title = "Recent WIN Trades"
    else:
        loses_file = Path(SIMULATION_PATH) / datetime.now().strftime('%d-%m-%Y') / "loses.txt"
        if loses_file.exists():
            try:
                loses = extractor.extract_from_file(loses_file)
                df = pd.DataFrame(loses) if loses else pd.DataFrame()
            except:
                df = pd.DataFrame()
        else:
            df = pd.DataFrame()
        title = "Recent LOSE Trades"
    
    if df.empty:
        return html.Div([
            html.Div("No trades yet", style={'textAlign': 'center', 'padding': '40px', 'color': '#999'})
        ])
    
    df = df.tail(30)
    fig = create_history_table(df)
    fig.update_layout(title=dict(text=f"{title} ({len(df)})", font=dict(size=14)))
    
    return html.Div([dcc.Graph(figure=fig, style={'height': '400px'})], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px'})


def render_portfolio_tab():
    wallet_info = get_wallet_balance()
    history, wallet_addr = get_portfolio_history()
    positions = get_positions()
    
    if not wallet_info['connected']:
        return html.Div([
            html.Div("⚠️ Wallet not connected. Please check PRIVATE_KEY in .env", style={'textAlign': 'center', 'padding': '40px', 'color': '#e74c3c', 'fontSize': '14px', 'backgroundColor': 'white', 'borderRadius': '8px'})
        ])
    
    # Get values from API
    positions_value = wallet_info.get('positions_value', 0)
    positions_count = wallet_info.get('positions_count', 0)
    trades_count = wallet_info.get('trades_count', 0)
    
    # Calculate net flow
    if history:
        net_buy = sum(h.get('size', 0) * h.get('price', 0) for h in history if h.get('side') == 'BUY')
        net_sell = sum(h.get('size', 0) * h.get('price', 0) for h in history if h.get('side') == 'SELL')
        net_flow = net_sell - net_buy
    else:
        net_flow = 0
    
    return html.Div([
        # Summary Cards - show position value not cash
        html.Div([
            html.Div([html.Div("Positions Value", style={'fontSize': '10px', 'color': '#999'}), html.Div(f"${positions_value:,.2f}", style={'fontSize': '20px', 'color': '#00b894', 'fontWeight': 'bold'})], style={'padding': '12px', 'backgroundColor': 'white', 'borderRadius': '8px', 'textAlign': 'center'}),
            html.Div([html.Div("Total Trades", style={'fontSize': '10px', 'color': '#999'}), html.Div(str(trades_count), style={'fontSize': '20px', 'fontWeight': 'bold'})], style={'padding': '12px', 'backgroundColor': 'white', 'borderRadius': '8px', 'textAlign': 'center'}),
            html.Div([html.Div("Open Positions", style={'fontSize': '10px', 'color': '#999'}), html.Div(str(positions_count), style={'fontSize': '20px', 'fontWeight': 'bold'})], style={'padding': '12px', 'backgroundColor': 'white', 'borderRadius': '8px', 'textAlign': 'center'}),
            html.Div([html.Div("Net Flow", style={'fontSize': '10px', 'color': '#999'}), html.Div(f"${net_flow:+,.2f}", style={'fontSize': '20px', 'fontWeight': 'bold', 'color': '#00b894' if net_flow >= 0 else '#e74c3c'})], style={'padding': '12px', 'backgroundColor': 'white', 'borderRadius': '8px', 'textAlign': 'center'}),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '10px', 'marginBottom': '10px'}),
        
        # Wallet address
        html.Div([html.Div(f"Wallet: {wallet_addr[:10]}...{wallet_addr[-6:]}" if wallet_addr else "N/A", style={'fontSize': '10px', 'color': '#666', 'textAlign': 'center'})], style={'padding': '8px', 'backgroundColor': 'white', 'borderRadius': '8px', 'marginBottom': '10px'}),
        
        # Positions
        html.Div([dcc.Graph(id='positions-table', figure=create_positions_table(positions), style={'height': '200px'})], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px', 'marginBottom': '10px'}),
        
        # History
        html.Div([dcc.Graph(id='history-table', figure=create_portfolio_table(history), style={'height': '350px'})], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px'}),
    ])


# Callback for start/stop
@callback(
    [Output('simulation-state', 'data'),
     Output('simulation-status-display', 'children'),
     Output('btn-toggle', 'children'),
     Output('btn-toggle', 'style')],
    [Input('btn-toggle', 'n_clicks')],
    [State('simulation-state', 'data'),
     State('cfg-balance', 'value'),
     State('cfg-bet', 'value'),
     State('cfg-prob', 'value'),
     State('cfg-max-open', 'value'),
     State('cfg-max-pct', 'value'),
     State('cfg-minutes', 'value'),
     State('cfg-category', 'value')]
)
def handle_simulation_controls(clicks, current_state, balance, bet, prob, max_open, max_pct, minutes, category):
    if clicks is None or clicks == 0:
        is_running = check_simulation_status()
        if is_running:
            current_state = {"running": True, "started_at": current_state.get("started_at")}
            return current_state, "🟢 Sim running", "⏹", {'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none', 'width': '32px', 'height': '32px', 'borderRadius': '4px', 'fontSize': '14px', 'cursor': 'pointer'}
        return current_state, "⚪ Ready", "▶", {'backgroundColor': '#00b894', 'color': 'white', 'border': 'none', 'width': '32px', 'height': '32px', 'borderRadius': '4px', 'fontSize': '14px', 'cursor': 'pointer'}
    
    config = {
        "balance": balance if balance else 100,
        "bet_size": bet if bet else 2,
        "min_prob": prob if prob else 0.70,
        "max_open_bets": max_open if max_open else 10,
        "max_open_pct": max_pct if max_pct else 0.30,
        "minutes": minutes if minutes else 60,
        "category": category if category else 'all'
    }
    
    if current_state.get("running", False):
        success, msg = stop_simulation()
        return {"running": False, "started_at": None}, "⏹ Stopped", "▶", {'backgroundColor': '#00b894', 'color': 'white', 'border': 'none', 'width': '32px', 'height': '32px', 'borderRadius': '4px', 'fontSize': '14px', 'cursor': 'pointer'}
    else:
        success, msg = start_simulation(config)
        if success:
            return {"running": True, "started_at": datetime.now().strftime("%H:%M:%S")}, "🟢 Running", "⏹", {'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none', 'width': '32px', 'height': '32px', 'borderRadius': '4px', 'fontSize': '14px', 'cursor': 'pointer'}
        return current_state, f"❌ {msg}", "▶", {'backgroundColor': '#00b894', 'color': 'white', 'border': 'none', 'width': '32px', 'height': '32px', 'borderRadius': '4px', 'fontSize': '14px', 'cursor': 'pointer'}


@callback(
    Output('btn-reset', 'n_clicks'),
    Input('btn-reset', 'n_clicks')
)
def handle_reset(clicks):
    if clicks and clicks > 0:
        try:
            from bot.simulate_future import reset_balance
            reset_balance()
            return 0
        except Exception as e:
            print(f"Reset error: {e}")
    return clicks


if __name__ == "__main__":
    print(f"\n🚀 Dashboard: http://localhost:8050")
    app.run(debug=True, port=8050)