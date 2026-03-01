from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()
START_TIME = datetime.now(timezone.utc)


@router.get(
    "/health",
    summary="Health check",
    description="Returns system status, version, and determinism contract status.",
)
async def health():
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "version": "v0.2.1-neurosymbolic",
        "api_version": "v1",
        "uptime_seconds": round(uptime, 1),
        "determinism_contract": "active",
        "neurosymbolic_boundary": "symbolic_only",
        "domains_available": ["legal_contract", "nda"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
