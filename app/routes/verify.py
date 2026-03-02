from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.templating import Jinja2Templates

from app.auth import api_key_header, get_tenant
from app.store import record_store

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    return "text/html" in accept and "application/json" not in accept


@router.get(
    "/verify/{record_id}",
    summary="Verify a provenance record",
    description="Retrieve a stored provenance record by ID or render the standalone verification page.",
)
async def verify(
    request: Request,
    record_id: str,
    api_key: Annotated[str | None, Security(api_key_header)] = None,
):
    if _wants_html(request) and not api_key:
        return templates.TemplateResponse(
            request,
            "verify.html",
            {"record_id": record_id},
        )

    if api_key:
        tenant = get_tenant(api_key)
        record = record_store.get(tenant["tenant_id"], record_id)
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Record {record_id} not found for this tenant.",
            )
        tenant_id = tenant["tenant_id"]
    else:
        found = record_store.find(record_id)
        if not found:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found.")
        tenant_id, record = found

    return {
        "record_id": record_id,
        "tenant_id": tenant_id,
        "verified": True,
        "record": record,
    }
