#!/bin/bash
# Closes running Chrome and launches your real Google Chrome with remote debugging enabled
echo "[*] Closing existing Chrome processes..."
killall "Google Chrome" 2>/dev/null
sleep 1

echo "[*] Launching your real Google Chrome with remote debugging on port 9222..."
open -a "Google Chrome" --args --remote-debugging-port=9222 "https://learn.better.efekta.com/gap/ui/self-study"

echo ""
echo "[✓] Google Chrome is now open with your personal profile."
echo "[*] Make sure you are on the Efekta dashboard or inside a lesson, then run:"
echo "    python bot.py"
