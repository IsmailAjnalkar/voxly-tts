#!/usr/bin/env bash
# Run every minute by voxly-watchdog.timer. Restarts the app after 2 failed
# health checks in a row and, if ALERT_URL is set (any webhook that accepts a
# plain-text POST, e.g. https://ntfy.sh/<your-topic>), sends an alert.
STATE=/run/voxly-watchdog.fails
ALERT_URL=${ALERT_URL:-}

alert() { logger -t voxly-watchdog "$1"; [ -n "$ALERT_URL" ] && curl -s --max-time 10 -d "$1" "$ALERT_URL" >/dev/null; }

if curl -sf --max-time 10 http://127.0.0.1:8000/api/health >/dev/null; then
  if [ -s "$STATE" ]; then alert "text-2-speech.com recovered"; fi
  rm -f "$STATE"
  exit 0
fi
fails=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 ))
echo "$fails" > "$STATE"
if [ "$fails" -eq 2 ]; then
  systemctl restart voxly
  alert "text-2-speech.com health check failed twice; voxly restarted"
fi
