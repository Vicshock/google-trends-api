"""MCP server exposing Google Trends to AI assistants (Claude, ChatGPT, Cursor) through the hosted Apify Actor.

Run: APIFY_TOKEN=... uvx --from git+https://github.com/Vicshock/google-trends-api google-trends-mcp
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

from apify_client import ApifyClientAsync
from mcp.server.mcpserver import MCPServer

ACTOR = "victorrodi/google-trends-api"
SIGNUP = "https://console.apify.com/sign-up (free monthly credit), then copy your token from https://console.apify.com/account/integrations"
MAX_CHARGE_USD = Decimal(os.environ.get("GOOGLE_TRENDS_MAX_CHARGE_USD", "0.50"))  # hard cost cap per tool call
MAX_POINTS = 60  # keep timelines short enough for an LLM context
TIME_RANGES = ("now 1-H", "now 4-H", "now 1-d", "now 7-d", "today 1-m", "today 3-m", "today 12-m", "today 5-y", "all")

mcp = MCPServer(
    name="google-trends",
    instructions="Google Trends data: interest over time with growth %, related and rising queries, "
    "Trending Now with search volume, and ranking of any number of keywords on one 0-100 scale.",
    website_url="https://github.com/Vicshock/google-trends-api",
)


class TrendsError(RuntimeError):
    pass


def _check(terms: list[str], time_range: str, limit: int = 5) -> list[str]:
    clean = [t.strip() for t in terms if t and t.strip()]
    if not clean:
        raise TrendsError("Give at least one search term.")
    if len(clean) > limit:
        raise TrendsError(f"At most {limit} terms here; use google_trends_rank_keywords for more.")
    if time_range not in TIME_RANGES and not _is_custom_range(time_range):
        raise TrendsError(f"time_range must be one of {TIME_RANGES} or 'YYYY-MM-DD YYYY-MM-DD'.")
    return clean


def _is_custom_range(value: str) -> bool:
    parts = value.split()
    return len(parts) == 2 and all(len(p) == 10 and p[4] == "-" and p[7] == "-" for p in parts)


async def run_actor(run_input: dict[str, Any]) -> list[dict]:
    """Run the Actor and return its dataset items. Logs are not streamed: stdout belongs to the MCP protocol."""
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise TrendsError(f"APIFY_TOKEN is not set. Get one at {SIGNUP}.")
    client = ApifyClientAsync(token)
    run = await client.actor(ACTOR).call(run_input=run_input, logger=None, max_total_charge_usd=MAX_CHARGE_USD)
    if run is None or run.default_dataset_id is None:
        raise TrendsError("The Google Trends run did not finish.")
    page = await client.dataset(run.default_dataset_id).list_items(clean=True)
    return list(page.items)


def _trim(item: dict) -> dict:
    if len(item.get("timeline") or []) > MAX_POINTS:
        step = len(item["timeline"]) / MAX_POINTS
        item["timeline"] = [item["timeline"][int(i * step)] for i in range(MAX_POINTS)]
    return item


@mcp.tool()
async def google_trends_interest(terms: list[str], geo: str = "", time_range: str = "today 12-m") -> list[dict]:
    """Interest over time (0-100) for up to 5 terms on one scale, with average, peak, latest value and growth %.

    geo: country or region code such as US, GB, DE, US-CA ("" = worldwide).
    time_range: now 1-H, now 4-H, now 1-d, now 7-d, today 1-m, today 3-m, today 12-m, today 5-y, all, or 'YYYY-MM-DD YYYY-MM-DD'.
    """
    clean = _check(terms, time_range)
    items = await run_actor(
        {
            "searchTerms": [", ".join(clean)],
            "geo": geo.upper(),
            "timeRange": time_range,
            "dataTypes": ["interestOverTime"],
        }
    )
    return [_trim(i) for i in items]


@mcp.tool()
async def google_trends_related_queries(term: str, geo: str = "", time_range: str = "today 12-m") -> list[dict]:
    """Top and rising related searches for one term, including 'Breakout' queries (growth over 5000%)."""
    clean = _check([term], time_range, limit=1)
    return await run_actor(
        {"searchTerms": clean, "geo": geo.upper(), "timeRange": time_range, "dataTypes": ["relatedQueries"]}
    )


@mcp.tool()
async def google_trends_trending_now(geo: str = "US", hours: int = 24, max_items: int = 20) -> list[dict]:
    """What people search right now in a country: title, search volume, growth %, categories, related queries, news.

    hours: 4, 24, 48 or 168. max_items: 1-100, biggest search volume first.
    """
    if hours not in (4, 24, 48, 168):
        raise TrendsError("hours must be 4, 24, 48 or 168.")
    return await run_actor(
        {
            "trendingNowGeos": [geo.upper() or "US"],
            "trendingNowHours": str(hours),
            "trendingNowMaxItems": max(1, min(max_items, 100)),
        }
    )


@mcp.tool()
async def google_trends_rank_keywords(terms: list[str], geo: str = "", time_range: str = "today 12-m") -> dict:
    """Rank any number of keywords (2-100) on one common 0-100 scale, beyond Google's 5-term limit."""
    clean = _check(terms, time_range, limit=100)
    if len(clean) < 2:
        raise TrendsError("Give at least 2 terms to rank.")
    items = await run_actor(
        {
            "searchTerms": [", ".join(clean)],
            "keywordRanking": True,
            "geo": geo.upper(),
            "timeRange": time_range,
            "dataTypes": ["interestOverTime"],
        }
    )
    ranking = [i for i in items if i.get("type") == "keywordRanking"]
    if not ranking:
        raise TrendsError("Google returned no ranking for these terms.")
    return ranking[0]


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
