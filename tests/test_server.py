import pytest

from google_trends_mcp import server


class FakeActor(list):
    """Records each run input; returns `items` as the dataset."""

    def __init__(self):
        super().__init__()
        self.items: list[dict] = []


@pytest.fixture
def fake_actor(monkeypatch):
    calls = FakeActor()

    async def run(run_input):
        calls.append(run_input)
        return calls.items

    monkeypatch.setattr(server, "run_actor", run)
    return calls


async def test_interest_builds_one_compared_query_and_trims_timeline(fake_actor):
    fake_actor.items = [{"type": "interestOverTime", "timeline": [{"v": i} for i in range(260)]}]
    result = await server.google_trends_interest(["iphone", " samsung ", ""], geo="us")
    assert fake_actor == [
        {"searchTerms": ["iphone, samsung"], "geo": "US", "timeRange": "today 12-m", "dataTypes": ["interestOverTime"]}
    ]
    assert len(result[0]["timeline"]) == server.MAX_POINTS


@pytest.mark.parametrize(
    ("terms", "time_range", "message"),
    [
        ([], "today 12-m", "at least one"),
        (list("abcdef"), "today 12-m", "At most 5"),
        (["x"], "last year", "time_range"),
    ],
)
async def test_interest_rejects_bad_input(fake_actor, terms, time_range, message):
    with pytest.raises(server.TrendsError, match=message):
        await server.google_trends_interest(terms, time_range=time_range)
    assert fake_actor == []


async def test_custom_range_and_related_queries(fake_actor):
    await server.google_trends_related_queries("air fryer", time_range="2024-01-01 2024-06-30")
    assert fake_actor[0]["dataTypes"] == ["relatedQueries"] and fake_actor[0]["timeRange"] == "2024-01-01 2024-06-30"


async def test_trending_now_clamps_and_validates(fake_actor):
    await server.google_trends_trending_now("gb", hours=4, max_items=500)
    assert fake_actor[0] == {"trendingNowGeos": ["GB"], "trendingNowHours": "4", "trendingNowMaxItems": 100}
    with pytest.raises(server.TrendsError, match="hours"):
        await server.google_trends_trending_now(hours=12)


async def test_rank_keywords_returns_ranking_item(fake_actor):
    fake_actor.items = [{"type": "interestOverTime"}, {"type": "keywordRanking", "ranking": [{"term": "a"}]}]
    result = await server.google_trends_rank_keywords(["a", "b", "c", "d", "e", "f"])
    assert result["ranking"] == [{"term": "a"}] and fake_actor[0]["keywordRanking"] is True
    fake_actor.items = []
    with pytest.raises(server.TrendsError, match="no ranking"):
        await server.google_trends_rank_keywords(["a", "b"])
    with pytest.raises(server.TrendsError, match="at least 2"):
        await server.google_trends_rank_keywords(["a"])


async def test_missing_token_explains_how_to_get_one(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(server.TrendsError, match="APIFY_TOKEN is not set"):
        await server.run_actor({})


async def test_tools_are_registered():
    names = {t.name for t in await server.mcp.list_tools()}
    assert names == {
        "google_trends_interest",
        "google_trends_related_queries",
        "google_trends_trending_now",
        "google_trends_rank_keywords",
    }
