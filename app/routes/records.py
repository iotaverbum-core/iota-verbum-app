from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_tenant
from app.store import record_store

router = APIRouter()


@router.get(
    "/records/{record_id}",
    summary="Fetch a stored provenance record",
    description="Returns the stored provenance JSON for the authenticated tenant.",
)
async def get_record(
    record_id: str,
    tenant: Annotated[dict, Depends(get_tenant)],
):
    record = record_store.get(tenant["tenant_id"], record_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Record {record_id} not found for this tenant.",
        )
    return record
