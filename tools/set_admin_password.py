"""Set the /admin password (run on the server as the app user):
    cd /opt/voxly && sudo -u voxly .venv/bin/python /root/voxly-tts/tools/set_admin_password.py /opt/voxly/admin.json
Reads the password from stdin (or prompts), stores only its hash plus a new session
secret, so changing the password also signs out every browser."""
import getpass, json, os, secrets, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import hash_password  # noqa: E402

target = Path(sys.argv[1])
pw = sys.stdin.readline().strip() if not sys.stdin.isatty() else getpass.getpass("New admin password: ")
if len(pw) < 12:
    sys.exit("Use at least 12 characters.")
target.write_text(json.dumps({"password_hash": hash_password(pw), "secret": secrets.token_hex(32)}), encoding="utf-8")
os.chmod(target, 0o600)
print(f"saved {target}")
