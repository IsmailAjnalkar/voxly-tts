# Voxly → Hostinger VPS runbook (prepared 2026-10-18)

Why this route: the Muse sandbox's outbound traffic is HTTP(S)-proxy-only — SSH
(key exchange) gets reset by the proxy, and proxy CONNECT to :22 returns nothing.
So the deploy is driven through the hPanel **browser SSH terminal** in Ismail's
signed-in Hostinger session. No secrets are typed anywhere: the VPS generates its
own GitHub deploy key (read-only) and only the public half leaves the server.

Target: VPS 177.7.52.202 (root), domain text-2-speech.com (his, Hostinger DNS).

## Step 1 — in the VPS browser terminal (root)
```
ssh-keygen -t ed25519 -f /root/.ssh/github_deploy -N "" -C "voxly-vps"
printf 'Host github.com\n  IdentityFile /root/.ssh/github_deploy\n  StrictHostKeyChecking accept-new\n' > /root/.ssh/config
cat /root/.ssh/github_deploy.pub
```
Read back the public key line.

## Step 2 — GitHub (his session)
Repo IsmailAjnalkar/voxly-tts → Settings → Deploy keys → Add deploy key →
title "voxly-vps", paste the public key, **leave "Allow write access" unchecked**.

## Step 3 — back in the VPS terminal
```
apt-get update -qq && apt-get install -y -qq git > /dev/null
git clone git@github.com:IsmailAjnalkar/voxly-tts.git /root/voxly-tts
cd /root/voxly-tts && git log --oneline -1   # expect 832c1be or newer master
bash deploy/setup.sh
```
setup.sh installs python3+venv+ffmpeg+nginx, copies server.py/web/requirements
to /opt/voxly, creates the voxly service (127.0.0.1:8000), enables nginx.
server.py creates its own data/ dir under /opt/voxly at runtime (voxly-owned ✓).

## Step 4 — nginx for the real domain + HTTPS
Only AFTER the DNS A record (step 5) resolves to 177.7.52.202:
```
sed -i 's/server_name _;/server_name text-2-speech.com www.text-2-speech.com;/' /etc/nginx/sites-available/voxly
nginx -t && systemctl reload nginx
apt-get install -y -qq certbot python3-certbot-nginx > /dev/null
certbot --nginx -d text-2-speech.com -d www.text-2-speech.com --non-interactive --agree-tos --register-unsafely-without-email --redirect
```

## Step 5 — DNS at Hostinger (hPanel → text-2-speech.com → DNS)
- A record: name `@`, value `177.7.52.202` (replace the parked-page record if any)
- A record: name `www`, value `177.7.52.202`
Order note: set DNS first, wait for resolution (check from sandbox:
`getent hosts text-2-speech.com`), then run step 4's certbot.
Sequence safely: do Step 5 right after Step 3, verify resolution, then Step 4.

## Step 6 — verify (from the Muse sandbox, HTTPS)
- `curl https://text-2-speech.com/api/health` → 200
- Homepage loads (Voxly UI, not the Hostinger parked page)
- Real generation: POST a short TTS request via the site's API and confirm audio
  returns (use the same call the web UI makes; check server.py routes).
- Confirm voxly.chatbotreply.com (Render) still up as fallback.

## Updates later
On the VPS: `cd /root/voxly-tts && git pull && cp server.py + web to /opt/voxly
&& systemctl restart voxly` (mirror what setup.sh does), or re-run setup.sh.

## Notes
- Adding Muse's own sandbox key in hPanel became moot (no SSH egress from the
  sandbox); harmless if added.
- Render: if the parallel task added text-2-speech.com as a Render custom
  domain, it's inert while DNS points at the VPS; can be removed later.
