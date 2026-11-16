import json
import logging
import os
from typing import Any, Dict, Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def build_revenue_cache_key(
    tenant_id: str,
    property_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> str:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    y = str(year) if year is not None else "all"
    m = str(month) if month is not None else "all"
    # scope by tenant_id so shared property IDs like prop-001 never leak across clients
    return f"revenue:{tenant_id}:{property_id}:{y}:{m}"


async def get_revenue_summary(
    property_id: str,
    tenant_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    cache_key = build_revenue_cache_key(tenant_id, property_id, month=month, year=year)

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis read skipped ({cache_key}): {e}")

    from app.services.reservations import calculate_total_revenue

    result = await calculate_total_revenue(property_id, tenant_id, month=month, year=year)

    try:
        await redis_client.setex(cache_key, 300, json.dumps(result))
    except Exception as e:
        logger.warning(f"Redis write skipped ({cache_key}): {e}")

    return result
