from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

load_dotenv()

from src.api.routes.generate import router as generate_router
from src.api.routes.validate import router as validate_router
from src.api.routes.run import router as run_router
from src.api.routes.generate_steps import router as generate_steps_router
from src.api.routes.n8n import router as n8n_router
from src.api.routes.auth import router as auth_router
from src.api.routes.history import router as history_router
from src.db.database import init_db

app = FastAPI(
    title="LastautAI",
    description="Natural Language to Workflow Automation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router)
app.include_router(validate_router)
app.include_router(run_router)
app.include_router(generate_steps_router)
app.include_router(n8n_router)
app.include_router(auth_router)
app.include_router(history_router)

init_db()

UI_PATH = Path(__file__).parent.parent.parent / "ui" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return UI_PATH.read_text()


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
