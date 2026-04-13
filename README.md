# Polymarket Trading Bot

Bot trading otomatis untuk Polymarket dengan fitur scan market, analisis kategori, dan auto trade.

## 🚀 Quick Start

```bash
cd /Users/azharuddinarrosis/Developments/polymarket
./venv/bin/python -m bot.scan
```

## 📋 Mode yang Tersedia

| Command | Fungsi |
|---------|--------|
| `./venv/bin/python -m bot.scan` | Real-time scanner + auto trade |
| `./venv/bin/python -m bot.dashboard` | Dashboard view |
| `./venv/bin/python -m bot.backtest` | Backtest strategy |
| `./venv/bin/python -m bot.category_cli` | Scan per kategori |
| `./venv/bin/python -m bot.portfolio` | Portfolio dashboard (balance, PnL, positions) |

## ⚡ Cara Running

### Menu Interaktif
```bash
chmod +x menu.sh
./menu.sh
```

### Manual Mode
```bash
./venv/bin/python -m bot.scan          # Real-time scanner (SIMULATION/DRY RUN default)
./venv/bin/python -m bot.dashboard    # Dashboard view
./venv/bin/python -m bot.backtest      # Backtest strategy
./venv/bin/python -m bot.category_cli # Category scanner
./venv/bin/python -m bot.cli           # Interactive mode with tabs
./venv/bin/python -m bot.portfolio    # Portfolio: balance, PnL, positions
./run.sh                               # Quick run scanner
```

### Background Mode (Tanpa Terminal)
```bash
# Start bot di background
nohup ./venv/bin/python -m bot.scan > bot_background.log 2>&1 &

# Commands untuk kontrol:
# - tail -f bot_background.log   # View logs
# - pgrep -f "bot.scan"         # Check running
# - pkill -f "bot.scan"         # Stop bot
```

### Mode Trading

```bash
# SIMULATION / DRY RUN (Default) - Tidak benar-benar trading
DRY_RUN=true ./venv/bin/python -m bot.scan

# REAL TRADING - Place order sebenarnya
DRY_RUN=false ./venv/bin/python -m bot.scan
```

**Atau ubah di file `.env`:**
```env
DRY_RUN=false  # true = simulation, false = real trading
```

**Log Files:**
| File | Keterangan |
|------|------------|
| `bot_trading.log` | Log umum |
| `bot_simulation.log` | Log simulasi (DRY RUN) |
| `bot_real_trades.log` | Log trading real |
| `bot_background.log` | Log background mode |

**Backtest Logs:**
```
backtest/{m-d-y_time}/
├── config.txt   # Konfigurasi
├── summary.txt  # Hasil akhir
└── trades.txt   # Semua trade详情
```

## ⚙️ Konfigurasi

Edit file `.env`:

```env
# Relayer API (dari Polymarket.com)
RELAYER_API_KEY=019d2216-8d1b-7ed1-b2a0-76932b1d41a3
RELAYER_API_KEY_ADDRESS=0x86cE9823998f6F323151aA613e751156Dc1b9486

# Private Key (wallet Ethereum)
PRIVATE_KEY=0x...

# Mode
DRY_RUN=true        # true = simulation, false = live trading
SCAN_INTERVAL=60   # dalam detik
```

## 📊 Link Penting

| Service | URL |
|---------|-----|
| Portfolio | https://polymarket.com/portfolio |
| Wallet Deposit | Kirim USDC ke address wallet |
| Event | https://polymarket.com/event/{slug} |

## 🎯 Strategi Trading

- **BUY**: Probability < 10% (underdog potential)
- **SELL**: Probability > 90% (lock profit)
- **Fokus**: High volume + Low spread

## 📁 Struktur File

```
polymarket/
├── bot/
│   ├── scan.py           # Main scanner (auto trading)
│   ├── dashboard.py     # Dashboard view
│   ├── backtest.py      # Backtest strategy
│   ├── category.py      # Category analysis
│   ├── category_cli.py  # Category CLI
│   ├── cli.py           # Interactive mode with tabs
│   ├── config.py        # Config
│   ├── auth.py          # Wallet auth
│   ├── market.py        # Market data
│   ├── trading.py        # Trade execution
│   ├── risk.py          # Risk management
│   └── portfolio.py      # Portfolio dashboard (NEW!)
├── .env                 # Environment variables
├── requirements.txt     # Python dependencies
├── bot_trading.log      # Trading logs
├── bot_simulation.log   # Simulation logs
├── bot_real_trades.log # Real trades logs
└── bot_background.log   # Background mode logs
```

## 🛑 Stop Bot

### Terminal Mode
Press `Ctrl+C` untuk stop

### Background Mode
```bash
# Stop bot yang running di background
pkill -f "bot.scan"

# Atau gunakan PID yang ditampilkan saat start
kill [PID]
```

## ⚠️ Peringatan

1. **Dry Run**: Mulai dengan `DRY_RUN=true`
2. **Deposit**: Pastikan ada USDC di wallet untuk trading
3. **Risk**: Bot menggunakan risk management (max 10% per trade)
