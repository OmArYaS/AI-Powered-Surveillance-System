from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config.settings import settings
from src.presentation.routes.camera import router as camera_router, shutdown_stream
from src.presentation.routes.face import router as face_router
from src.presentation.routes.items import router as items_router
from src.presentation.routes.settings import router as settings_router
from src.presentation.routes.threat import router as threat_router

ROOT_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    shutdown_stream()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    app.include_router(camera_router)
    app.include_router(settings_router)
    app.include_router(face_router)
    app.include_router(threat_router)
    app.include_router(items_router)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    return app
