#!/bin/bash
# Run Polymarket bot in background

cd "$(dirname "$0")"

# Check if already running
if pgrep -f "bot.scan" > /dev/null; then
    echo "Bot is already running!"
    exit 1
fi

echo "Starting Polymarket bot in background..."
nohup ./venv/bin/python -m bot.scan > bot_background.log 2>&1 &

echo "Bot started! PID: $(pgrep -f 'bot.scan')"
echo "Log file: bot_background.log"
echo ""
echo "Commands:"
echo "  tail -f bot_background.log  - View logs"
echo "  pgrep -f 'bot.scan'         - Check if running"
echo "  pkill -f 'bot.scan'         - Stop bot"