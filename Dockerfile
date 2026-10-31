FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY google_trends_mcp ./google_trends_mcp
RUN pip install --no-cache-dir .
# APIFY_TOKEN is read at tool-call time, so the server starts and lists its tools without it.
CMD ["google-trends-mcp"]
