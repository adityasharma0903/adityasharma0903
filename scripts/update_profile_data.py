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


def build_stats() -> tuple[int, int, int, str, str]:
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(days=365)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
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

    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    days: list[dict[str, object]] = [day for week in weeks for day in week["contributionDays"]]

    total = int(calendar["totalContributions"])

    current_streak = 0
    for day in reversed(days):
        if int(day["contributionCount"]) > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for day in days:
        if int(day["contributionCount"]) > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    return total, current_streak, longest_streak, format_date(start.date()), format_date(now.date())


def build_svg(total: int, current_streak: int, longest_streak: int, from_date: str, to_date: str) -> str:
    ring_dash = max(92, min(160, 90 + (current_streak * 14)))
    ring_offset = max(0, 248 - (current_streak * 10))

    return f"""<svg width="1600" height="300" viewBox="0 0 1600 300" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub profile snapshot">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1600" y2="300" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0B1020"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1600" y2="300" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="50%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#22D3EE"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
  </defs>

  <rect x="10" y="10" width="1580" height="280" rx="18" fill="url(#bg)" stroke="#1F2A44"/>
  <rect x="10" y="10" width="1580" height="280" rx="18" fill="none" stroke="url(#accent)" stroke-opacity="0.18"/>

  <rect x="533" y="28" width="534" height="244" rx="10" fill="#0F172A" fill-opacity="0.75" stroke="#17213A"/>

  <line x1="533" y1="48" x2="533" y2="252" stroke="#24314F"/>
  <line x1="1067" y1="48" x2="1067" y2="252" stroke="#24314F"/>

  <g>
    <text x="667" y="112" text-anchor="middle" fill="#E2E8F0" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="32" font-weight="700">{total}</text>
    <text x="667" y="148" text-anchor="middle" fill="#93C5FD" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="15" font-weight="500">Total Contributions</text>
    <text x="667" y="188" text-anchor="middle" fill="#94A3B8" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13">{from_date} - {to_date}</text>
  </g>

  <g>
    <circle cx="800" cy="102" r="34" fill="none" stroke="#60A5FA" stroke-width="6" stroke-dasharray="{ring_dash} {ring_offset}" stroke-linecap="round" filter="url(#glow)">
      <animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 800 102" to="360 800 102" dur="10s" repeatCount="indefinite"/>
    </circle>
    <circle cx="800" cy="102" r="40" fill="none" stroke="#8B5CF6" stroke-opacity="0.25" stroke-width="2"/>
    <path d="M800 70V60" stroke="#8B5CF6" stroke-width="5" stroke-linecap="round"/>
    <text x="800" y="115" text-anchor="middle" fill="#E2E8F0" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="30" font-weight="700">{current_streak}</text>
    <text x="800" y="148" text-anchor="middle" fill="#93C5FD" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="15" font-weight="500">Current Streak</text>
    <text x="800" y="188" text-anchor="middle" fill="#94A3B8" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13">{to_date}</text>
  </g>

  <g>
    <text x="933" y="112" text-anchor="middle" fill="#E2E8F0" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="32" font-weight="700">{longest_streak}</text>
    <text x="933" y="148" text-anchor="middle" fill="#93C5FD" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="15" font-weight="500">Longest Streak</text>
    <text x="933" y="188" text-anchor="middle" fill="#94A3B8" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13">Best run in the last 365 days</text>
  </g>

  <rect x="42" y="42" width="1516" height="216" rx="14" fill="none" stroke="#1E293B" stroke-opacity="0.8"/>
</svg>
"""


def main() -> None:
    total, current_streak, longest_streak, from_date, to_date = build_stats()
    OUTPUT_FILE.write_text(build_svg(total, current_streak, longest_streak, from_date, to_date), encoding="utf-8")
    print(f"Updated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()