"""Compare up to 5 keywords on Google Trends and print who is growing.

pip install "apify-client>=3"
APIFY_TOKEN=... python compare_keywords.py
"""

import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("victorrodi/google-trends-api").call(
    run_input={
        "searchTerms": ["chatgpt, gemini, claude"],
        "geo": "US",
        "timeRange": "today 12-m",
        "dataTypes": ["interestOverTime"],
    }
)
for item in client.dataset(run.default_dataset_id).iterate_items():
    for term, s in sorted(item["summary"].items(), key=lambda kv: -kv[1]["average"]):
        print(f"{term:10} avg {s['average']:5.1f}  latest {s['latest']:3}  change {s['changePct']:+.1f}%")
