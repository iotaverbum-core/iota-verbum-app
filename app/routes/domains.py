from fastapi import APIRouter

router = APIRouter()

DOMAIN_REGISTRY = {
    "legal_contract": {
        "name": "Legal Contract",
        "description": "Extracts parties, obligations, defined terms, effective date, governing law, and termination conditions.",
        "schema": "schemas/legal_contract.json",
        "risk_tier": "high",
        "eu_ai_act_article": "Article 13 - Transparency obligations",
        "status": "stable",
    },
    "nda": {
        "name": "Non-Disclosure Agreement",
        "description": "Planned NDA extraction domain metadata. Runtime extraction support is pending in the pinned core package.",
        "schema": "schemas/nda.json",
        "risk_tier": "medium",
        "eu_ai_act_article": "Article 13 - Transparency obligations",
        "status": "planned",
    },
}


@router.get(
    "/domains",
    summary="List available extraction domains",
    description="Returns document domain metadata, governance context, and current runtime status.",
)
async def list_domains():
    return {
        "domains": DOMAIN_REGISTRY,
        "count": len(DOMAIN_REGISTRY),
        "neurosymbolic_layer": "symbolic_only",
        "boundary_version": "1.0",
    }
