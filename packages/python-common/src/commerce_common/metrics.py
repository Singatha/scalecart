from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "scalecart_http_requests_total",
    "HTTP requests processed",
    ("service", "method", "path", "status"),
)
HTTP_ERRORS = Counter(
    "scalecart_http_errors_total",
    "HTTP error responses",
    ("service", "method", "path", "status"),
)
HTTP_LATENCY = Histogram(
    "scalecart_http_request_duration_seconds",
    "HTTP request latency",
    ("service", "method", "path"),
)
