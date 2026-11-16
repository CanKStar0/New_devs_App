from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import logging

logger = logging.getLogger(__name__)

# Seed-accurate fallback used only when Postgres is not reachable
_SEED_PROPERTIES = [
    {"id": "prop-001", "tenant_id": "tenant-a", "name": "Beach House Alpha", "timezone": "Europe/Paris"},
    {"id": "prop-002", "tenant_id": "tenant-a", "name": "City Apartment Downtown", "timezone": "Europe/Paris"},
    {"id": "prop-003", "tenant_id": "tenant-a", "name": "Country Villa Estate", "timezone": "Europe/Paris"},
    {"id": "prop-001", "tenant_id": "tenant-b", "name": "Mountain Lodge Beta", "timezone": "America/New_York"},
    {"id": "prop-004", "tenant_id": "tenant-b", "name": "Lakeside Cottage", "timezone": "America/New_York"},
    {"id": "prop-005", "tenant_id": "tenant-b", "name": "Urban Loft Modern", "timezone": "America/New_York"},
]

_SEED_RESERVATIONS = [
    {"id": "res-tz-1", "property_id": "prop-001", "tenant_id": "tenant-a", "check_in": "2024-02-29T23:30:00+00:00", "check_out": "2024-03-05T10:00:00+00:00", "amount": "1250.000"},
    {"id": "res-dec-1", "property_id": "prop-001", "tenant_id": "tenant-a", "check_in": "2024-03-15T10:00:00+00:00", "check_out": "2024-03-18T10:00:00+00:00", "amount": "333.333"},
    {"id": "res-dec-2", "property_id": "prop-001", "tenant_id": "tenant-a", "check_in": "2024-03-16T10:00:00+00:00", "check_out": "2024-03-19T10:00:00+00:00", "amount": "333.333"},
    {"id": "res-dec-3", "property_id": "prop-001", "tenant_id": "tenant-a", "check_in": "2024-03-17T10:00:00+00:00", "check_out": "2024-03-20T10:00:00+00:00", "amount": "333.334"},
    {"id": "res-004", "property_id": "prop-002", "tenant_id": "tenant-a", "check_in": "2024-03-05T14:00:00+00:00", "check_out": "2024-03-08T11:00:00+00:00", "amount": "1250.000"},
    {"id": "res-005", "property_id": "prop-002", "tenant_id": "tenant-a", "check_in": "2024-03-12T16:00:00+00:00", "check_out": "2024-03-15T10:00:00+00:00", "amount": "1475.500"},
    {"id": "res-006", "property_id": "prop-002", "tenant_id": "tenant-a", "check_in": "2024-03-20T15:00:00+00:00", "check_out": "2024-03-23T12:00:00+00:00", "amount": "1199.250"},
    {"id": "res-007", "property_id": "prop-002", "tenant_id": "tenant-a", "check_in": "2024-03-25T18:00:00+00:00", "check_out": "2024-03-28T14:00:00+00:00", "amount": "1050.750"},
    {"id": "res-008", "property_id": "prop-003", "tenant_id": "tenant-a", "check_in": "2024-03-02T15:00:00+00:00", "check_out": "2024-03-09T12:00:00+00:00", "amount": "2850.000"},
    {"id": "res-009", "property_id": "prop-003", "tenant_id": "tenant-a", "check_in": "2024-03-18T16:00:00+00:00", "check_out": "2024-03-25T11:00:00+00:00", "amount": "3250.500"},
    {"id": "res-010", "property_id": "prop-004", "tenant_id": "tenant-b", "check_in": "2024-03-08T18:00:00+00:00", "check_out": "2024-03-11T15:00:00+00:00", "amount": "420.000"},
    {"id": "res-011", "property_id": "prop-004", "tenant_id": "tenant-b", "check_in": "2024-03-14T17:00:00+00:00", "check_out": "2024-03-18T14:00:00+00:00", "amount": "560.750"},
    {"id": "res-012", "property_id": "prop-004", "tenant_id": "tenant-b", "check_in": "2024-03-22T16:00:00+00:00", "check_out": "2024-03-26T13:00:00+00:00", "amount": "480.250"},
    {"id": "res-013", "property_id": "prop-004", "tenant_id": "tenant-b", "check_in": "2024-03-28T19:00:00+00:00", "check_out": "2024-03-31T15:00:00+00:00", "amount": "315.500"},
    {"id": "res-014", "property_id": "prop-005", "tenant_id": "tenant-b", "check_in": "2024-03-06T19:00:00+00:00", "check_out": "2024-03-10T16:00:00+00:00", "amount": "920.000"},
    {"id": "res-015", "property_id": "prop-005", "tenant_id": "tenant-b", "check_in": "2024-03-15T18:00:00+00:00", "check_out": "2024-03-19T17:00:00+00:00", "amount": "1080.400"},
    {"id": "res-016", "property_id": "prop-005", "tenant_id": "tenant-b", "check_in": "2024-03-24T20:00:00+00:00", "check_out": "2024-03-29T14:00:00+00:00", "amount": "1255.600"},
]


def quantize_currency(amount: Decimal) -> Decimal:
    return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_zoneinfo(tz_name: str = "UTC") -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or "UTC")
    except ZoneInfoNotFoundError:
        logger.warning(f"Unknown timezone '{tz_name}', using UTC")
        return ZoneInfo("UTC")


def get_month_utc_bounds(year: int, month: int, tz_name: str = "UTC") -> Tuple[datetime, datetime]:
    tz = _get_zoneinfo(tz_name)
    # Convert property-local month boundaries to UTC so midnight-adjacent bookings land in the right month
    local_start = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    if month < 12:
        local_end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        local_end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)

    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def _format_local_iso(dt: datetime, tz_name: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_get_zoneinfo(tz_name)).strftime("%Y-%m-%d %H:%M %Z")


async def _query_property_revenue(
    session,
    property_id: str,
    tenant_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    from sqlalchemy import text

    prop_row = (
        await session.execute(
            text("SELECT timezone FROM properties WHERE id = :property_id AND tenant_id = :tenant_id"),
            {"property_id": property_id, "tenant_id": tenant_id},
        )
    ).fetchone()

    if not prop_row:
        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": "0.00",
            "currency": "USD",
            "count": 0,
        }

    prop_tz = prop_row.timezone or "UTC"
    params: Dict[str, Any] = {"property_id": property_id, "tenant_id": tenant_id}

    date_filter = ""
    if month is not None and year is not None:
        utc_start, utc_end = get_month_utc_bounds(year, month, prop_tz)
        params["utc_start"] = utc_start
        params["utc_end"] = utc_end
        date_filter = "AND check_in_date >= :utc_start AND check_in_date < :utc_end"

    row = (
        await session.execute(
            text(f"""
                SELECT
                    COALESCE(SUM(total_amount), 0) AS total_revenue,
                    COUNT(*) AS reservation_count
                FROM reservations
                WHERE property_id = :property_id
                  AND tenant_id = :tenant_id
                  {date_filter}
            """),
            params,
        )
    ).fetchone()

    # Keep Decimal precision across SUM before rounding to 2 decimals at the end
    raw_total = Decimal(str(row.total_revenue)) if row and row.total_revenue is not None else Decimal("0")
    total = quantize_currency(raw_total)
    count = int(row.reservation_count) if row and row.reservation_count is not None else 0

    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": str(total),
        "currency": "USD",
        "count": count,
        "timezone": prop_tz,
    }


async def calculate_monthly_revenue(
    property_id: str,
    month: int,
    year: int,
    db_session=None,
    tenant_id: Optional[str] = None,
) -> Decimal:
    if db_session is not None and tenant_id is not None:
        summary = await _query_property_revenue(
            db_session, property_id, tenant_id, month=month, year=year
        )
        return Decimal(summary["total"])

    if tenant_id is not None:
        summary = await calculate_total_revenue(property_id, tenant_id, month=month, year=year)
        return Decimal(summary["total"])

    return Decimal("0.00")


def _fallback_filter_reservations(
    tenant_id: str,
    property_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    prop_map = {
        p["id"]: p for p in _SEED_PROPERTIES if p["tenant_id"] == tenant_id
    }
    matched: List[Dict[str, Any]] = []
    for r in _SEED_RESERVATIONS:
        if r["tenant_id"] != tenant_id:
            continue
        if property_id and r["property_id"] != property_id:
            continue
        prop = prop_map.get(r["property_id"])
        tz_name = prop["timezone"] if prop else "UTC"
        dt_in = datetime.fromisoformat(r["check_in"])
        if month is not None and year is not None:
            utc_start, utc_end = get_month_utc_bounds(year, month, tz_name)
            if not (utc_start <= dt_in < utc_end):
                continue
        matched.append({
            "id": r["id"],
            "property_id": r["property_id"],
            "property_name": prop["name"] if prop else r["property_id"],
            "timezone": tz_name,
            "check_in_date": r["check_in"],
            "check_in_local": _format_local_iso(dt_in, tz_name),
            "check_out_date": r["check_out"],
            "total_amount": r["amount"],
            "currency": "USD",
        })
    return matched


async def calculate_total_revenue(
    property_id: str,
    tenant_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        from app.core.database_pool import db_pool

        if db_pool.session_factory is None:
            await db_pool.initialize()

        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                return await _query_property_revenue(
                    session, property_id, tenant_id, month=month, year=year
                )
        raise RuntimeError("Database pool not available")

    except Exception as e:
        logger.warning(f"DB query failed for {property_id} ({tenant_id}): {e}")
        rows = _fallback_filter_reservations(tenant_id, property_id=property_id, month=month, year=year)
        raw_total = sum((Decimal(r["total_amount"]) for r in rows), Decimal("0"))
        total = quantize_currency(raw_total)
        prop = next((p for p in _SEED_PROPERTIES if p["tenant_id"] == tenant_id and p["id"] == property_id), None)
        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(total),
            "currency": "USD",
            "count": len(rows),
            "timezone": prop["timezone"] if prop else "UTC",
        }


async def list_tenant_properties(tenant_id: str) -> List[Dict[str, Any]]:
    try:
        from sqlalchemy import text
        from app.core.database_pool import db_pool

        if db_pool.session_factory is None:
            await db_pool.initialize()

        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                rows = (
                    await session.execute(
                        text("""
                            SELECT id, tenant_id, name, timezone
                            FROM properties
                            WHERE tenant_id = :tenant_id
                            ORDER BY id
                        """),
                        {"tenant_id": tenant_id},
                    )
                ).fetchall()
                return [
                    {
                        "id": r.id,
                        "tenant_id": r.tenant_id,
                        "name": r.name,
                        "timezone": r.timezone,
                    }
                    for r in rows
                ]
        raise RuntimeError("Database pool not available")
    except Exception as e:
        logger.warning(f"DB property list fallback ({tenant_id}): {e}")
        return [dict(p) for p in _SEED_PROPERTIES if p["tenant_id"] == tenant_id]


async def list_tenant_reservations(
    tenant_id: str,
    property_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        from sqlalchemy import text
        from app.core.database_pool import db_pool

        if db_pool.session_factory is None:
            await db_pool.initialize()

        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                params: Dict[str, Any] = {"tenant_id": tenant_id}
                prop_filter = ""
                if property_id:
                    prop_filter = "AND r.property_id = :property_id"
                    params["property_id"] = property_id

                rows = (
                    await session.execute(
                        text(f"""
                            SELECT r.id, r.property_id, p.name AS property_name, p.timezone,
                                   r.check_in_date, r.check_out_date, r.total_amount, r.currency
                            FROM reservations r
                            JOIN properties p ON r.property_id = p.id AND r.tenant_id = p.tenant_id
                            WHERE r.tenant_id = :tenant_id
                              {prop_filter}
                            ORDER BY r.check_in_date ASC
                        """),
                        params,
                    )
                ).fetchall()

                items: List[Dict[str, Any]] = []
                for r in rows:
                    tz_name = r.timezone or "UTC"
                    dt_in = r.check_in_date
                    if month is not None and year is not None:
                        utc_start, utc_end = get_month_utc_bounds(year, month, tz_name)
                        dt_cmp = dt_in if dt_in.tzinfo else dt_in.replace(tzinfo=timezone.utc)
                        if not (utc_start <= dt_cmp < utc_end):
                            continue
                    items.append({
                        "id": r.id,
                        "property_id": r.property_id,
                        "property_name": r.property_name,
                        "timezone": tz_name,
                        "check_in_date": dt_in.isoformat(),
                        "check_in_local": _format_local_iso(dt_in, tz_name),
                        "check_out_date": r.check_out_date.isoformat(),
                        "total_amount": str(r.total_amount),
                        "currency": r.currency or "USD",
                    })

                raw_total = sum((Decimal(i["total_amount"]) for i in items), Decimal("0"))
                total = quantize_currency(raw_total)
                return {
                    "tenant_id": tenant_id,
                    "reservations": items,
                    "count": len(items),
                    "total_revenue": float(total),
                    "total_revenue_exact": str(total),
                    "currency": "USD",
                }
        raise RuntimeError("Database pool not available")
    except Exception as e:
        logger.warning(f"DB reservations list fallback ({tenant_id}): {e}")
        items = _fallback_filter_reservations(tenant_id, property_id=property_id, month=month, year=year)
        raw_total = sum((Decimal(i["total_amount"]) for i in items), Decimal("0"))
        total = quantize_currency(raw_total)
        return {
            "tenant_id": tenant_id,
            "reservations": items,
            "count": len(items),
            "total_revenue": float(total),
            "total_revenue_exact": str(total),
            "currency": "USD",
        }
