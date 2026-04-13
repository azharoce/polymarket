# Real-Bot Documentation

## Overview

Real-bot is a Polymarket trading bot with simulation and real trading capabilities. It scans high-probability markets and executes trades automatically.

## Project Structure

```
real-bot/
├── bot/
│   └── autobet.py          # Main bot implementation
├── bot_controller.py       # Bot state management
├── server.py               # Flask API server
├── api.py                  # Market & balance APIs
├── simulation_api.py       # Simulation logic
├── dashboard/
│   └── app.py              # Streamlit dashboard
├── html/
│   └── index.html          # Web interface
├── .env                    # Configuration (credentials)
└── autobet_logs/           # Trade logs
```

## Quick Start

### 1. Setup Credentials

```bash
python get_polymarket_creds.py
```

This will guide you to get 3 layers of credentials from Polymarket:
- **Layer 1**: Wallet (Private Key)
- **Layer 2**: API Credentials (Key, Secret, Passphrase)
- **Layer 3**: RPC URL

### 2. Configure .env

```env
# Layer 1 - Wallet
POLY_PK=0x...
POLY_FUNDER_ADDRESS=0x...
POLY_SIGNATURE_TYPE=0

# Layer 2 - API
POLY_API_KEY=...
POLY_API_SECRET=...
POLY_API_PASSPHRASE=...

# Layer 3 - RPC
RPC_URL=https://polygon-rpc.com
CLOB_HTTP_URL=https://clob.polymarket.com
USDC_CONTRACT=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
```

### 3. Run the Bot

**Simulation Mode:**
```bash
python -m bot.autobet
```

**Real Trading Mode:**
```bash
python -m bot.autobet --real
```

**Loop Mode (continuous scanning):**
```bash
python -m bot.autobet --loop --interval 60
```

**Real + Loop:**
```bash
python -m bot.autobet --real --loop
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--balance` | Initial balance | 100.0 |
| `--min-prob` | Min probability threshold | 0.70 |
| `--max-losses` | Max consecutive losses | 5 |
| `--bet-pct` | Bet as % of balance | 0.1 |
| `--real` | Use real trading | false |
| `--loop` | Run continuously | false |
| `--interval` | Loop interval (seconds) | 60 |
| `--min-vol` | Min market volume | 1000 |

## Web Interface

Start the Flask server:

```bash
python server.py
```

Then open http://localhost:5001

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/balances` | GET | Get all balances |
| `/api/markets` | GET | Get markets |
| `/api/trades` | GET | Get trade history |
| `/api/bot/status` | GET | Bot status |
| `/api/bot/start` | POST | Start bot |
| `/api/bot/stop` | POST | Stop bot |
| `/api/simulation/start` | POST | Start simulation |
| `/api/simulation/stop` | POST | Stop simulation |

## Bot Modes

- **simulation**: Simulated trading (default)
- **dryrun**: Test mode without real trades
- **real**: Real money trading

## Trading Logic

1. **Scan Markets**: Fetch active markets from Polymarket API
2. **Filter**: Keep markets with volume > min_volume
3. **Find Opportunities**: Look for YES/NO with probability >= min_prob
4. **Calculate Odds**: Based on probability table
5. **Execute Trade**:
   - Simulation: Random outcome based on probability
   - Real: Place order via CLOB API
6. **Track**: Log trades and update balance
7. **Stop Conditions**:
   - Max consecutive losses reached
   - Balance too low

## Odds Table

| Probability | Odds |
|-------------|------|
| >= 95% | 1.05x |
| >= 90% | 1.15x |
| >= 85% | 1.25x |
| >= 80% | 1.35x |
| >= 75% | 1.45x |
| >= 70% | 1.60x |
| < 70% | 2.00x |

## Categories

The bot identifies market categories:
- Sports (NHL, NBA, NFL, etc.)
- Politics (President, election, Trump, etc.)
- Crypto (Bitcoin, Ethereum, etc.)
- Economy (GDP, inflation, Fed, etc.)
- Tech (AI, Apple, Google, etc.)
- Culture (album, movie, etc.)
- Weather (hurricane, earthquake, etc.)
- Esports (Dota, League, etc.)

## Logs

Trade logs are saved to:
```
autobet_logs/
├── DD-MM-YYYY/
│   ├── HH/
│   │   ├── MM.txt  # Per minute logs
│   │   └── ...
│   └── summary.txt
```

## Dashboard (Optional)

For Streamlit dashboard:
```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Security Notes

- Never commit `.env` file to version control
- Keep private keys secure
- Start with simulation mode to test
- Set appropriate loss limits