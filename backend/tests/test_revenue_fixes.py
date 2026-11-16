import asyncio
import json
import sqlite3
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import sys

import sys
import types

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Provide a lightweight stub for redis.asyncio if running outside Docker without redis installed
if "redis" not in sys.modules:
    redis_pkg = types.ModuleType("redis")
    redis_asyncio = types.ModuleType("redis.asyncio")
    redis_asyncio.Redis = MagicMock()
    redis_asyncio.Redis.from_url = MagicMock(return_value=MagicMock())
    redis_pkg.asyncio = redis_asyncio
    sys.modules["redis"] = redis_pkg
    sys.modules["redis.asyncio"] = redis_asyncio

from app.services.cache import build_revenue_cache_key, get_revenue_summary
from app.services.reservations import (
    calculate_monthly_revenue,
    get_month_utc_bounds,
    quantize_currency,
)


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value


class FakeRow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeSQLiteAsyncSession:
    """In-memory SQLite-backed async session executing the exact seed.sql dataset."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE properties (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                timezone TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE reservations (
                id TEXT PRIMARY KEY,
                property_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                check_in_date TEXT NOT NULL,
                check_out_date TEXT NOT NULL,
                total_amount TEXT NOT NULL
            )
        """)
        cur.executemany(
            "INSERT INTO properties VALUES (?, ?, ?, ?)",
            [
                ("prop-001", "tenant-a", "Beach House Alpha", "Europe/Paris"),
                ("prop-001", "tenant-b", "Mountain Lodge Beta", "America/New_York"),
                ("prop-002", "tenant-a", "City Apartment Downtown", "Europe/Paris"),
            ],
        )
        cur.executemany(
            "INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("res-tz-1", "prop-001", "tenant-a", "2024-02-29T23:30:00+00:00", "2024-03-05T10:00:00+00:00", "1250.000"),
                ("res-dec-1", "prop-001", "tenant-a", "2024-03-15T10:00:00+00:00", "2024-03-18T10:00:00+00:00", "333.333"),
                ("res-dec-2", "prop-001", "tenant-a", "2024-03-16T10:00:00+00:00", "2024-03-19T10:00:00+00:00", "333.333"),
                ("res-dec-3", "prop-001", "tenant-a", "2024-03-17T10:00:00+00:00", "2024-03-20T10:00:00+00:00", "333.334"),
                ("res-b-1", "prop-001", "tenant-b", "2024-03-10T15:00:00+00:00", "2024-03-12T11:00:00+00:00", "500.000"),
            ],
        )
        self.conn.commit()

    async def execute(self, query, params):
        sql = str(query)
        cur = self.conn.cursor()
        if "FROM properties" in sql:
            cur.execute(
                "SELECT timezone FROM properties WHERE id = ? AND tenant_id = ?",
                (params["property_id"], params["tenant_id"]),
            )
            row = cur.fetchone()
            return FakeResult(FakeRow(timezone=row["timezone"]) if row else None)

        if "FROM reservations" in sql:
            cur.execute(
                "SELECT check_in_date, total_amount FROM reservations WHERE property_id = ? AND tenant_id = ?",
                (params["property_id"], params["tenant_id"]),
            )
            rows = cur.fetchall()
            utc_start = params.get("utc_start")
            utc_end = params.get("utc_end")
            total = Decimal("0")
            count = 0
            for r in rows:
                dt = datetime.fromisoformat(r["check_in_date"])
                if utc_start and utc_end:
                    if not (utc_start <= dt < utc_end):
                        continue
                total += Decimal(r["total_amount"])
                count += 1
            return FakeResult(FakeRow(total_revenue=total, reservation_count=count))

        raise ValueError(f"Unexpected query: {sql}")


class TestRevenueFixes(unittest.TestCase):
    def test_cache_key_includes_tenant_and_period(self):
        key_a = build_revenue_cache_key("tenant-a", "prop-001", month=3, year=2024)
        key_b = build_revenue_cache_key("tenant-b", "prop-001", month=3, year=2024)
        self.assertNotEqual(key_a, key_b)
        self.assertEqual(key_a, "revenue:tenant-a:prop-001:2024:3")
        self.assertEqual(key_b, "revenue:tenant-b:prop-001:2024:3")

    def test_march_paris_timezone_includes_feb29_2330_utc(self):
        utc_start, utc_end = get_month_utc_bounds(2024, 3, "Europe/Paris")
        # 2024-03-01 00:00:00+01:00 == 2024-02-29 23:00:00+00:00
        self.assertEqual(utc_start, datetime(2024, 2, 29, 23, 0, tzinfo=timezone.utc))
        # Paris switches to CEST (+02:00) on March 31, 2024, so April 1 00:00+02:00 == March 31 22:00 UTC
        self.assertEqual(utc_end, datetime(2024, 3, 31, 22, 0, tzinfo=timezone.utc))

    def test_subcent_decimal_precision_no_cent_loss(self):
        total = Decimal("333.333") + Decimal("333.333") + Decimal("333.334")
        self.assertEqual(quantize_currency(total), Decimal("1000.00"))

    def test_monthly_revenue_timezone_and_precision_with_db(self):
        session = FakeSQLiteAsyncSession()
        march_total = asyncio.run(
            calculate_monthly_revenue("prop-001", 3, 2024, db_session=session, tenant_id="tenant-a")
        )
        feb_total = asyncio.run(
            calculate_monthly_revenue("prop-001", 2, 2024, db_session=session, tenant_id="tenant-a")
        )
        # March includes res-tz-1 (1250.000) + res-dec-1..3 (1000.000) = 2250.00
        self.assertEqual(march_total, Decimal("2250.00"))
        self.assertEqual(feb_total, Decimal("0.00"))

    def test_cache_isolation_between_tenants_for_same_property_id(self):
        fake_redis = FakeRedis()

        async def run_test():
            with patch("app.services.cache.redis_client", fake_redis):
                with patch(
                    "app.services.reservations.calculate_total_revenue",
                    new=AsyncMock(
                        side_effect=[
                            {"property_id": "prop-001", "tenant_id": "tenant-a", "total": "2250.00", "currency": "USD", "count": 4},
                            {"property_id": "prop-001", "tenant_id": "tenant-b", "total": "500.00", "currency": "USD", "count": 1},
                        ]
                    ),
                ):
                    res_a = await get_revenue_summary("prop-001", "tenant-a", month=3, year=2024)
                    res_b = await get_revenue_summary("prop-001", "tenant-b", month=3, year=2024)
                    # Second fetch for tenant-a must hit tenant-a cache, not tenant-b
                    res_a_cached = await get_revenue_summary("prop-001", "tenant-a", month=3, year=2024)
                    return res_a, res_b, res_a_cached

        res_a, res_b, res_a_cached = asyncio.run(run_test())
        self.assertEqual(res_a["total"], "2250.00")
        self.assertEqual(res_b["total"], "500.00")
        self.assertEqual(res_a_cached["total"], "2250.00")
        self.assertEqual(json.loads(fake_redis.store["revenue:tenant-a:prop-001:2024:3"])["total"], "2250.00")
        self.assertEqual(json.loads(fake_redis.store["revenue:tenant-b:prop-001:2024:3"])["total"], "500.00")


if __name__ == "__main__":
    unittest.main()
