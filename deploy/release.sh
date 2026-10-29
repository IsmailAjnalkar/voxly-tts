#!/usr/bin/env bash
# Deploy the checked-out commit to /opt/voxly with backups and automatic rollback.
# Run as root on the VPS:  cd /root/voxly-tts && git pull --ff-only && bash deploy/release.sh
# Steps: app files -> restart + health check (rollback on failure) -> nginx config
# (nginx -t, restore on failure) -> watchdog timer.
set -euo pipefail
cd "$(dirname "$0")/.."
TS=$(date +%F-%H%M)
echo "deploying $(git log --oneline -1)"

tar czf /root/voxly-backup-$TS.tgz -C /opt/voxly server.py web requirements.txt
cp /etc/nginx/sites-available/voxly /root/nginx-voxly.bak-$TS
echo "backups: /root/voxly-backup-$TS.tgz /root/nginx-voxly.bak-$TS"

# ---- app
cp server.py requirements.txt /opt/voxly/
# web/ is replaced as a whole (copy, then swap) so files removed from the repo disappear too
rm -rf /opt/voxly/web.new /opt/voxly/web.old
cp -r web /opt/voxly/web.new && mv /opt/voxly/web /opt/voxly/web.old && mv /opt/voxly/web.new /opt/voxly/web && rm -rf /opt/voxly/web.old
cp deploy/voxly-watchdog.sh /opt/voxly/ && chmod 755 /opt/voxly/voxly-watchdog.sh
/opt/voxly/.venv/bin/pip install -q -r /opt/voxly/requirements.txt
chown -R voxly:voxly /opt/voxly
systemctl restart voxly
ok=0; for _ in $(seq 1 30); do if curl -sf 127.0.0.1:8000/api/health >/dev/null; then ok=1; break; fi; sleep 1; done
if [ "$ok" -ne 1 ]; then
  echo "APP HEALTH FAILED - rolling back the app"
  tar xzf /root/voxly-backup-$TS.tgz -C /opt/voxly && systemctl restart voxly
  journalctl -u voxly -n 30 --no-pager; exit 1
fi
echo "app OK"

# ---- nginx (this site only)
cp deploy/nginx-voxy-tls.conf /etc/nginx/sites-available/voxly
if nginx -t; then systemctl reload nginx; echo "nginx reloaded"; else
  echo "NGINX TEST FAILED - restoring the previous config"
  cp /root/nginx-voxly.bak-$TS /etc/nginx/sites-available/voxly && nginx -t && systemctl reload nginx; exit 1
fi

# ---- watchdog (restart after 2 failed health checks; set ALERT_URL in the unit for alerts)
cp deploy/voxly-watchdog.service deploy/voxly-watchdog.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now voxly-watchdog.timer
systemctl is-active voxly nginx voxly-watchdog.timer
echo "done. Rollback: tar xzf /root/voxly-backup-$TS.tgz -C /opt/voxly && cp /root/nginx-voxly.bak-$TS /etc/nginx/sites-available/voxly && systemctl restart voxly && systemctl reload nginx"
