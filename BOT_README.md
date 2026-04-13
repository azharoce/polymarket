# Polymarket Trading Bot

## Quick Start

### Jalankan Simulation (Baru)
```bash
source venv/bin/activate
python3 -m bot.trading_live --balance 100 --loop
```

### Lanjutkan Simulation yang Sudah Ada
Bot secara otomatis akan melanjutkan dari saldo terakhir. Kamu tidak perlu melakukan apapun - cukup jalankan seperti biasa:

```bash
source venv/bin/activate
python3 -m bot.trading_live --balance 100 --loop
```

Bot akan:
1. Membaca saldo terakhir dari file `simulation/DD-MM-YYYY/summary.txt`
2. Melanjutkan trading dari saldo tersebut

## Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--balance` | Initial balance | 100 |
| `--loop` | Run continuously | false |
| `--interval` | Interval between scans (seconds) | 60 |
| `--min-prob` | Min probability threshold | 0.70 |
| `--max-losses` | Max consecutive losses | 5 |
| `--bet-pct` | Bet as % of balance | 0.1 |

## Dashboard

Jalankan dashboard untuk melihat visualisasi:
```bash
source venv/bin/activate
python3 -m dashboard.app
```

Buka http://localhost:8050

Tabs:
- **Simulation** - Grafik dan statistik simulasi
- **Real Portfolio** - Riwayat trades dan posisi nyata dari Polymarket

## Log Structure

```
simulation/
├── DD-MM-YYYY/
│   ├── HH/
│   │   └── MM.txt    # Trade logs per menit
│   └── summary.txt    # Ringkasan harian
```

## Notes

- Simulation mode selalu WIN (untuk testing strategi)
- Real trading belum diimplementasikan
- Bot akan stop otomatis setelah 5x kalah berturut-turut