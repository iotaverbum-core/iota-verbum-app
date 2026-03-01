from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter, rate_limit_handler
from app.routes import analyse, domains, health, verify

app = FastAPI(
    title="IOTA VERBUM CORE API",
    description=(
        "Deterministic legal document intelligence with neurosymbolic "
        "provenance architecture. Every output is independently verifiable."
    ),
    version="0.1.0",
    contact={"name": "IOTA VERBUM CORE", "url": "https://github.com/iotaverbum-core"},
)


@app.get("/")
async def root():
    return {"status": "ok"}


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(analyse.router, prefix="/v1", tags=["Analysis"])
app.include_router(verify.router, prefix="/v1", tags=["Verification"])
app.include_router(domains.router, prefix="/v1", tags=["Domains"])
app.include_router(health.router, tags=["System"])
