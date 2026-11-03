"""Generates contrib-graph.svg and trophies.svg from live GitHub data.

Usage:
    GITHUB_TOKEN=... LOGIN=Luvin-2511 python3 scripts/gen_stats.py dist
    python3 scripts/gen_stats.py dist --demo      # mock data, for local preview
"""
import html
import json
import os
import random
import sys
import urllib.request

G = "#A78BFA"
DIM = "#8B7BC0"
WHITE = "#C9C2E8"
FF = "Courier New, Courier, DejaVu Sans Mono, monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def esc(s):
    return html.escape(str(s), quote=False)


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": "bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "profile-svg-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    user = (data.get("data") or {}).get("user")
    if "errors" in data or not user:
        raise SystemExit("GitHub GraphQL error: " + json.dumps(data)[:600])
    return user


def demo_user():
    random.seed(3)
    weeks = []
    import datetime
    d = datetime.date(2025, 10, 12)
    for _ in range(53):
        days = []
        for _ in range(7):
            days.append({"date": d.isoformat(), "countc": 0, "contributionCount": random.choice([0, 0, 1, 2, 3, 5, 8])})
            d += datetime.timedelta(days=1)
        weeks.append({"contributionDays": days})
    return {
        "followers": {"totalCount": 12},
        "repositories": {"totalCount": 9, "nodes": [{"stargazerCount": 3}, {"stargazerCount": 1}]},
        "pullRequests": {"totalCount": 7},
        "issues": {"totalCount": 2},
        "contributionsCollection": {
            "totalCommitContributions": 420,
            "contributionCalendar": {"totalContributions": 640, "weeks": weeks},
        },
    }


# ---------------------------------------------------------------- contribution graph
def contrib_svg(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    vals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    dates = [w["contributionDays"][0]["date"] for w in weeks if w["contributionDays"]]
    n = len(vals)
    if n < 2:
        vals = vals + [0]
        dates = dates + dates[-1:]
        n = len(vals)
    total = cal["totalContributions"]
    peak = max(vals)
    maxv = max(peak, 1)

    W, H = 800, 290
    x0, x1, y0, y1 = 56, 770, 92, 232

    def px(i):
        return x0 + i * (x1 - x0) / float(n - 1)

    def py(v):
        return y1 - (v / float(maxv)) * (y1 - y0)

    pts = [(px(i), py(v)) for i, v in enumerate(vals)]
    line = "M" + " L".join("%.1f,%.1f" % p for p in pts)
    area = line + " L%.1f,%d L%.1f,%d Z" % (x1, y1, x0, y1)
    pk = vals.index(peak)

    s = []
    s.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FF))
    s.append('<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="%s" stop-opacity="0.38"/><stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient>'
             '<filter id="gl" x="-5%%" y="-30%%" width="110%%" height="160%%"><feGaussianBlur stdDeviation="3" result="b"/>'
             '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>' % (G, G))
    s.append('<rect x="1" y="1" width="%d" height="%d" rx="12" fill="#07040f" stroke="%s" stroke-opacity="0.4"/>' % (W - 2, H - 2, G))
    s.append('<rect x="1" y="14" width="4" height="40" rx="2" fill="%s"/>' % G)
    s.append('<text x="24" y="34" font-size="17" font-weight="bold" fill="#FFFFFF">&gt; git log --contributions --since=1y</text>')
    s.append('<text x="24" y="56" font-size="12" fill="%s">weekly commits, issues, PRs and reviews</text>' % DIM)
    s.append('<text x="776" y="34" font-size="22" font-weight="bold" text-anchor="end" fill="%s">%s</text>' % (G, format(total, ",")))
    s.append('<text x="776" y="54" font-size="12" text-anchor="end" fill="%s">TOTAL CONTRIBUTIONS</text>' % DIM)
    for frac in (0, 0.5, 1):
        y = y1 - frac * (y1 - y0)
        s.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-opacity="0.15" stroke-dasharray="3 5"/>' % (x0, y, x1, y, G))
        s.append('<text x="%d" y="%.1f" font-size="10" text-anchor="end" fill="%s">%d</text>' % (x0 - 8, y + 3, DIM, round(frac * maxv)))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last_m = None
    for i, dt in enumerate(dates[:n]):
        m = int(dt[5:7])
        if m != last_m:
            last_m = m
            if i < n - 1:
                s.append('<text x="%.1f" y="%d" font-size="11" fill="%s">%s</text>' % (px(i), y1 + 22, DIM, months[m - 1]))
    s.append('<path d="%s" fill="url(#ar)" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="1.2s" dur="1s" fill="freeze"/></path>' % area)
    s.append('<path d="%s" fill="none" stroke="%s" stroke-width="6" stroke-opacity="0.18" stroke-linejoin="round" pathLength="1" '
             'stroke-dasharray="1" stroke-dashoffset="1"><animate attributeName="stroke-dashoffset" from="1" to="0" dur="2.2s" fill="freeze"/></path>' % (line, G))
    s.append('<path d="%s" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round" pathLength="1" '
             'stroke-dasharray="1" stroke-dashoffset="1" filter="url(#gl)"><animate attributeName="stroke-dashoffset" from="1" to="0" dur="2.2s" fill="freeze"/></path>' % (line, G))
    s.append('<rect y="%d" width="2" height="%d" fill="%s" opacity="0.25"><animate attributeName="x" from="%d" to="%d" dur="5s" repeatCount="indefinite"/></rect>'
             % (y0 - 6, y1 - y0 + 6, G, x0, x1))
    cx, cy = pts[pk]
    s.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"><animate attributeName="r" values="3;7;3" dur="1.6s" repeatCount="indefinite"/>'
             '<animate attributeName="opacity" values="1;0.35;1" dur="1.6s" repeatCount="indefinite"/></circle>' % (cx, cy, G))
    tx = min(max(cx, x0 + 60), x1 - 60)
    s.append('<text x="%.1f" y="%.1f" font-size="11" text-anchor="middle" fill="#FFFFFF">peak week: %d</text>' % (tx, max(cy - 12, y0 - 14), peak))
    s.append('</svg>')
    return "\n".join(s)


# ---------------------------------------------------------------- trophies
RANKS = ["-", "C", "B", "A", "S"]
TIER = ["#3b2f5e", DIM, G, "#22D3EE", "#FFD166"]


def short(v):
    return "%.1fk" % (v / 1000.0) if v >= 1000 else str(v)


def trophies_svg(user):
    repos = user["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    items = [
        ("STARS", stars, [1, 10, 50, 200]),
        ("COMMITS 1Y", user["contributionsCollection"]["totalCommitContributions"], [1, 50, 300, 1000]),
        ("PULL REQUESTS", user["pullRequests"]["totalCount"], [1, 5, 25, 100]),
        ("ISSUES", user["issues"]["totalCount"], [1, 5, 25, 100]),
        ("REPOS", repos["totalCount"], [1, 5, 15, 30]),
        ("FOLLOWERS", user["followers"]["totalCount"], [1, 10, 50, 200]),
    ]
    W, H = 800, 232
    cw, gap, left, top = 118, 12, 16, 62
    unlocked = sum(1 for _, v, th in items if v >= th[0])
    s = []
    s.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FF))
    s.append('<rect x="1" y="1" width="%d" height="%d" rx="12" fill="#07040f" stroke="%s" stroke-opacity="0.4"/>' % (W - 2, H - 2, G))
    s.append('<rect x="1" y="14" width="4" height="32" rx="2" fill="%s"/>' % G)
    s.append('<text x="24" y="36" font-size="17" font-weight="bold" fill="#FFFFFF">&gt; ./trophies.sh --show-all</text>')
    s.append('<text x="776" y="36" font-size="13" text-anchor="end" fill="%s">UNLOCKED %d/%d'
             '<animate attributeName="opacity" values="1;0.4;1" dur="1.8s" repeatCount="indefinite"/></text>' % (G, unlocked, len(items)))
    for i, (label, val, th) in enumerate(items):
        rank = sum(1 for t in th if val >= t)
        col = TIER[rank]
        x = left + i * (cw + gap)
        cxm = x + cw / 2.0
        delay = 0.2 + i * 0.18
        s.append('<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="%.2fs" dur="0.5s" fill="freeze"/>'
                 '<animateTransform attributeName="transform" type="translate" from="0 14" to="0 0" begin="%.2fs" dur="0.5s" fill="freeze"/>' % (delay, delay))
        s.append('<rect x="%d" y="%d" width="%d" height="152" rx="10" fill="#0d0820" stroke="%s" stroke-width="1.5" stroke-opacity="%s">%s</rect>'
                 % (x, top, cw, col, "0.9" if rank else "0.5",
                    '<animate attributeName="stroke-opacity" values="0.5;1;0.5" dur="2.4s" repeatCount="indefinite"/>' if rank >= 3 else ""))
        hx, hy, r = cxm, top + 40, 24
        hexpts = " ".join("%.1f,%.1f" % (hx + r * __import__("math").cos(__import__("math").radians(60 * k - 30)),
                                           hy + r * __import__("math").sin(__import__("math").radians(60 * k - 30))) for k in range(6))
        s.append('<polygon points="%s" fill="#150f2e" stroke="%s" stroke-width="2"/>' % (hexpts, col))
        s.append('<text x="%.1f" y="%.1f" font-size="22" font-weight="bold" text-anchor="middle" fill="%s">%s</text>' % (hx, hy + 8, col, RANKS[rank]))
        s.append('<text x="%.1f" y="%d" font-size="28" font-weight="bold" text-anchor="middle" fill="#FFFFFF">%s</text>' % (cxm, top + 106, esc(short(val))))
        s.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">%s</text>' % (cxm, top + 130, DIM, esc(label)))
        s.append('</g>')
    s.append('</svg>')
    return "\n".join(s)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else "dist"
    os.makedirs(out, exist_ok=True)
    if "--demo" in sys.argv:
        user = demo_user()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        login = os.environ.get("LOGIN")
        if not token or not login:
            raise SystemExit("Set GITHUB_TOKEN and LOGIN (or pass --demo)")
        user = fetch(login, token)
    with open(os.path.join(out, "contrib-graph.svg"), "w", encoding="utf-8") as f:
        f.write(contrib_svg(user))
    with open(os.path.join(out, "trophies.svg"), "w", encoding="utf-8") as f:
        f.write(trophies_svg(user))
    print("written to", out)


if __name__ == "__main__":
    main()
