from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USERNAME = os.environ.get("STATS_USERNAME", "keyaruga33")
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "assets" / "section" / "stats.svg"

GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"
UA = "keyaruga33-stats-bot"


def _request(url: str, *, data: bytes | None = None, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _graphql(query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {
        "Authorization": f"bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": UA,
    }
    result = _request(GRAPHQL_URL, data=payload, headers=headers)
    if "errors" in result:
        raise RuntimeError(result["errors"])
    return result["data"]


def _rest(path: str) -> dict:
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"bearer {TOKEN}"
    return _request(f"{REST_URL}{path}", headers=headers)


def collect_graphql() -> dict:
    stars = forks = 0
    repos_owned = 0
    created_at = None
    followers = following = 0
    after = None

    repo_query = """
    query($login:String!, $after:String) {
      user(login:$login) {
        createdAt
        followers { totalCount }
        following { totalCount }
        repositories(first:100, ownerAffiliations:OWNER, isFork:false, after:$after) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { stargazerCount forkCount }
        }
      }
    }
    """
    while True:
        data = _graphql(repo_query, {"login": USERNAME, "after": after})["user"]
        created_at = data["createdAt"]
        followers = data["followers"]["totalCount"]
        following = data["following"]["totalCount"]
        repos = data["repositories"]
        repos_owned = repos["totalCount"]
        for node in repos["nodes"]:
            stars += node["stargazerCount"]
            forks += node["forkCount"]
        if repos["pageInfo"]["hasNextPage"]:
            after = repos["pageInfo"]["endCursor"]
        else:
            break

    total_commits = _lifetime_commits(created_at)

    return {
        "created_at": created_at,
        "followers": followers,
        "following": following,
        "repos": repos_owned,
        "stars": stars,
        "forks": forks,
        "commits": total_commits,
    }


def _lifetime_commits(created_at: str) -> int | None:
    try:
        start_year = int(created_at[:4])
    except (TypeError, ValueError):
        return None
    now_year = datetime.now(timezone.utc).year
    query = """
    query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        contributionsCollection(from:$from, to:$to) {
          totalCommitContributions
          restrictedContributionCount
        }
      }
    }
    """
    total = 0
    for year in range(start_year, now_year + 1):
        variables = {
            "login": USERNAME,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        }
        c = _graphql(query, variables)["user"]["contributionsCollection"]
        total += c["totalCommitContributions"] + c["restrictedContributionCount"]
    return total


def collect_rest() -> dict:
    user = _rest(f"/users/{USERNAME}")
    stars = forks = 0
    page = 1
    while True:
        repos = _rest(f"/users/{USERNAME}/repos?per_page=100&page={page}&type=owner")
        if not repos:
            break
        for r in repos:
            if r.get("fork"):
                continue
            stars += r.get("stargazers_count", 0)
            forks += r.get("forks_count", 0)
        if len(repos) < 100:
            break
        page += 1
    return {
        "created_at": user.get("created_at"),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "repos": user.get("public_repos", 0),
        "stars": stars,
        "forks": forks,
        "commits": None,
    }


def account_age(created_at: str | None) -> str:
    if not created_at:
        return "—"
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    delta = datetime.now(timezone.utc) - created
    years = delta.days // 365
    days = delta.days - years * 365
    if years <= 0:
        return f"{days} days"
    return f"{years}y {days}d"


def fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def collect() -> dict:
    if TOKEN:
        try:
            return collect_graphql()
        except Exception as exc:  # noqa: BLE001 - fall back gracefully
            print(f"[warn] GraphQL failed ({exc}); falling back to REST.")
    return collect_rest()


WIDTH = 900
HEIGHT = 300
COL_X = (48, 486)
ROW_Y = (112, 190, 268)


def render_svg(stats: dict) -> str:
    cells = [
        ("ACCOUNT AGE", account_age(stats.get("created_at"))),
        ("TOTAL STARS", fmt(stats.get("stars"))),
        ("REPOSITORIES", fmt(stats.get("repos"))),
        ("TOTAL COMMITS", fmt(stats.get("commits"))),
        ("FOLLOWERS", fmt(stats.get("followers"))),
        ("TOTAL FORKS", fmt(stats.get("forks"))),
    ]

    cell_svg = []
    for i, (label, value) in enumerate(cells):
        x = COL_X[i // 3]
        y = ROW_Y[i % 3]
        delay = i * 0.12
        cell_svg.append(f"""
      <g transform="translate({x},{y})" class="cell" style="animation-delay:{delay:.2f}s">
        <rect x="-16" y="-40" width="4" height="58" rx="2" fill="url(#statGrad)"/>
        <text class="lbl" x="0" y="-22">{label}</text>
        <text class="val" x="0" y="10">{value}</text>
      </g>""")

    synced = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<svg width="100%" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="statGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00D9CB"/>
      <stop offset="60%" stop-color="#109EE6"/>
      <stop offset="100%" stop-color="#BD49FF"/>
    </linearGradient>
    <filter id="statGlow" x="-30%" y="-60%" width="160%" height="220%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="stClip"><rect width="{WIDTH}" height="{HEIGHT}" rx="14"/></clipPath>
  </defs>

  <style>
    text {{ font:500 15px 'Consolas','Fira Code',monospace; fill:#DCF0FF; }}
    .lbl {{ fill:#A0B4CC; font-size:13px; letter-spacing:2px; }}
    .val {{ font-size:30px; font-weight:700; fill:url(#statGrad); filter:url(#statGlow); }}
    .head {{ animation:headBlink 2.4s ease-in-out infinite; }}
    @keyframes headBlink {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.4;}} }}
    .flick {{ animation:fBorder 6s steps(24) infinite; }}
    @keyframes fBorder {{ 0%,100%{{opacity:0.8;}} 40%{{opacity:0.3;}} 42%{{opacity:0.8;}} }}
    .cell {{ animation:cellIn 0.6s ease-out both; }}
    @keyframes cellIn {{ 0%{{opacity:0;transform:translateY(8px);}} 100%{{opacity:1;}} }}
  </style>

  <g clip-path="url(#stClip)">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="#0E1424"/>
    <rect width="{WIDTH}" height="34" fill="#080D19"/>
    <circle class="head" cx="20" cy="17" r="5" fill="#00D9CB"/>
    <text x="34" y="22" class="lbl">system_stats.log</text>
    <text x="{WIDTH - 20}" y="22" text-anchor="end" class="lbl">synced: {synced}</text>
    <line x1="0" y1="34" x2="{WIDTH}" y2="34" stroke="#1E3448"/>
{''.join(cell_svg)}
    <rect class="flick" x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}"
          rx="13" fill="none" stroke="#BD49FF" stroke-width="1.5"/>
  </g>
</svg>
"""


def main() -> None:
    try:
        stats = collect()
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
        print(f"[warn] stats collection failed ({exc}); emitting placeholder card.")
        stats = {}
    OUTPUT_FILE.write_text(render_svg(stats), encoding="utf-8")
    print(f"Generated: {OUTPUT_FILE}")
    for key in ("created_at", "stars", "repos", "commits", "followers", "forks"):
        print(f"  {key}: {stats.get(key)}")


if __name__ == "__main__":
    main()



