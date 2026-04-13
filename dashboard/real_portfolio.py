"""
Real Portfolio Dashboard - Polymarket
Halaman terpisah untuk data wallet real
"""
import os
os.environ['PYTHONPATH'] = '.'
os.environ['DASH_SUPPRESS'] = '1'

import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

DATA_API_URL = "https://data-api.polymarket.com"


def get_wallet_info():
    """Get wallet info from API"""
    try:
        from bot.auth import load_wallet
        wallet = load_wallet()
        if not wallet:
            return None, None, None, 0
        
        import requests
        url = f"{DATA_API_URL}/trades"
        params = {"address": wallet.address, "limit": 200}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            history = response.json()
            return wallet.address, history, history, len(history)
        
        return wallet.address, [], [], 0
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, 0


def create_portfolio_table(history):
    """Create portfolio history table"""
    if not history:
        fig = go.Figure()
        fig.add_annotation(text="Belum ada riwayat", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_dark', height=350, margin=dict(l=10, r=10, t=30, b=10))
        return fig
    
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
            values=['Waktu', 'Market', 'Side', 'Harga', 'Jumlah', 'Total'],
            fill_color='#1a1a2e',
            align='center',
            font=dict(color='white', size=10, weight='bold'),
            height=28
        ),
        cells=dict(
            values=[times, markets, sides, prices, sizes, amounts],
            fill_color=[['#16213e'] * 20],
            align=['center', 'left', 'center', 'right', 'right', 'right'],
            font=dict(color='#fff', size=9),
            height=24
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Riwayat Trades ({len(history)})", font=dict(size=14, color='#fff')),
        template='plotly_dark',
        height=350,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    return fig


def get_positions():
    """Get open positions"""
    try:
        from bot.auth import load_wallet
        wallet = load_wallet()
        
        if not wallet:
            return []
        
        from bot.portfolio import get_trades_from_api, get_positions_from_trades
        trades = get_trades_from_api(wallet.address, limit=200)
        positions = get_positions_from_trades(trades)
        
        return positions
    except:
        return []


def create_positions_table(positions):
    """Create open positions table"""
    if not positions:
        fig = go.Figure()
        fig.add_annotation(text="Tidak ada posisi terbuka", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_dark', height=250, margin=dict(l=10, r=10, t=30, b=10))
        return fig
    
    markets = [p.get('title', p.get('market', 'N/A'))[:35] for p in positions]
    sides = [p.get('side', '') for p in positions]
    qty = [f"{p.get('qty', 0):.1f}" for p in positions]
    avg_price = [f"${p.get('avg_price', 0):.2f}" for p in positions]
    cost = [f"${p.get('cost', 0):.2f}" for p in positions]
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Market', 'Side', 'Jumlah', 'Harga Avg', 'Cost'],
            fill_color='#1a1a2e',
            align='center',
            font=dict(color='white', size=10, weight='bold'),
            height=28
        ),
        cells=dict(
            values=[markets, sides, qty, avg_price, cost],
            fill_color=[['#16213e'] * len(positions)],
            align=['left', 'center', 'right', 'right', 'right'],
            font=dict(color='#fff', size=9),
            height=24
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Posisi Terbuka ({len(positions)})", font=dict(size=14, color='#fff')),
        template='plotly_dark',
        height=250,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    return fig


# Create real portfolio app
real_app = dash.Dash(__name__, url_base_pathname='/real/', title="Polymarket - Real Portfolio")

real_app.layout = html.Div([
    html.Div([
        html.H4("💼 MODE: REAL TRADING", style={'margin': '0', 'color': '#0984e3', 'display': 'inline-block', 'fontWeight': 'bold'}),
        html.A("← Kembali ke Simulasi", href="/", style={'fontSize': '12px', 'color': '#666', 'marginLeft': '20px', 'textDecoration': 'none'}),
    ], style={'padding': '10px 15px', 'backgroundColor': 'white', 'borderRadius': '8px', 'marginBottom': '10px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'}),

    dcc.Interval(id='refresh', interval=30000, n_intervals=0),
    
    html.Div(id='content'),
    
], style={'backgroundColor': '#0f0f23', 'minHeight': '100vh', 'padding': '10px', 'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'})


@real_app.callback(
    Output('content', 'children'),
    Input('refresh', 'n_intervals')
)
def update_content(n):
    wallet_addr, history, _, trades_count = get_wallet_info()
    positions = get_positions()
    
    if not wallet_addr:
        return html.Div([
            html.Div("⚠️ Wallet belum terhubung. Silakan cek PRIVATE_KEY di .env", style={'textAlign': 'center', 'padding': '40px', 'color': '#e74c3c', 'fontSize': '14px', 'backgroundColor': 'white', 'borderRadius': '8px'})
        ])
    
    # Get positions value
    positions_value = sum(p.get('cost', 0) for p in positions)
    
    # Calculate net flow
    if history:
        net_buy = sum(h.get('size', 0) * h.get('price', 0) for h in history if h.get('side') == 'BUY')
        net_sell = sum(h.get('size', 0) * h.get('price', 0) for h in history if h.get('side') == 'SELL')
        net_flow = net_sell - net_buy
    else:
        net_flow = 0
    
    return html.Div([
        # Summary Cards
        html.Div([
            html.Div([html.Div("Nilai Posisi", style={'fontSize': '10px', 'color': '#aaa'}), html.Div(f"${positions_value:,.2f}", style={'fontSize': '20px', 'color': '#00b894', 'fontWeight': 'bold'})], style={'padding': '12px', 'backgroundColor': '#1a1a2e', 'borderRadius': '8px', 'textAlign': 'center'}),
            html.Div([html.Div("Total Trades", style={'fontSize': '10px', 'color': '#aaa'}), html.Div(str(trades_count), style={'fontSize': '20px', 'fontWeight': 'bold', 'color': '#fff'})], style={'padding': '12px', 'backgroundColor': '#1a1a2e', 'borderRadius': '8px', 'textAlign': 'center'}),
            html.Div([html.Div("Posisi Terbuka", style={'fontSize': '10px', 'color': '#aaa'}), html.Div(str(len(positions)), style={'fontSize': '20px', 'fontWeight': 'bold', 'color': '#fff'})], style={'padding': '12px', 'backgroundColor': '#1a1a2e', 'borderRadius': '8px', 'textAlign': 'center'}),
            html.Div([html.Div("Net Flow", style={'fontSize': '10px', 'color': '#aaa'}), html.Div(f"${net_flow:+,.2f}", style={'fontSize': '20px', 'fontWeight': 'bold', 'color': '#00b894' if net_flow >= 0 else '#e74c3c'})], style={'padding': '12px', 'backgroundColor': '#1a1a2e', 'borderRadius': '8px', 'textAlign': 'center'}),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '10px', 'marginBottom': '10px'}),
        
        # Wallet address
        html.Div([html.Div(f"Wallet: {wallet_addr[:10]}...{wallet_addr[-6:]}", style={'fontSize': '10px', 'color': '#aaa', 'textAlign': 'center', 'padding': '8px', 'backgroundColor': '#1a1a2e', 'borderRadius': '8px'})], style={'marginBottom': '10px'}),
        
        # Positions
        html.Div([dcc.Graph(figure=create_positions_table(positions), style={'height': '200px'})], style={'backgroundColor': '#1a1a2e', 'borderRadius': '8px', 'padding': '10px', 'marginBottom': '10px'}),
        
        # History
        html.Div([dcc.Graph(figure=create_portfolio_table(history), style={'height': '350px'})], style={'backgroundColor': '#1a1a2e', 'borderRadius': '8px', 'padding': '10px'}),
    ])


if __name__ == "__main__":
    print(f"\n💼 Real Portfolio: http://localhost:8050/real")
    real_app.run(debug=True, port=8050)