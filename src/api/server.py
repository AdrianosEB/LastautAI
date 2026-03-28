from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.routes.generate import router as generate_router
from src.api.routes.validate import router as validate_router

app = FastAPI(
    title="LastautAI",
    description="Natural Language to Workflow Automation",
    version="0.1.0",
)

app.include_router(generate_router)
app.include_router(validate_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": str(exc),
        },
    )
