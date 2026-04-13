#!/bin/bash

cd "$(dirname "$0")"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         ⚡ POLYMARKET TRADING BOT - SELECT MODE             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  [1] 📊 All Markets      - Scan semua market"
echo "  [2] 🏒 Sports           - NHL, NBA, NFL, dll"
echo "  [3] 🗳️  Politics         - Election, President, dll"
echo "  [4] ₿ Crypto            - Bitcoin, Ethereum, dll"
echo "  [5] 📈 Economy          - GDP, Inflation, Fed"
echo "  [6] 💻 Tech             - AI, Apple, Google"
echo "  [7] 🎬 Culture          - Album, Movie, GTA"
echo "  [8] 🌤️  Weather          - Hurricane, Storm"
echo "  [9] 🎮 Esports          - Dota, League"
echo ""
echo "  [s] 🔍 Quick Scan       - Scan sinyal saja"
echo "  [r] 🔴 REAL Trading     - Mode trading real"
echo ""
echo "  ───────────────────────────────────────────────────────────"
echo "  [d] 📈 Dashboard SIM     - http://localhost:8050"
echo "  [D] 💰 Dashboard REAL   - http://localhost:8051"
echo ""
echo "  [q] ❌ Quit"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

read -p "Pilih menu [1-9, s, r, d, D, q]: " choice

case $choice in
  1) ./venv/bin/python -m bot.cli --tab markets ;;
  2) ./venv/bin/python -m bot.cli --category Sports ;;
  3) ./venv/bin/python -m bot.cli --category Politics ;;
  4) ./venv/bin/python -m bot.cli --category Crypto ;;
  5) ./venv/bin/python -m bot.cli --category Economy ;;
  6) ./venv/bin/python -m bot.cli --category Tech ;;
  7) ./venv/bin/python -m bot.cli --category Culture ;;
  8) ./venv/bin/python -m bot.cli --category Weather ;;
  9) ./venv/bin/python -m bot.cli --category Esports ;;
  s) ./venv/bin/python -m bot.scan ;;
  r) DRY_RUN=false ./venv/bin/python -m bot.scan ;;
  d) echo "🚀 Starting Dashboard SIM..."; source venv/bin/activate && python -m dashboard.app ;;
  D) echo "💰 Starting Dashboard REAL..."; source venv/bin/activate && python -m dashboard.real_app ;;
  q) echo "👋 Goodbye!" ;;
  *) ./venv/bin/python -m bot.cli ;;
esac
