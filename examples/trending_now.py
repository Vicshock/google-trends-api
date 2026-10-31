"""What is trending on Google right now, with search volume (like trends.google.com/trending).

pip install "apify-client>=3"
APIFY_TOKEN=... python trending_now.py
"""

import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("victorrodi/google-trends-api").call(
    run_input={"trendingNowGeos": ["US"], "trendingNowHours": "24", "trendingNowMaxItems": 20}
)
for t in client.dataset(run.default_dataset_id).iterate_items():
    print(f"{t['rank']:2}. {t['title']:40} {t['searchVolume'] or 0:>10,} searches  {t['categories']}")
