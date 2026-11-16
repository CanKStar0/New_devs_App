from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    if (month is None) != (year is None):
        raise HTTPException(
            status_code=400,
            detail="Both month and year must be provided together",
        )

    revenue_data = await get_revenue_summary(
        property_id, tenant_id, month=month, year=year
    )

    quantized_total = Decimal(str(revenue_data["total"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "property_id": revenue_data["property_id"],
        "tenant_id": tenant_id,
        "total_revenue": float(quantized_total),
        "total_revenue_exact": str(quantized_total),
        "currency": revenue_data["currency"],
        "reservations_count": revenue_data["count"],
    }
