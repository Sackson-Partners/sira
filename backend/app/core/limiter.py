"""
Rate Limiting
Uses slowapi (Starlette-native limiter built on the 'limits' library).
Default key: client IP address.
For production with multiple replicas, set REDIS_URL so limits are shared
across instances — otherwise each instance tracks independently.
"""

import os
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_storage_uri() -> str:
    """Return Redis URI if configured, else in-memory (single-instance only)."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_get_storage_uri(),
    headers_enabled=True,  # adds X-RateLimit-* headers to every response
)
