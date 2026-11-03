"""Generates stats.svg, langs.svg, streak.svg, contrib-graph.svg and trophies.svg from live GitHub data.

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

G = "#34D399"
DIM = "#6B9A87"
WHITE = "#C8E6D8"
FF = "Courier New, Courier, DejaVu Sans Mono, monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    createdAt
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 6, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      contributionYears
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


YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def gql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": "bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "profile-svg-generator"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_history(login, token, years):
    """Every contribution day since the account started: {date: count}."""
    days = {}
    for y in sorted(years):
        data = gql(YEAR_QUERY, {"login": login, "from": "%d-01-01T00:00:00Z" % y, "to": "%d-12-31T23:59:59Z" % y}, token)
        u = (data.get("data") or {}).get("user")
        if not u:
            continue
        for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    return days


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
        "createdAt": "2024-05-30T00:00:00Z",
        "repositories": {"totalCount": 9, "nodes": [
            {"stargazerCount": 3, "languages": {"edges": [
                {"size": 52000, "node": {"name": "JavaScript", "color": "#f1e05a"}},
                {"size": 31000, "node": {"name": "TypeScript", "color": "#3178c6"}},
                {"size": 9000, "node": {"name": "CSS", "color": "#563d7c"}}]}},
            {"stargazerCount": 1, "languages": {"edges": [
                {"size": 24000, "node": {"name": "Python", "color": "#3572A5"}},
                {"size": 12000, "node": {"name": "C++", "color": "#f34b7d"}},
                {"size": 4000, "node": {"name": "HTML", "color": "#e34c26"}}]}}]},
        "pullRequests": {"totalCount": 7},
        "issues": {"totalCount": 2},
        "contributionsCollection": {
            "contributionYears": [2026, 2025, 2024],
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
    s.append('<rect x="1" y="1" width="%d" height="%d" rx="12" fill="#04100c" stroke="%s" stroke-opacity="0.4"/>' % (W - 2, H - 2, G))
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
TIER = ["#1f4a3a", DIM, G, "#FBBF24", "#FB7185"]


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
    s.append('<rect x="1" y="1" width="%d" height="%d" rx="12" fill="#04100c" stroke="%s" stroke-opacity="0.4"/>' % (W - 2, H - 2, G))
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
        s.append('<rect x="%d" y="%d" width="%d" height="152" rx="10" fill="#081a14" stroke="%s" stroke-width="1.5" stroke-opacity="%s">%s</rect>'
                 % (x, top, cw, col, "0.9" if rank else "0.5",
                    '<animate attributeName="stroke-opacity" values="0.5;1;0.5" dur="2.4s" repeatCount="indefinite"/>' if rank >= 3 else ""))
        hx, hy, r = cxm, top + 40, 24
        hexpts = " ".join("%.1f,%.1f" % (hx + r * __import__("math").cos(__import__("math").radians(60 * k - 30)),
                                           hy + r * __import__("math").sin(__import__("math").radians(60 * k - 30))) for k in range(6))
        s.append('<polygon points="%s" fill="#0f2a20" stroke="%s" stroke-width="2"/>' % (hexpts, col))
        s.append('<text x="%.1f" y="%.1f" font-size="22" font-weight="bold" text-anchor="middle" fill="%s">%s</text>' % (hx, hy + 8, col, RANKS[rank]))
        s.append('<text x="%.1f" y="%d" font-size="28" font-weight="bold" text-anchor="middle" fill="#FFFFFF">%s</text>' % (cxm, top + 106, esc(short(val))))
        s.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">%s</text>' % (cxm, top + 130, DIM, esc(label)))
        s.append('</g>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- shared card chrome
def card_open(W, H, title, sub=None):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, FF)]
    s.append('<rect x="1" y="1" width="%d" height="%d" rx="12" fill="#04100c" stroke="%s" stroke-opacity="0.4"/>' % (W - 2, H - 2, G))
    s.append('<rect x="1" y="14" width="4" height="32" rx="2" fill="%s"/>' % G)
    s.append('<text x="24" y="36" font-size="17" font-weight="bold" fill="#FFFFFF">%s</text>' % esc(title))
    if sub:
        s.append('<text x="%d" y="36" font-size="12" text-anchor="end" fill="%s">%s</text>' % (W - 24, DIM, esc(sub)))
    return s


# ---------------------------------------------------------------- stats card
def stats_svg(user, history=None):
    cc = user["contributionsCollection"]
    repos = user["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    total = sum(history.values()) if history else cc["contributionCalendar"]["totalContributions"]
    rows = [
        ("TOTAL CONTRIBUTIONS", format(total, ",")),
        ("COMMITS (1Y)", format(cc["totalCommitContributions"], ",")),
        ("PULL REQUESTS", format(user["pullRequests"]["totalCount"], ",")),
        ("ISSUES", format(user["issues"]["totalCount"], ",")),
        ("STARS EARNED", format(stars, ",")),
        ("REPOSITORIES", format(repos["totalCount"], ",")),
    ]
    W, H = 392, 220
    s = card_open(W, H, "> git stats --live")
    for i, (label, val) in enumerate(rows):
        y = 74 + i * 26
        s.append('<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="%.2fs" dur="0.4s" fill="freeze"/>'
                 '<text x="24" y="%d" font-size="13" fill="%s">%s</text>'
                 '<text x="%d" y="%d" font-size="15" font-weight="bold" text-anchor="end" fill="%s">%s</text></g>'
                 % (0.15 * i, y, WHITE, label, W - 24, y, G, esc(val)))
        s.append('<line x1="24" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="0.12"/>' % (y + 8, W - 24, y + 8, G))
    s.append('</svg>')
    return "\n".join(s)


# ---------------------------------------------------------------- top languages
def langs_svg(user):
    totals = {}
    for r in user["repositories"]["nodes"]:
        for e in (r.get("languages") or {}).get("edges", []):
            n = e["node"]
            t = totals.setdefault(n["name"], [0, n.get("color") or G])
            t[0] += e["size"]
    top = sorted(totals.items(), key=lambda kv: -kv[1][0])[:6]
    whole = float(sum(v[0] for _, v in top)) or 1.0
    W, H = 392, 220
    s = card_open(W, H, "> ls ./languages")
    if not top:
        s.append('<text x="24" y="80" font-size="13" fill="%s">no language data yet</text></svg>' % DIM)
        return "\n".join(s)
    bx, bw = 24, W - 48
    s.append('<clipPath id="bar"><rect x="%d" y="56" width="%d" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">' % (bx, bw))
    x = float(bx)
    for name, (size, col) in top:
        w = bw * size / whole
        s.append('<rect x="%.1f" y="56" width="%.1f" height="10" fill="%s"/>' % (x, w, col))
        x += w
    s.append('</g>')
    for i, (name, (size, col)) in enumerate(top):
        cx = 24 + (i % 2) * 176
        cy = 96 + (i // 2) * 34
        s.append('<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="%.2fs" dur="0.4s" fill="freeze"/>'
                 '<circle cx="%d" cy="%d" r="5" fill="%s"/>'
                 '<text x="%d" y="%d" font-size="13" fill="%s">%s</text>'
                 '<text x="%d" y="%d" font-size="11" fill="%s">%.1f%%</text></g>'
                 % (0.15 * i, cx + 5, cy - 4, col, cx + 18, cy, WHITE, esc(name), cx + 18, cy + 15, DIM, 100 * size / whole))
    s.append('</svg>')
    return "\n".join(s)


# ---------------------------------------------------------------- streak
def streaks(days):
    import datetime
    if not days:
        return 0, 0, None, None, None, None
    ordered = sorted(days)
    today = datetime.date.today()
    best = cur = 0
    best_end = None
    run_start = None
    best_start = None
    prev = None
    for d in ordered:
        dt = datetime.date.fromisoformat(d)
        if dt > today:
            continue
        if days[d] > 0:
            if prev is not None and (dt - prev).days == 1 and cur > 0:
                cur += 1
            else:
                cur = 1
                run_start = dt
            if cur > best:
                best, best_start, best_end = cur, run_start, dt
            prev = dt
        else:
            # an empty *today* doesn't break a live streak
            if dt != today:
                cur = 0
            prev = dt if dt != today else prev
    live_end = None
    if cur:
        live_end = prev
    cs = run_start if cur else None
    return cur, best, cs, live_end, best_start, best_end


def fmt_d(d):
    return d.strftime("%b ") + str(d.day) if d else "-"


def streak_svg(user, history=None):
    import datetime
    if history is None:
        history = {}
        for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                history[d["date"]] = d["contributionCount"]
    cur, best, cs, ce, bs, be = streaks(history)
    total = sum(history.values())
    first = min(history) if history else None
    W, H = 800, 170
    s = card_open(W, H, "> ./streak --current", "since " + (first or "-"))
    cols = [
        (W * 0.17, "TOTAL CONTRIBUTIONS", format(total, ","), (first or "-") + " - present", 40, G),
        (W * 0.5, "CURRENT STREAK", str(cur), (fmt_d(cs) + " - " + fmt_d(ce)) if cur else "no active streak", 46, "#FBBF24"),
        (W * 0.83, "LONGEST STREAK", str(best), (fmt_d(bs) + " - " + fmt_d(be)) if best else "-", 40, G),
    ]
    for i, (cx, label, val, rng, fs, col) in enumerate(cols):
        s.append('<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="%.2fs" dur="0.5s" fill="freeze"/>'
                 '<text x="%.1f" y="104" font-size="%d" font-weight="bold" text-anchor="middle" fill="%s">%s</text>'
                 '<text x="%.1f" y="128" font-size="12" text-anchor="middle" fill="%s">%s</text>'
                 '<text x="%.1f" y="148" font-size="11" text-anchor="middle" fill="%s">%s</text></g>'
                 % (0.2 * i, cx, fs, col, esc(val), cx, WHITE, label, cx, DIM, esc(rng)))
    for x in (W * 0.34, W * 0.66):
        s.append('<line x1="%.1f" y1="64" x2="%.1f" y2="152" stroke="%s" stroke-opacity="0.25"/>' % (x, x, G))
    s.append('<circle cx="%.1f" cy="97" r="40" fill="none" stroke="#FBBF24" stroke-opacity="0.35" stroke-width="3">'
             '<animate attributeName="stroke-opacity" values="0.15;0.6;0.15" dur="2.4s" repeatCount="indefinite"/></circle>' % (W * 0.5))
    s.append('</svg>')
    return "\n".join(s)


# ---------------------------------------------------------------- snake placeholder (real one comes from Platane/snk)
def snake_placeholder():
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="140" viewBox="0 0 800 140" font-family="%s">' % FF,
         '<rect x="1" y="1" width="798" height="138" rx="12" fill="#04100c" stroke="%s" stroke-opacity="0.4"/>' % G,
         '<text x="400" y="76" font-size="14" text-anchor="middle" fill="%s">snake is warming up... run the workflow once</text>' % DIM,
         '</svg>']
    return "\n".join(s)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else "dist"
    os.makedirs(out, exist_ok=True)
    history = None
    if "--demo" in sys.argv:
        user = demo_user()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        login = os.environ.get("LOGIN")
        if not token or not login:
            raise SystemExit("Set GITHUB_TOKEN and LOGIN (or pass --demo)")
        user = fetch(login, token)
        try:
            history = fetch_history(login, token, user["contributionsCollection"]["contributionYears"])
        except Exception as e:  # fall back to the 1-year calendar
            print("history fetch failed, using last year only:", e)
    files = {
        "contrib-graph.svg": contrib_svg(user),
        "trophies.svg": trophies_svg(user),
        "stats.svg": stats_svg(user, history),
        "langs.svg": langs_svg(user),
        "streak.svg": streak_svg(user, history),
    }
    if "--demo" in sys.argv:
        files["snake-dark.svg"] = snake_placeholder()
    for name, content in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(content)
    print("written to", out)


if __name__ == "__main__":
    main()
