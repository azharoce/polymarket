"""
Visualization module for Polymarket Trading Bot Dashboard
Creates interactive charts using Plotly
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Optional


def create_balance_chart(df: pd.DataFrame, title: str = "Balance") -> go.Figure:
    """Create a line chart showing balance growth over time from trades"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_dark', height=200, margin=dict(l=40, r=20, t=30, b=20))
        return fig
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df.index + 1,
        y=df['balance'],
        mode='lines+markers',
        name='Balance',
        line=dict(color='#00d4aa', width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 170, 0.1)',
        hovertemplate='Trade #%{x}<br>$%{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color='#fff')),
        xaxis_title="Trade #",
        yaxis_title="$",
        xaxis=dict(color='#aaa', showgrid=False),
        yaxis=dict(color='#aaa', showgrid=True, gridcolor='#333'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#fff'),
        height=200,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    
    return fig


def create_pnl_chart(df: pd.DataFrame, title: str = "PnL") -> go.Figure:
    """Create a bar chart showing profit/loss per trade"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_dark', height=200, margin=dict(l=40, r=20, t=30, b=20))
        return fig
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    colors = ['#00d4aa' if x >= 0 else '#ff4757' for x in df['profit']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=df.index + 1,
            y=df['profit'],
            marker_color=colors,
            hovertemplate='Trade #%{x}<br>$%{y:.2f}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color='#fff')),
        xaxis_title="Trade #",
        xaxis=dict(color='#aaa', showgrid=False),
        yaxis=dict(color='#aaa', showgrid=True, gridcolor='#333'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#fff'),
        height=200,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    
    return fig


def create_trade_count_chart(df: pd.DataFrame, title: str = "Total Trades") -> go.Figure:
    """Create a chart showing cumulative trade count"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_dark', height=200, margin=dict(l=40, r=20, t=30, b=20))
        return fig
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['trade_num'] = range(1, len(df) + 1)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['trade_num'],
        y=df['trade_num'],
        mode='lines',
        name='Trades',
        line=dict(color='#5f27cd', width=2),
        fill='tozeroy',
        fillcolor='rgba(95, 39, 205, 0.2)',
        hovertemplate='Trade #%{x}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color='#fff')),
        xaxis_title="Trade #",
        yaxis_title="Count",
        xaxis=dict(color='#aaa', showgrid=False),
        yaxis=dict(color='#aaa', showgrid=True, gridcolor='#333'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#fff'),
        height=200,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    
    return fig


def create_history_table(df: pd.DataFrame) -> go.Figure:
    """Create a table showing recent trades"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No trades yet", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#999'))
        fig.update_layout(template='plotly_white', height=300, margin=dict(l=10, r=10, t=30, b=10))
        return fig
    
    df = df.tail(30).sort_values('timestamp', ascending=False)
    
    times = []
    for ts in df['timestamp']:
        if hasattr(ts, 'strftime'):
            times.append(ts.strftime('%H:%M:%S'))
        else:
            times.append(str(ts)[:8])
    
    questions = [str(q)[:30] if 'question' in df.columns and pd.notna(q) else 'N/A' for q in df.get('question', df.get('url', ['N/A']*len(df))).tolist()]
    actions = df['action'].tolist()
    odds = [f"{x:.2f}x" for x in df['odds'].tolist()]
    entries = [f"{x*100:.1f}%" if 'entry_price' in df.columns and pd.notna(x) else '-' for x in df.get('entry_price', [0]*len(df)).tolist()]
    exits = [f"{x*100:.1f}%" if 'exit_price' in df.columns and pd.notna(x) else '-' for x in df.get('exit_price', [0]*len(df)).tolist()]
    profits = [f"+${p:.2f}" if p >= 0 else f"-${abs(p):.2f}" for p in df['profit']]
    balances = [f"${b:.2f}" for b in df['balance'].tolist()]
    results = ['📈 WIN' if w else '📉 LOSE' for w in df.get('won', df['result'] == 'WIN').tolist()]
    
    colors = []
    for p in df['profit']:
        colors.append('#d4edda') if p >= 0 else colors.append('#f8d7da')
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Time', 'Action', 'Odds', 'Profit', 'Balance', 'Result'],
            fill_color='#0984e3',
            align='center',
            font=dict(color='white', size=10, weight='bold'),
            height=28
        ),
        cells=dict(
            values=[times, actions, odds, profits, balances, results],
            fill_color=[colors * 6],
            align=['center', 'center', 'right', 'right', 'right', 'center'],
            font=dict(color='#333', size=9),
            height=24
        )
    )])
    
    fig.update_layout(
        title=dict(text=f"Recent Trades ({len(df)})", font=dict(size=14)),
        template='plotly_white',
        height=320,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    return fig


def create_dashboard(df: pd.DataFrame, initial_balance: float = 100.0) -> go.Figure:
    """Create a complete dashboard with multiple charts"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Start simulation to see data", 
                          xref="paper", yref="paper", x=0.5, y=0.5, 
                          showarrow=False, font=dict(size=16, color='#666'))
        fig.update_layout(
            template='plotly_dark',
            height=250,
            paper_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['trade_num'] = range(1, len(df) + 1)
    df['cumulative_profit'] = df['profit'].cumsum()
    
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=(
            "Balance",
            "PnL",
            "Total Trades"
        ),
        specs=[
            [{"type": "scatter"}, {"type": "bar"}, {"type": "scatter"}]
        ],
        horizontal_spacing=0.1
    )
    
    # 1. Balance chart
    fig.add_trace(
        go.Scatter(
            x=df['trade_num'],
            y=df['balance'],
            mode='lines+markers',
            name='Balance',
            line=dict(color='#00d4aa', width=2),
            marker=dict(size=4),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 170, 0.1)',
            hovertemplate='Trade #%{x}<br>$%{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # 2. PnL bar chart
    colors = ['#00d4aa' if x >= 0 else '#ff4757' for x in df['profit']]
    fig.add_trace(
        go.Bar(
            x=df['trade_num'],
            y=df['profit'],
            marker_color=colors,
            hovertemplate='Trade #%{x}<br>$%{y:.2f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # 3. Cumulative trades
    fig.add_trace(
        go.Scatter(
            x=df['trade_num'],
            y=df['trade_num'],
            mode='lines',
            name='Trades',
            line=dict(color='#5f27cd', width=2),
            fill='tozeroy',
            fillcolor='rgba(95, 39, 205, 0.2)',
            hovertemplate='Trade #%{x}<extra></extra>'
        ),
        row=1, col=3
    )
    
    # Calculate metrics
    total_profit = df['profit'].sum()
    current_balance = df['balance'].iloc[-1] if len(df) > 0 else initial_balance
    wins = (df['profit'] > 0).sum()
    total_trades = len(df)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    roi = ((current_balance - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0
    
    fig.update_layout(
        title=dict(
            text=f"Balance: ${current_balance:.2f} | PnL: ${total_profit:+.2f} | Trades: {total_trades} | Win: {win_rate:.1f}%",
            font=dict(size=14, color='#fff')
        ),
        template='plotly_dark',
        height=250,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=50, b=30)
    )
    
    fig.update_xaxes(color='#aaa', showgrid=False, row=1, col=1)
    fig.update_yaxes(color='#aaa', showgrid=True, gridcolor='#333', row=1, col=1)
    fig.update_xaxes(color='#aaa', showgrid=False, row=1, col=2)
    fig.update_yaxes(color='#aaa', showgrid=True, gridcolor='#333', row=1, col=2)
    fig.update_xaxes(color='#aaa', showgrid=False, row=1, col=3)
    fig.update_yaxes(color='#aaa', showgrid=True, gridcolor='#333', row=1, col=3)
    
    return fig