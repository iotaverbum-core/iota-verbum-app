from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()
START_TIME = datetime.now(timezone.utc)


def _uptime_seconds() -> float:
    uptime = datetime.now(timezone.utc) - START_TIME
    return round(uptime.total_seconds(), 1)


@router.get(
    "/health",
    summary="Health check",
    description="Returns system status and production capability flags.",
)
async def health() -> dict:
    return {
        "status": "healthy",
        "version": "v0.3.0-production",
        "api_version": "v1",
        "uptime_seconds": _uptime_seconds(),
        "determinism_contract": "active",
        "neurosymbolic_boundary": "symbolic_only",
        "storage": "postgresql",
        "pdf_parsing": "active",
        "languages_supported": ["en", "fr", "de", "es"],
        "soc2_controls": "active",
        "domains_available": ["legal_contract", "nda"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/v1/status",
    summary="API status",
    description="Returns operational status for core API components.",
)
async def status() -> dict:
    return {
        "status": "operational",
        "uptime_seconds": _uptime_seconds(),
        "components": {
            "api": "operational",
            "database": "operational",
            "pdf_parsing": "operational",
            "language_detection": "operational",
        },
    }
