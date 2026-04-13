# Polymarket Scanner & Backtest Guide

## 🚀 Quick Start

```bash
cd /Users/azharuddinarrosis/Developments/polymarket
source venv/bin/activate
```

---

## 📊 Scanner Commands

### 1. Live Scanner - Semua Kategori (Per Category)
```bash
python -m bot.scanner --save
```
Output:
- **HIGH PROBABILITY** - pisah per kategori (Crypto, Sports, dll)
- **UPCOMING EVENTS** - market yang lagi berjalan (50-50)
- **RESOLVED** - market yang sudah selesai

### 2. Scanner Loop (Continuous Monitoring)
```bash
python -m bot.scanner --loop --save
```
Scan every 60 seconds, auto-save daily signal

### 3. Custom Probability Threshold
```bash
python -m bot.scanner --min-prob 0.80 --save  # 80%+
python -m bot.scanner --min-prob 0.90 --save  # 90%+
```

### 4. Filter by Volume
```bash
python -m bot.scanner --min-vol 5000 --save  # min $5k volume
```

---

## 📈 Backtest Commands

### 1. Historical Analysis (Resolved Markets)
```bash
python -m bot.backtest
```
Output:
- Win rate dari market yang sudah selesai
- Profit calculation dengan modal $10, bet $2
- Per kategori juga

### 2. Custom Backtest Parameters
```bash
python -m bot.backtest --days 30 --balance 10 --size 2 --min-prob 0.70
```
- `--days`: Jumlah hari simulasi
- `--balance`: Modal awal ($)
- `--size`: Besar bet per trade ($)
- `--min-prob`: Threshold probabilitas (0.0-1.0)

---

## 📁 Output Files

| File | Location | Description |
|------|----------|-------------|
| Daily Signal | `signals/signal_YYYY-MM-DD.txt` | High prob markets per category + URL |
| Backtest Logs | `backtest/MM-DD-YYYY_HH-MM/` | Trade history per run |

---

## 🎯 Strategy

### High Probability Trading
1. **Ambil market dengan prob >70%** atau **<30%**
2. **Action:**
   - Prob >70% → BET YES (odds ~1.4x)
   - Prob <30% → BET NO (odds ~3.3x)
3. **Expected Win Rate:** ~80-90% (from historical data)

### Risk Management
- **Max bet per trade:** 10-20% modal
- **Stop loss:** 3 consecutive losses
- **Daily limit:** 5% max loss

---

## 📋 Available Categories

| Code | Category |
|------|----------|
| 1 | Sports |
| 2 | Politics |
| 3 | Crypto |
| 4 | Economy |
| 5 | Tech |
| 6 | Culture |
| 7 | Weather |
| 8 | Esports |
| a | All Categories |

---

## 🔧 Advanced Usage

### Scanner dengan kategori tertentu
```bash
python -m bot.scanner --min-prob 0.75 --min-vol 5000 --save
```

### Backtest kategori tertentu
```bash
python -m bot.backtest --category Sports
python -m bot.backtest --category Crypto
```

---

## ⚠️ Disclaimer

- Historical win rate 100% tidak menjamin future performance
- Always use proper risk management
- Test with small amounts first