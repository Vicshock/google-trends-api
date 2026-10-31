"""Rank more than 5 keywords on one Google Trends scale (not possible with pytrends).

pip install "apify-client>=3"
APIFY_TOKEN=... python rank_keywords.py
"""

import os

from apify_client import ApifyClient

TERMS = "bitcoin, ethereum, solana, dogecoin, cardano, xrp, polkadot, chainlink, litecoin, avalanche"

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("victorrodi/google-trends-api").call(
    run_input={"searchTerms": [TERMS], "keywordRanking": True, "dataTypes": ["interestOverTime"], "geo": "US"}
)
for item in client.dataset(run.default_dataset_id).iterate_items():
    if item["type"] == "keywordRanking":
        for row in item["ranking"]:
            print(f"{row['rank']:2}. {row['term']:12} score {row['score']}")
