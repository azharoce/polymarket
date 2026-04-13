# Dashboard Creation Plan for Polymarket Trading Bot

## Objective
Create an interactive dashboard showing compound growth from trading bot simulations.

## Data Sources
1. Trade log files in `/simulation/DD-MM-YYYY/HH/MM.txt` format
2. Daily summary files in `/simulation/DD-MM-YYYY/summary.txt`

## Plan

### Phase 1: Data Extraction & Processing
1. Create a Python script to parse all trade log files
2. Extract timestamp, balance, and trade details from each log entry
3. Build a time-series DataFrame with columns: timestamp, balance, profit, trade_count
4. Handle duplicate entries and ensure chronological order

### Phase 2: Visualization Components
1. **Main Chart**: Interactive line chart showing balance over time (compound growth)
2. **Secondary Charts**:
   - Daily profit/loss bar chart
   - Trade frequency heatmap (hour of day vs day of week)
   - Win rate pie chart
   - Distribution of profits histogram
3. **Metrics Display**:
   - Current balance
   - Total profit/loss
   - Win rate (%)
   - Average profit per trade
   - Sharpe ratio (if applicable)
   - Max drawdown

### Phase 3: Dashboard Implementation
1. Use Plotly Dash or Streamlit for interactive web dashboard
2. Implement date range selector
3. Add auto-refresh capability for live simulation data
4. Include export functionality (CSV, PNG)

### Phase 4: Integration & Testing
1. Ensure consistent logging format between simulation and real trades
2. Test with historical data
3. Validate against session summaries
4. Optimize performance for large datasets

## Technical Details

### Log Format Standardization
Both simulation and real trades should use identical log format:
```
[YYYY-MM-DD HH:MM:SS] ACTION ODDSx | Bet: $X.XX | RESULT | Profit: $X.XX | Balance: $X.XX | Category: CATEGORY | URL: URL
```

### Data Processing Pipeline
1. File discovery: Recursively find all .txt files in simulation directory
2. File parsing: Extract structured data from each log line
3. Data cleaning: Remove duplicates, sort by timestamp
4. Aggregation: Calculate running balances, daily stats, etc.

### Dashboard Features
1. Time range selection (last hour, today, week, all time)
2. Real-time updates (polling interval)
3. Interactive elements (hover tooltips, zoom, pan)
4. Responsive design (mobile/desktop)
5. Dark/light theme toggle

## Implementation Steps
1. Create data extraction module (`dashboard/data_extractor.py`)
2. Create visualization module (`dashboard/visualizations.py`)
3. Create main dashboard app (`dashboard/app.py`)
4. Create utilities for logging consistency (`dashboard/logging_utils.py`)
5. Add requirements file
6. Test with existing data