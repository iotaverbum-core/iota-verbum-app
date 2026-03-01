from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_tenant
from app.store import record_store

router = APIRouter()


@router.get(
    "/verify/{record_id}",
    summary="Verify a provenance record",
    description="Retrieve a stored provenance record by ID. Records are scoped to the tenant of the requesting API key.",
)
async def verify(
    record_id: str,
    tenant: Annotated[dict, Depends(get_tenant)],
):
    record = record_store.get(tenant["tenant_id"], record_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Record {record_id} not found for this tenant.",
        )
    return {
        "record_id": record_id,
        "tenant_id": tenant["tenant_id"],
        "verified": True,
        "record": record,
    }
