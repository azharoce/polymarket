"""
Real Trading Dashboard for Polymarket
Separate from simulation - uses real wallet and API
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

os.environ['PYTHONPATH'] = '.'
os.environ['DASH_SUPPRESS'] = '1'

from dotenv import load_dotenv
load_dotenv()

import dash
from dash import dcc, html, callback, Output, Input, State
import pandas as pd

from dashboard.data_extractor import TradeLogExtractor as SimExtractor

REAL_TRADING_PATH = "trading"
DATA_API_URL = "https://data-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"

ACCOUNT_INFO = {
    "username": "arrosis-azharuddin",
    "email": "arrosisazharuddin58@gmail.com"
}

app = dash.Dash(__name__, title="Polymarket Real")

INITIAL_BALANCE = 0


def get_wallet_info():
    """Get wallet info from Polymarket API"""
    try:
        from bot.auth import load_wallet
        wallet = load_wallet()
        
        if not wallet:
            return {"connected": False, "address": None, "balance": 0, "status": "No wallet"}
        
        from bot.portfolio import get_client
        client, balance = get_client()
        
        if not client:
            return {"connected": False, "address": wallet.address, "balance": 0, "status": "API error"}
        
        return {
            "connected": True,
            "address": wallet.address,
            "balance": balance,
            "status": "Connected"
        }
    except Exception as e:
        return {"connected": False, "error": str(e), "status": f"Error: {e}"}


def get_positions():
    """Get open positions from API"""
    try:
        from bot.auth import load_wallet
        wallet = load_wallet()
        
        if not wallet:
            return []
        
        from bot.portfolio import get_trades_from_api, get_positions_from_trades
        trades = get_trades_from_api(wallet.address, limit=200)
        positions = get_positions_from_trades(trades)
        
        return positions
    except Exception as e:
        print(f"Error getting positions: {e}")
        return []


def get_trade_history():
    """Get trade history from API"""
    try:
        from bot.auth import load_wallet
        wallet = load_wallet()
        
        if not wallet:
            return [], 0
        
        from bot.portfolio import get_trades_from_api
        trades = get_trades_from_api(wallet.address, limit=200)
        
        total_pnl = 0
        for t in trades:
            pnl = t.get('profit', 0)
            if t.get('side') == 'BUY':
                total_pnl -= pnl
            else:
                total_pnl += pnl
        
        return trades, total_pnl
    except Exception as e:
        print(f"Error getting trades: {e}")
        return [], 0


def get_real_pnl_stats():
    """Get PnL stats for real trading"""
    try:
        wallet_info = get_wallet_info()
        
        if not wallet_info.get('connected'):
            return 0, 0, 0, 0
        
        positions = get_positions()
        trades, total_pnl = get_trade_history()
        
        floating_pnl = 0
        for p in positions:
            cost = p.get('cost', 0)
            value = p.get('value', 0)
            floating_pnl += (value - cost)
        
        released_pnl = total_pnl - floating_pnl
        running_pnl = total_pnl
        
        return wallet_info.get('balance', 0), released_pnl, floating_pnl, running_pnl
    except Exception as e:
        print(f"Error: {e}")
        return 0, 0, 0, 0


app.layout = html.Div([
    dcc.Interval(id='refresh-interval', interval=10 * 1000, n_intervals=0),
    
    html.Div([
        html.Div([
            html.H4("💰 Polymarket Real", style={'margin': '0', 'color': '#0984e3', 'fontWeight': 'bold'}),
            html.Span(id='wallet-status', style={'fontSize': '11px', 'color': '#666', 'marginLeft': '8px'})
        ], style={'padding': '10px 15px', 'backgroundColor': 'white', 'borderRadius': '8px', 'marginBottom': '10px'}),
        
        html.Div(id='wallet-info', style={'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px', 'marginBottom': '10px'}),
        
        html.Div(id='pnl-stats', style={'marginBottom': '10px'}),
        
        html.Div(id='positions-table', style={'marginBottom': '10px'}),
        
        html.Div(id='history-table'),
        
    ], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '10px'}),
    
], style={'backgroundColor': '#f5f6fa', 'minHeight': '100vh', 'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'})


@callback(
    Output('wallet-status', 'children'),
    Input('refresh-interval', 'n_intervals')
)
def update_wallet_status(n):
    info = get_wallet_info()
    if info.get('connected'):
        addr = info.get('address', '')
        return f"✅ {addr[:10]}...{addr[-6:]}"
    return "❌ Not connected"


@callback(
    Output('wallet-info', 'children'),
    Input('refresh-interval', 'n_intervals')
)
def update_wallet_info(n):
    info = get_wallet_info()
    
    if not info.get('connected'):
        return html.Div([
            html.Div("⚠️ Wallet not connected", style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '20px'}),
            html.Div("Add PRIVATE_KEY to .env file", style={'color': '#999', 'textAlign': 'center'})
        ])
    
    balance = info.get('balance', 0)
    addr = info.get('address', '')
    
    return html.Div([
        html.Div([
            html.Div("Username", style={'fontSize': '11px', 'color': '#666'}),
            html.Div(ACCOUNT_INFO.get('username', 'N/A'), style={'fontSize': '14px', 'fontWeight': 'bold', 'color': '#0984e3'})
        ], style={'display': 'inline-block', 'marginRight': '20px'}),
        html.Div([
            html.Div("Email", style={'fontSize': '11px', 'color': '#666'}),
            html.Div(ACCOUNT_INFO.get('email', 'N/A'), style={'fontSize': '12px'})
        ], style={'display': 'inline-block', 'marginRight': '20px'}),
        html.Div([
            html.Div("Wallet Address", style={'fontSize': '11px', 'color': '#666'}),
            html.Div(addr[:10] + '...' + addr[-6:] if len(addr) > 20 else addr, style={'fontSize': '12px', 'wordBreak': 'break-all'})
        ], style={'display': 'inline-block'}),
        html.Div([
            html.Div("Balance", style={'fontSize': '11px', 'color': '#666'}),
            html.Div(f"${balance:.4f}", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894'})
        ])
    ])


@callback(
    Output('pnl-stats', 'children'),
    Input('refresh-interval', 'n_intervals')
)
def update_pnl_stats(n):
    balance, released, floating, running = get_real_pnl_stats()
    
    return html.Div([
        html.Div([html.Div("Balance", style={'fontSize': '11px', 'color': '#666'}), html.Div(f"${balance:.4f}", style={'fontSize': '18px', 'fontWeight': 'bold'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
        html.Div([html.Div("Released PnL", style={'fontSize': '11px', 'color': '#666'}), html.Div(f"${released:.2f}", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894' if released >= 0 else '#e74c3c'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
        html.Div([html.Div("Floating PnL", style={'fontSize': '11px', 'color': '#666'}), html.Div(f"${floating:.2f}", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894' if floating >= 0 else '#e74c3c'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
        html.Div([html.Div("Running PnL", style={'fontSize': '11px', 'color': '#666'}), html.Div(f"${running:.2f}", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#00b894' if running >= 0 else '#e74c3c'})], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': 'white', 'borderRadius': '8px'}),
    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '10px', 'marginBottom': '10px'})


@callback(
    Output('positions-table', 'children'),
    Input('refresh-interval', 'n_intervals')
)
def update_positions(n):
    positions = get_positions()
    
    if not positions:
        return html.Div("No open positions", style={'textAlign': 'center', 'padding': '20px', 'color': '#999', 'backgroundColor': 'white', 'borderRadius': '8px'})
    
    import plotly.graph_objects as go
    
    markets = [p.get('title', 'N/A')[:40] for p in positions]
    sides = [p.get('side', '') for p in positions]
    qty = [f"{p.get('qty', 0):.2f}" for p in positions]
    avg = [f"${p.get('avg_price', 0):.2f}" for p in positions]
    cost = [f"${p.get('cost', 0):.2f}" for p in positions]
    
    fig = go.Figure(data=[go.Table(
        header=dict(values=['Market', 'Side', 'Qty', 'Avg Price', 'Cost'], fill_color='#6c5ce7', align='center', font=dict(color='white', size=10)),
        cells=dict(values=[markets, sides, qty, avg, cost], align=['left', 'center', 'right', 'right', 'right'], font=dict(size=9))
    )])
    fig.update_layout(title=f"Open Positions ({len(positions)})", height=200, margin=dict(l=10, r=10, t=30, b=10))
    
    return html.Div([dcc.Graph(figure=fig)], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px'})


@callback(
    Output('history-table', 'children'),
    Input('refresh-interval', 'n_intervals')
)
def update_history(n):
    trades, _ = get_trade_history()
    
    if not trades:
        return html.Div("No trade history", style={'textAlign': 'center', 'padding': '20px', 'color': '#999', 'backgroundColor': 'white', 'borderRadius': '8px'})
    
    trades = trades[:30]
    
    import plotly.graph_objects as go
    
    times = []
    markets = []
    sides = []
    prices = []
    sizes = []
    pnls = []
    
    for t in trades:
        ts = t.get('timestamp', '')
        if ts:
            try:
                dt = datetime.fromtimestamp(ts)
                times.append(dt.strftime('%m/%d %H:%M'))
            except:
                times.append('')
        else:
            times.append('')
        
        title = t.get('title', t.get('question', 'N/A'))[:35]
        markets.append(title)
        sides.append(t.get('side', ''))
        prices.append(f"${t.get('price', 0):.2f}")
        sizes.append(f"{t.get('size', 0):.2f}")
        
        pnl = t.get('profit', 0)
        pnls.append(f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}")
    
    colors = ['#d4edda' if pnl.startswith('+') else '#f8d7da' for pnl in pnls]
    
    fig = go.Figure(data=[go.Table(
        header=dict(values=['Time', 'Market', 'Side', 'Price', 'Size', 'P&L'], fill_color='#0984e3', align='center', font=dict(color='white', size=10)),
        cells=dict(values=[times, markets, sides, prices, sizes, pnls], fill_color=[colors * 6], align=['center', 'left', 'center', 'right', 'right', 'right'], font=dict(size=9))
    )])
    fig.update_layout(title=f"Trade History ({len(trades)})", height=400, margin=dict(l=10, r=10, t=30, b=10))
    
    return html.Div([dcc.Graph(figure=fig)], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '10px'})


if __name__ == "__main__":
    print(f"\n💰 Real Trading Dashboard: http://localhost:8051")
    app.run(debug=True, port=8051)
