"""In-memory cache for Canvas API responses. TTL configurable via config."""
import logging
from time import time
from typing import Any, Awaitable, Callable, Optional

import config

logger = logging.getLogger(__name__)

_store: dict[str, tuple[Any, float]] = {}


async def get_or_fetch(
    key: str,
    fetcher: Callable[[], Awaitable[Any]],
    ttl_minutes: Optional[int] = None,
) -> Any:
    """Return cached data if valid; otherwise call fetcher, store and return."""
    ttl = ttl_minutes if ttl_minutes is not None else config.CACHE_TTL_MINUTES
    now = time()
    if key in _store:
        data, expires_at = _store[key]
        if expires_at > now:
            logger.info("Cache hit: %s", key)
            return data
    data = await fetcher()
    _store[key] = (data, now + ttl * 60)
    return data


def clear() -> None:
    """Clear all cached entries."""
    _store.clear()
    logger.info("Cache cleared")
