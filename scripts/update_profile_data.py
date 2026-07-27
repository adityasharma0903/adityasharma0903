from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = REPO_ROOT / "assets" / "profile-data.svg"
LOGIN = os.environ.get("GITHUB_REPOSITORY_OWNER", "adityasharma0903")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def format_date(value: dt.date) -> str:
    return value.strftime("%b %d, %Y").replace(" 0", " ")


def graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is required to regenerate the profile snapshot")

    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "adityasharma0903-profile-snapshot",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)

    if body.get("errors"):
        raise SystemExit(json.dumps(body["errors"], indent=2))

    return body["data"]


def get_all_time_commits(login: str, token: str) -> int:
    request = urllib.request.Request(
        f"https://api.github.com/search/commits?q=author:{login}",
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "adityasharma0903-profile-snapshot",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.load(response)
        return int(body.get("total_count", 0))
    except Exception as e:
        print(f"Error fetching all-time commits: {e}", file=sys.stderr)
        return 0


def build_stats() -> tuple[int, int, int, str, str, str, str]:
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(days=365)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        createdAt
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    data = graphql(
        query,
        {
            "login": LOGIN,
            "from": start.isoformat(),
            "to": now.isoformat(),
        },
    )

    try:
        created_date_str = data["user"]["createdAt"]
        if created_date_str.endswith("Z"):
            created_date_str = created_date_str[:-1] + "+00:00"
        created_dt = dt.datetime.fromisoformat(created_date_str)
        from_date = format_date(created_dt.date())
    except Exception as e:
        print(f"Error parsing user createdAt date: {e}", file=sys.stderr)
        from_date = format_date(start.date())

    collection = data["user"]["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    weeks = calendar["weeks"]
    days: list[dict[str, object]] = [day for week in weeks for day in week["contributionDays"]]

    total = int(collection["totalCommitContributions"])
    all_time_commits = get_all_time_commits(LOGIN, TOKEN)
    if all_time_commits > 0:
        total = all_time_commits

    # Calculate current streak and its dates
    current_streak = 0
    streak_days = []
    for day in reversed(days):
        if int(day["contributionCount"]) > 0:
            current_streak += 1
            streak_days.append(day["date"])
        else:
            break

    if current_streak > 0:
        def format_streak_date(d_str: str) -> str:
            return dt.date.fromisoformat(d_str).strftime("%b %d").replace(" 0", " ")
        streak_dates = f"{format_streak_date(streak_days[-1])} - {format_streak_date(streak_days[0])}"
    else:
        streak_dates = "No active streak"

    # Calculate longest streak and its dates
    longest_streak = 0
    longest_start_idx = -1
    longest_end_idx = -1

    running = 0
    running_start_idx = -1

    for i, day in enumerate(days):
        if int(day["contributionCount"]) > 0:
            if running == 0:
                running_start_idx = i
            running += 1
            if running > longest_streak:
                longest_streak = running
                longest_start_idx = running_start_idx
                longest_end_idx = i
        else:
            running = 0

    if longest_streak > 0:
        longest_streak_dates = f"{format_date(dt.date.fromisoformat(days[longest_start_idx]['date']))} - {format_date(dt.date.fromisoformat(days[longest_end_idx]['date']))}"
    else:
        longest_streak_dates = "No streak recorded"

    return total, current_streak, longest_streak, format_date(start.date()), format_date(now.date()), streak_dates, longest_streak_dates


def build_svg(total: int, current_streak: int, longest_streak: int, from_date: str, to_date: str, streak_dates: str, longest_streak_dates: str) -> str:
    commit_bar_width = min(376, max(36, int((total / 1000) * 376))) if total > 0 else 36
    commit_bar_min = max(36, commit_bar_width - 30)
    commit_bar_max = min(376, commit_bar_width + 30)

    streak_dash = max(50, min(220, 100 + (current_streak * 15)))
    streak_offset = max(31, 251 - streak_dash)

    longest_bar_width = min(376, max(36, int((longest_streak / 30) * 376))) if longest_streak > 0 else 36

    return f"""<svg width="1600" height="420" viewBox="0 0 1600 420" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub profile snapshot">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1600" y2="420" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0B1220"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <linearGradient id="accent" x1="120" y1="60" x2="1480" y2="360" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="50%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#22D3EE"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="16"/>
    </filter>
  </defs>

  <rect x="8" y="8" width="1584" height="404" rx="28" fill="url(#bg)" stroke="url(#accent)" stroke-opacity="0.5"/>
  <circle cx="138" cy="100" r="84" fill="#1D4ED8" fill-opacity="0.16" filter="url(#glow)"/>
  <circle cx="1468" cy="322" r="112" fill="#8B5CF6" fill-opacity="0.14" filter="url(#glow)"/>

  <text x="72" y="64" fill="#E2E8F0" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="30" font-weight="700">GitHub Snapshot</text>
  <text x="72" y="96" fill="#93C5FD" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="16" font-weight="500">Real profile numbers, shown as a local card so the preview never falls back to alt text.</text>

  <g transform="translate(72 136)">
    <rect width="448" height="204" rx="24" fill="#0F172A" fill-opacity="0.82" stroke="#334155"/>
    <text x="36" y="54" fill="#E2E8F0" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="34" font-weight="700">{total}</text>
    <text x="36" y="86" fill="#94A3B8" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="16">Commit Count</text>
    <rect x="36" y="120" width="376" height="12" rx="6" fill="#1E293B"/>
    <rect x="36" y="120" width="{commit_bar_width}" height="12" rx="6" fill="url(#accent)">
      <animate attributeName="width" values="{commit_bar_min};{commit_bar_max};{commit_bar_min}" dur="7s" repeatCount="indefinite"/>
    </rect>
    <text x="36" y="168" fill="#64748B" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14">{from_date} - {to_date}</text>
  </g>

  <g transform="translate(576 136)">
    <rect width="448" height="204" rx="24" fill="#0F172A" fill-opacity="0.82" stroke="#334155"/>
    <text x="36" y="54" fill="#E2E8F0" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="34" font-weight="700">{current_streak}</text>
    <text x="36" y="86" fill="#94A3B8" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="16">Current Streak</text>
    <circle cx="336" cy="70" r="40" fill="none" stroke="#60A5FA" stroke-width="7" stroke-dasharray="{streak_dash} {streak_offset}" stroke-linecap="round">
      <animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 336 70" to="360 336 70" dur="10s" repeatCount="indefinite"/>
    </circle>
    <text x="36" y="168" fill="#64748B" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14">{streak_dates}</text>
  </g>

  <g transform="translate(1080 136)">
    <rect width="448" height="204" rx="24" fill="#0F172A" fill-opacity="0.82" stroke="#334155"/>
    <text x="36" y="54" fill="#E2E8F0" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="34" font-weight="700">{longest_streak}</text>
    <text x="36" y="86" fill="#94A3B8" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="16">Longest Streak</text>
    <rect x="36" y="120" width="376" height="12" rx="6" fill="#1E293B"/>
    <rect x="36" y="120" width="{longest_bar_width}" height="12" rx="6" fill="#A78BFA"/>
    <text x="36" y="168" fill="#64748B" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14">{longest_streak_dates}</text>
  </g>
</svg>
"""


def main() -> None:
    total, current_streak, longest_streak, from_date, to_date, streak_dates, longest_streak_dates = build_stats()
    OUTPUT_FILE.write_text(build_svg(total, current_streak, longest_streak, from_date, to_date, streak_dates, longest_streak_dates), encoding="utf-8")
    print(f"Updated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()