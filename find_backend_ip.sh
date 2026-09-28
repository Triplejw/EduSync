#!/usr/bin/env bash
set -euo pipefail

PORT=8000

if [[ "$(uname -s)" == "Darwin" ]]; then
  DEFAULT_IF="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}' || true)"
  SELECTED_IP="$(ipconfig getifaddr "$DEFAULT_IF" 2>/dev/null || true)"
  SELECTED_IF="$DEFAULT_IF"
else
  DEFAULT_IF="$(ip route show default 2>/dev/null | awk 'NR==1{print $5}' || true)"
  SELECTED_IP="$(ip -4 addr show "$DEFAULT_IF" 2>/dev/null | awk '/inet /{sub(/\/.*/, "", $2); print $2; exit}' || true)"
  SELECTED_IF="$DEFAULT_IF"
fi

if [[ -z "$SELECTED_IP" ]]; then
  echo "ERROR: No LAN IP found. Connect the Mac and phone to the same Wi-Fi." >&2
  exit 1
fi

if [[ "${1:-}" == "-e" ]]; then
  echo "export EXPO_PUBLIC_API_URL=http://${SELECTED_IP}:${PORT}"
  exit 0
fi

echo "EduSync LAN address: http://${SELECTED_IP}:${PORT} (${SELECTED_IF})"
echo "Backend: cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT}"
echo "Expo: cd EduSyncApp && EXPO_PUBLIC_API_URL=http://${SELECTED_IP}:${PORT} npx expo start --clear"
