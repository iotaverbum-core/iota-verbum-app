from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
templates = Jinja2Templates(directory="app/templates")


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    return "text/html" in accept and "application/json" not in accept


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if _wants_html(request):
        return templates.TemplateResponse(request, "index.html", {})
    return JSONResponse({"status": "ok"})


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if _wants_html(request):
        return templates.TemplateResponse(request, "404.html", {}, status_code=404)
    return JSONResponse({"detail": "Not Found"}, status_code=404)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if _wants_html(request):
        return templates.TemplateResponse(request, "500.html", {}, status_code=500)
    raise exc


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(analyse.router, prefix="/v1", tags=["Analysis"])
app.include_router(verify.router, prefix="/v1", tags=["Verification"])
app.include_router(domains.router, prefix="/v1", tags=["Domains"])
app.include_router(health.router, tags=["System"])
