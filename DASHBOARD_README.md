# Polymarket Trading Bot Dashboard

## Overview
This dashboard visualizes the performance of the Polymarket trading bot, showing compound growth, trade statistics, and other key metrics from both simulation and real trading data.

## Features
- Interactive balance over time chart (compound growth visualization)
- Daily profit/loss analysis
- Trade frequency heatmaps
- Win rate and profit distribution analysis
- Real-time data updates for live simulation monitoring
- Export capabilities for further analysis

## Data Structure
The dashboard processes log files stored in the following structure:
```
/simulation/
├── DD-MM-YYYY/
│   ├── HH/
│   │   └── MM.txt          # Individual trade logs for each minute
│   └── summary.txt         # Daily summary of simulations
```

## Log Format Standardization
Both simulation and real trades use identical log format for consistent processing:
```
[YYYY-MM-DD HH:MM:SS] ACTION ODDSx | Bet: $X.XX | RESULT | Profit: $X.XX | Balance: $X.XX | Category: CATEGORY | URL: URL
```

Example:
```
[2026-04-09 15:45:35] NO 1.05x | Bet: $10.00 | WIN | Profit: $0.50 | Balance: $100.50 | Category: Sports | URL: https://polymarket.com/market/will-the-charlotte-hornets-win-the-2026-nba-finals
```

## Installation
```bash
# Activate virtual environment
source venv/bin/activate

# Install required packages
pip install matplotlib plotly pandas dash
```

## Usage
To run the dashboard:
```bash
source venv/bin/activate
python dashboard/app.py
```

Then open your browser to http://localhost:8050

## Components
1. **Data Extractor** (`dashboard/data_extractor.py`)
   - Parses all log files from the simulation directory
   - Extracts timestamps, balances, trade details
   - Builds cleaned time-series DataFrame

2. **Visualizations** (`dashboard/visualizations.py`)
   - Balance over time (line chart)
   - Daily P&L (bar chart)
   - Trade frequency heatmap
   - Win rate distribution
   - Profit/loss distribution

3. **Main App** (`dashboard/app.py`)
   - Dash application layout
   - Callback functions for interactivity
   - Auto-refresh mechanism for live data

4. **Logging Utilities** (`dashboard/logging_utils.py`)
   - Functions to ensure consistent logging format
   - Helpers for both simulation and real trade logging

## Future Enhancements
- Real-time WebSocket updates instead of polling
- Integration with actual Polymarket API for live data
- Advanced risk metrics (Sharpe ratio, Sortino ratio, etc.)
- Portfolio diversification analysis
- Strategy comparison views
- Mobile-responsive design improvements
- Custom date range presets
- Anomaly detection highlights

## Dependencies
- pandas: Data manipulation and analysis
- plotly: Interactive visualizations
- dash: Web application framework
- matplotlib: Additional plotting capabilities (backup)

## Notes
- The dashboard is designed to work with both historical and live data
- For live simulations, the dashboard can be set to auto-refresh at defined intervals
- All timestamps are stored in UTC for consistency
- Financial calculations use decimal precision to avoid floating-point errors