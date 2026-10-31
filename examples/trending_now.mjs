// npm i apify-client && APIFY_TOKEN=... node trending_now.mjs
import { ApifyClient } from 'apify-client';

const client = new ApifyClient({ token: process.env.APIFY_TOKEN });
const run = await client.actor('victorrodi/google-trends-api').call({ trendingNowGeos: ['US'], trendingNowMaxItems: 20 });
const { items } = await client.dataset(run.defaultDatasetId).listItems();
for (const t of items) console.log(`${t.rank}. ${t.title}: ${t.searchVolume ?? 0} searches`);
