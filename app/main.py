from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter, rate_limit_handler
from app.routes import analyse, domains, health, records, verify


class CachedStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers.setdefault("Cache-Control", "public, max-age=3600")
        return response

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = exc.errors()
    missing_file = any("file" in ".".join(str(part) for part in item.get("loc", [])) for item in details)
    detail = "Validation error."
    if missing_file:
        detail = "Missing file upload."
    if _wants_html(request):
        return templates.TemplateResponse(
            request,
            "500.html",
            {"message": detail},
            status_code=422,
        )
    return JSONResponse({"detail": detail, "errors": details}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if _wants_html(request):
        return templates.TemplateResponse(request, "500.html", {}, status_code=500)
    raise exc


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.mount("/static", CachedStaticFiles(directory="static"), name="static")

app.include_router(analyse.router, prefix="/v1", tags=["Analysis"])
app.include_router(verify.router, prefix="/v1", tags=["Verification"])
app.include_router(records.router, prefix="/v1", tags=["Records"])
app.include_router(domains.router, prefix="/v1", tags=["Domains"])
app.include_router(health.router, tags=["System"])
