#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# find_backend_ip.sh — Detect the LAN IP for EduSync backend
#
# Priority: WiFi (wlp4s0) > Ethernet/Tether (enp5s0f3u1)
#
# Usage:
#   ./find_backend_ip.sh              # print IP + ready-to-paste commands
#   eval $(./find_backend_ip.sh -e)   # export EXPO_PUBLIC_API_URL directly
# ─────────────────────────────────────────────────────────────

WIFI_IF="wlp4s0"
ETH_IF="enp5s0f3u1"
PORT=8000

get_ip() {
    ip -4 addr show "$1" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1
}

WIFI_IP=$(get_ip "$WIFI_IF")
ETH_IP=$(get_ip "$ETH_IF")

# Pick the best available IP
if [[ -n "$WIFI_IP" ]]; then
    SELECTED_IP="$WIFI_IP"
    SELECTED_IF="$WIFI_IF (WiFi)"
elif [[ -n "$ETH_IP" ]]; then
    SELECTED_IP="$ETH_IP"
    SELECTED_IF="$ETH_IF (Ethernet/Tether)"
else
    echo "ERROR: No IP found on $WIFI_IF or $ETH_IF. Are you connected to a network?" >&2
    exit 1
fi

# Export mode: just print the export statement for eval
if [[ "$1" == "-e" ]]; then
    echo "export EXPO_PUBLIC_API_URL=http://${SELECTED_IP}:${PORT}"
    exit 0
fi

# Normal mode: print a summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  EduSync Backend IP Detection"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  WiFi   ($WIFI_IF):     ${WIFI_IP:-DOWN}"
echo "  Ether  ($ETH_IF): ${ETH_IP:-DOWN}"
echo ""
echo "  Selected: $SELECTED_IP  ($SELECTED_IF)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Quick start commands:"
echo ""
echo "  # 1. Start backend:"
echo "  cd backend && python main.py"
echo ""
echo "  # 2. Start Expo (paste this):"
echo "  cd EduSyncApp && EXPO_PUBLIC_API_URL=http://${SELECTED_IP}:${PORT} npx expo start"
echo ""
echo "  # Or update config.ts BACKEND_IP to: ${SELECTED_IP}"
echo ""
