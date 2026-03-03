from datetime import datetime, timezone

from fastapi import APIRouter

from app.store import record_store

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
    storage = record_store.storage_summary()
    return {
        "status": "healthy",
        "version": "v0.3.0-production",
        "api_version": "v1",
        "uptime_seconds": _uptime_seconds(),
        "determinism_contract": "active",
        "neurosymbolic_boundary": "symbolic_only",
        "storage": storage["mode"],
        "pdf_parsing": "inactive",
        "languages_supported": ["en", "fr", "de", "es"],
        "soc2_controls": "documented_controls_only",
        "domains_available": ["legal_contract", "nda"],
        "storage_record_count": storage["record_count"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/v1/status",
    summary="API status",
    description="Returns operational status for core API components.",
)
async def status() -> dict:
    storage = record_store.storage_summary()
    return {
        "status": "operational",
        "uptime_seconds": _uptime_seconds(),
        "storage_mode": storage["mode"],
        "storage_record_count": storage["record_count"],
        "components": {
            "api": "operational",
            "database": "ephemeral_in_memory",
            "pdf_parsing": "inactive",
            "language_detection": "operational",
            "rate_limit": "operational",
        },
    }
