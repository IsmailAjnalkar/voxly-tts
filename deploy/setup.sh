#!/usr/bin/env bash
# Text 2 Speech VPS setup (Ubuntu/Debian). Run as root on the VPS from the project dir.
set -euo pipefail
apt-get update
apt-get install -y python3 python3-venv ffmpeg nginx
id voxly >/dev/null 2>&1 || useradd --system --home /opt/voxly --shell /usr/sbin/nologin voxly
mkdir -p /opt/voxly
cp -r server.py web requirements.txt /opt/voxly/
python3 -m venv /opt/voxly/.venv
/opt/voxly/.venv/bin/pip install -q -r /opt/voxly/requirements.txt
chown -R voxly:voxly /opt/voxly
cp deploy/voxly.service /etc/systemd/system/voxly.service
systemctl daemon-reload && systemctl enable --now voxly
cp deploy/nginx-voxy.conf /etc/nginx/sites-available/voxly
ln -sf /etc/nginx/sites-available/voxly /etc/nginx/sites-enabled/voxly
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "Text 2 Speech up: http://<server-ip>/  (app on 127.0.0.1:8000 behind nginx)"
