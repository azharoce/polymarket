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