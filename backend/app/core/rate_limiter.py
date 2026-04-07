from __future__ import annotations

import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, status

_BUCKETS: dict[str, deque[float]] = {}
_LOCK = Lock()


def enforce_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    now = time.monotonic()
    cutoff = now - max(window_seconds, 1)

    with _LOCK:
        bucket = _BUCKETS.setdefault(key, deque())
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= max(max_requests, 1):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        bucket.append(now)
