# Deployment checklist: `seo/sage-remediation`

Based on [`deploy/release.sh`](../../deploy/release.sh) and [`deploy/RUNBOOK-hostinger.md`](../../deploy/RUNBOOK-hostinger.md). The VPS runs nginx (TLS) → uvicorn on `127.0.0.1:8000`, with the app in `/opt/voxly` and the git checkout in `/root/voxly-tts`.
Local commands are run from the repo root; the Windows venv is `.venv/Scripts/python.exe`.

## 1. Pre-deploy gates (all must pass)

| # | Gate | Command / check | Pass when |
|---|---|---|---|
| G0 | **Donation links not reverted (X1)** | `git grep -nE "EXAMPLE-replace-me\|buymeacoffee.com/yourname" -- web` | **No output** (the owner confirmed the real links in O1), or the owner has signed off in writing that the placeholders may go live |
| G1 | Owner content review | About, Help and the 3 new guides (O3, O4); privacy wording if changed (O12) | Approved in writing |
| G2 | API + SEO unit tests | `python -m unittest tests/test_api.py -v` | All pass |
| G3 | SEO checks (no network) | `python tests/seo_checks.py --json docs/seo-remediation/evidence/seo_checks_pre.json` | Exit 0 |
| G4 | Dependency audit | `pip-audit -r requirements.txt` | No known vulnerabilities |
| G5 | Start the app locally (port 8805 only) | `VOXLY_VOICE_SWEEP=0 .venv/Scripts/python.exe -m uvicorn server:app --port 8805` | `/api/health` → `{"ok":true}` |
| G6 | UI-language test | `cd tests && npm ci && BASE=http://localhost:8805 npm test` | Pass |
| G7 | E2E suite | `cd tests/e2e && BASE=http://localhost:8805 BROWSER=chromium npm test` (repeat with firefox and webkit) | All pass, including the skip-link and voice-list keyboard tests (S2, G2) |
| G8 | Route map on the branch | `python docs/seo-remediation/evidence/route_map.py http://localhost:8805 docs/seo-remediation/evidence/route_map_local` | 0 anomalies (no orphan language pages: L1); new pages 200 and in the sitemap |
| G9 | Legacy crawl | `python audit/scripts/seo_crawl.py http://localhost:8805 docs/seo-remediation/evidence/seo_crawl_local.json` | 0 issues |
| G10 | Lighthouse (local, no gzip: Performance may read slightly low) | `node audit/scripts/lighthouse_run.mjs http://localhost:8805 docs/seo-remediation/evidence local` | A11y / BP / SEO 100; no regression vs Agent 4's baseline |
| G11 | CI green on the PR | GitHub Actions `ci` | Green |
| G12 | Stop the local server | kill the uvicorn on 8805 | Port free |

## 2. Deploy

1. Merge the PR into `master` (owner approval O5).
2. On the VPS, as root (hPanel browser terminal per the runbook):
   ```
   cd /root/voxly-tts && git pull --ff-only && git log --oneline -1
   bash deploy/release.sh
   ```
   `release.sh` does the following:
   - backs up `/opt/voxly/{server.py,web,requirements.txt}` to `/root/voxly-backup-<TS>.tgz` and nginx to `/root/nginx-voxly.bak-<TS>`
   - copies `server.py`, swaps `web/` as a whole, pip-installs, restarts `voxly`
   - waits up to 30 s for `/api/health`, and **rolls the app back automatically** if it fails
   - installs the nginx config (`nginx -t`, restore on failure) and the watchdog timer

   It does not touch `/opt/voxly/stats/` (page-view counts), `admin.json` or `data/`.
3. Write down the `<TS>` it prints. You need it for rollback.

## 3. Post-deploy verification (production)

| # | Check | Command | Expect |
|---|---|---|---|
| P1 | Health | `curl -s https://text-2-speech.com/api/health` | `{"ok":true,"app":"text-2-speech"}` |
| P2 | Uptime workflow (real generation) | `gh workflow run uptime.yml`, then `gh run list --workflow uptime.yml -L 1` | Success |
| P3 | Donation links | `curl -s https://text-2-speech.com/ \| grep -o 'href="https://[^"]*\(stripe\|coffee\)[^"]*"'` | The confirmed real links, not placeholders |
| P4 | Sitemap count | `curl -s https://text-2-speech.com/sitemap.xml \| grep -o '<loc>' \| wc -l` | 129 + the number of new indexable English pages (for example about, help, 3 guides → 134). Record the actual number |
| P5 | Route map | `python docs/seo-remediation/evidence/route_map.py https://text-2-speech.com docs/seo-remediation/evidence/route_map_prod_after` | 0 anomalies; every sitemap URL 200, self-canonical, 1 H1; language sub-pages have inbound links (L1); `/about.html` and `/help.html` 200 |
| P6 | No-JS content | `python docs/seo-remediation/evidence/ssr_check.py https://text-2-speech.com docs/seo-remediation/evidence/ssr_check_prod_after.json` | 11/11 OK |
| P7 | Legacy crawl | `python audit/scripts/seo_crawl.py https://text-2-speech.com docs/seo-remediation/evidence/seo_crawl_prod_after.json` | 0 issues |
| P8 | Lighthouse, production (gzip + HTTP/2) | `RUNS=3 EXTRA_PATHS=/about.html,/help.html node audit/scripts/lighthouse_run.mjs https://text-2-speech.com docs/seo-remediation/evidence prod_after` | A11y / BP / SEO 100; Performance within the variance seen in the baseline (mobile language homes 95–100) |
| P9 | Rich Results + schema validator | `/`, `/es/`, `/about.html`, `/how-it-works.html`, one guide (O18) | No errors; results saved |
| P10 | E2E against production (no synthesis, to respect rate limits) | `cd tests/e2e && BASE=https://text-2-speech.com NO_GENERATE=1 npm test` | Pass |
| P11 | robots / llms | `curl -s https://text-2-speech.com/robots.txt`, `curl -s https://text-2-speech.com/llms.txt` | robots unchanged (no policy change in this PR); llms.txt lists the new pages |
| P12 | Search engines | Sitemap resubmit + URL Inspection in GSC and Bing (O16, O17) | Submitted |
| P13 | SAGE rerun | Owner (O15) | After scores recorded |

## 4. Rollback

The app rolls itself back if the health check fails during `release.sh`. For a manual rollback after a bad deploy, use the `<TS>` from step 2. **Delete `web/` first**: extracting the backup over it would leave new files such as `/about.html` and `/guides/*.html` in place, and the old app's static mount would still serve them.

```
systemctl stop voxly
rm -rf /opt/voxly/web
tar xzf /root/voxly-backup-<TS>.tgz -C /opt/voxly
cp /root/nginx-voxly.bak-<TS> /etc/nginx/sites-available/voxly && nginx -t
chown -R voxly:voxly /opt/voxly
systemctl start voxly && systemctl reload nginx
curl -s https://text-2-speech.com/api/health
```

Then revert the merge on `master` (`git revert -m 1 <merge-sha>`), so the repo matches production again and the next `release.sh` does not redeploy the bad version. If pages were already submitted, there is nothing to undo in GSC: removed URLs drop out as 404s.
