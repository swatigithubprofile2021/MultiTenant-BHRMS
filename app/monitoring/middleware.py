import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.monitoring.metrics import QUERY_COUNTER, QUERY_DURATION


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request count and duration per tenant
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        # Extract tenant_id from headers or JWT
        tenant_id = request.headers.get("X-Tenant-ID", "unknown")

        try:
            response: Response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - start
            # Track duration
            QUERY_DURATION.observe(elapsed)
            # Track total requests per tenant + status
            QUERY_COUNTER.labels(tenant=tenant_id, status=status).inc()

        return response
