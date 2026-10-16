#!/usr/bin/env python3
"""Wire Voxly's 6 sub-pages into the language system: data-i18n attributes,
header language switcher, translated alerts, runtime script tags.
Every replacement is count-asserted; any mismatch is reported, not forced."""
import re
import pathlib
import sys

W = pathlib.Path(__file__).resolve().parent.parent / "web"
fails = []


def rep(page, old, new, count=1):
    p = W / page
    t = p.read_text()
    n = t.count(old)
    if n != count:
        fails.append(f"{page}: expected {count}x {old[:70]!r}, found {n}")
        return
    p.write_text(t.replace(old, new))


def tag(page, needle, attr, tags="p|h1|h2|h3|label|option|button|span|a"):
    """Add attr to the unique element whose text starts with needle."""
    p = W / page
    t = p.read_text()
    pat = re.compile(r"<(" + tags + r")([^>]*)>(" + re.escape(needle) + r")")
    hits = pat.findall(t)
    if len(hits) != 1:
        fails.append(f"{page}: needle {needle[:50]!r} hits={len(hits)}")
        return
    t2 = pat.sub(lambda m: f"<{m.group(1)}{m.group(2)} {attr}>{m.group(3)}", t, count=1)
    p.write_text(t2)


SELECT = ('<select id="sublang" aria-label="Language" '
          'style="margin-left:14px;background:transparent;color:inherit;'
          'border:1px solid rgba(140,150,170,.45);border-radius:8px;'
          'padding:4px 6px;font:inherit;font-size:13px"></select>')
SCRIPTS = '<script src="/i18n-sub.js"></script><script src="/subi18n.js"></script></body>'

PAGES = ["tutorial.html", "donate.html", "support.html", "auth.html",
         "privacy.html", "terms.html"]

for page in PAGES:
    rep(page,
        '<nav><a href="/">Home</a><a href="/tutorial.html">Tutorial</a>'
        '<a href="/donate.html">Donate</a><a href="/support.html">Support</a></nav>',
        '<nav><a href="/" data-i18n="nav_home">Home</a>'
        '<a href="/tutorial.html" data-i18n="nav_tutorial">Tutorial</a>'
        '<a href="/donate.html" data-i18n="nav_donate">Donate</a>'
        '<a href="/support.html" data-i18n="nav_support">Support</a></nav>' + SELECT)
    rep(page, '<a href="/privacy.html">Privacy Policy</a>',
        '<a href="/privacy.html" data-i18n="foot_privacy">Privacy Policy</a>')
    rep(page, '<a href="/terms.html">Terms of Service</a>',
        '<a href="/terms.html" data-i18n="foot_terms">Terms of Service</a>')
    rep(page, '</body>', SCRIPTS)

# ---- tutorial ----
tag("tutorial.html", "Tutorial", 'data-i18n="tut_h1"', tags="h1")
tag("tutorial.html", "Short, practical guides", 'data-i18n="tut_sub"')
tag("tutorial.html", "Getting started: your first generated voice", 'data-i18n="tut_g1h"', tags="h2")
tag("tutorial.html", "Start with the language selector", 'data-i18n="tut_g1p"')
tag("tutorial.html", "How to use the break feature", 'data-i18n="tut_g2h"', tags="h2")
tag("tutorial.html", "Break markers insert exact silence", 'data-i18n-html="tut_g2p"')
tag("tutorial.html", "A tour of the voice collection", 'data-i18n="tut_g3h"', tags="h2")
tag("tutorial.html", "Voxly's catalog holds 300+ neural voices", 'data-i18n="tut_g3p"')

# ---- donate ----
tag("donate.html", "Donate", 'data-i18n="don_h1"', tags="h1")
tag("donate.html", "Voxly is free for everyone.", 'data-i18n="don_sub"')
tag("donate.html", "Where donations go", 'data-i18n="don_where_h"', tags="h2")
tag("donate.html", "Server costs · Feature development · Service maintenance", 'data-i18n="don_where_p"')
tag("donate.html", "Amount", 'data-i18n="don_amount"', tags="label")
tag("donate.html", "PayPal (USD)", 'data-i18n="don_paypal"', tags="h3")
tag("donate.html", "WeChat Pay (CNY)", 'data-i18n="don_wechat"', tags="h3")
tag("donate.html", "Alipay", 'data-i18n="don_alipay"', tags="h3")
tag("donate.html", "Cryptocurrency", 'data-i18n="don_crypto"', tags="h3")
tag("donate.html", "USDT · ETH · BTC and more", 'data-i18n="don_crypto_sub"')
rep("donate.html",
    "<button onclick=\"alert('Donation checkout opens with the public launch. Thank you for offering!')\">Donate Now</button>",
    "<button onclick=\"subAlert('don_alert')\" data-i18n=\"don_btn\">Donate Now</button>",
    count=4)

# ---- support ----
tag("support.html", "Support", 'data-i18n="sup_h1"', tags="h1")
tag("support.html", "Most answers live in the FAQ", 'data-i18n="sup_sub"')
tag("support.html", "Quick fixes", 'data-i18n="sup_quick_h"', tags="h2")
tag("support.html", "• No sound on Preview:", 'data-i18n-html="sup_quick_p"')
tag("support.html", "Contact", 'data-i18n="sup_contact_h"', tags="h2")
tag("support.html", "Your email", 'data-i18n="sup_email"', tags="label")
tag("support.html", "Topic", 'data-i18n="sup_topic"', tags="label")
tag("support.html", "Generation problem", 'data-i18n="sup_o1"', tags="option")
tag("support.html", "Voice request", 'data-i18n="sup_o2"', tags="option")
tag("support.html", "Bug report", 'data-i18n="sup_o3"', tags="option")
tag("support.html", "Business / licensing", 'data-i18n="sup_o4"', tags="option")
tag("support.html", "Other", 'data-i18n="sup_o5"', tags="option")
tag("support.html", "Message", 'data-i18n="sup_msg"', tags="label")
rep("support.html",
    'placeholder="Describe what happened, which voice you used, and what you expected..."',
    'data-i18n-ph="sup_msg_ph" placeholder="Describe what happened, which voice you used, and what you expected..."')
rep("support.html",
    "<button onclick=\"alert('Thanks — the support inbox opens with the public launch. For now, the FAQ covers the common cases.')\">Send message</button>",
    "<button onclick=\"subAlert('sup_alert')\" data-i18n=\"sup_send\">Send message</button>")

# ---- auth ----
tag("auth.html", "Welcome back", 'data-i18n="auth_h1"', tags="h1")
tag("auth.html", "Accounts are optional", 'data-i18n="auth_sub"')
tag("auth.html", "Email", 'data-i18n="auth_email"', tags="label")
tag("auth.html", "Password", 'data-i18n="auth_pass"', tags="label")
rep("auth.html",
    "<button style=\"width:100%\" onclick=\"alert('Accounts arrive with the public launch. Everything on Voxly already works signed-out.')\">Sign in</button>",
    "<button style=\"width:100%\" onclick=\"subAlert('auth_alert_signin')\" data-i18n=\"auth_signin\">Sign in</button>")
rep("auth.html",
    "New here? <a href=\"#\" onclick=\"alert('Accounts arrive with the public launch. No sign-up is needed to convert text.');return false;\">Create an account</a> · <a href=\"#\" onclick=\"alert('Password reset arrives with accounts at public launch.');return false;\">Forgot password?</a>",
    "<span data-i18n=\"auth_newq\">New here?</span> <a href=\"#\" onclick=\"subAlert('auth_alert_create');return false;\" data-i18n=\"auth_create\">Create an account</a> · <a href=\"#\" onclick=\"subAlert('auth_alert_forgot');return false;\" data-i18n=\"auth_forgot\">Forgot password?</a>")

# ---- privacy ----
tag("privacy.html", "Privacy Policy", 'data-i18n="priv_h1"', tags="h1")
tag("privacy.html", "Last updated: October 2026", 'data-i18n="priv_updated"')
tag("privacy.html", "Voxly is designed to need as little", 'data-i18n="priv_intro"')
tag("privacy.html", "Text you convert", 'data-i18n="priv_s1h"', tags="h2")
tag("privacy.html", "Text you submit is sent to the speech engine", 'data-i18n="priv_s1p"')
tag("privacy.html", "Cookies and analytics", 'data-i18n="priv_s2h"', tags="h2")
tag("privacy.html", "If you accept the cookie banner", 'data-i18n="priv_s2p"')
tag("privacy.html", "What we never do", 'data-i18n="priv_s3h"', tags="h2")
tag("privacy.html", "We do not sell personal data", 'data-i18n="priv_s3p"')
tag("privacy.html", "Contact", 'data-i18n="priv_s4h"', tags="h2")
tag("privacy.html", "Questions about privacy:", 'data-i18n-html="priv_s4p"')

# ---- terms ----
tag("terms.html", "Terms of Service", 'data-i18n="terms_h1"', tags="h1")
tag("terms.html", "Last updated: October 2026", 'data-i18n="terms_updated"')
tag("terms.html", "The service", 'data-i18n="terms_s1h"', tags="h2")
tag("terms.html", "Voxly converts text you provide", 'data-i18n="terms_s1p"')
tag("terms.html", "Your responsibilities", 'data-i18n="terms_s2h"', tags="h2")
tag("terms.html", "Only convert text you have the right to use", 'data-i18n="terms_s2p"')
tag("terms.html", "Acceptable use", 'data-i18n="terms_s3h"', tags="h2")
tag("terms.html", "Personal, educational and creative use is welcome", 'data-i18n="terms_s3p"')
tag("terms.html", "Changes", 'data-i18n="terms_s4h"', tags="h2")
tag("terms.html", "Features and these terms may evolve", 'data-i18n="terms_s4p"')

if fails:
    print("FAILURES:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("wiring complete, all replacements matched")
