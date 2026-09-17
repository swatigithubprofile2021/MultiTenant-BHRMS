from prometheus_client import Counter, Histogram

QUERY_COUNTER = Counter(
    "bot_queries_total",
    "Total queries per tenant",
    ["tenant", "status"],
)

QUERY_DURATION = Histogram(
    "bot_query_duration_seconds",
    "Query duration in seconds",
)

UPLOAD_COUNTER = Counter(
    "bot_uploads_total",
    "Total uploads",
    ["tenant", "status"],
)
