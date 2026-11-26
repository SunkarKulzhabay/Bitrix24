from contextlib import asynccontextmanager
from pathlib import Path

from backend.app.employees.router import router as employees_router

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.app.org.router import router as org_router

from backend.app.auth.router import router as auth_router
from backend.app.database import Base, engine

from backend.app.database import Base, SessionLocal, engine
from backend.app.documents import models as document_models  # noqa: F401
from backend.app.documents.router import router as documents_router
from backend.app.documents.seed import seed_templates

from backend.app.projects import models as project_models  # noqa: F401
from backend.app.projects.router import router as projects_router

from backend.app.events import models as event_models  # noqa: F401
from backend.app.events.router import router as events_router

from backend.app.tasks import models as task_models  # noqa: F401
from backend.app.tasks.router import router as tasks_router

from backend.app.employees import models  # noqa: F401  (чтобы таблица попала в Base)
FRONT_DIR = Path(__file__).resolve().parents[2] / "front"

from backend.app.payroll import models as payroll_models  # noqa: F401
from backend.app.payroll.router import router as payroll_router

from pathlib import Path

from fastapi.staticfiles import StaticFiles

FRONT_DIR = Path(__file__).resolve().parents[2] / "front"


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Таблицы создаются миграциями: python -m alembic upgrade head
    async with SessionLocal() as session:
        await seed_templates(session)
    yield


app = FastAPI(
    title="Office CRM",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        return {"db": result.scalar()}


app.include_router(auth_router)

app.include_router(employees_router)

app.include_router(tasks_router)

app.include_router(events_router)

app.include_router(documents_router)

app.include_router(projects_router)

app.include_router(payroll_router)

app.include_router(org_router)

# Страницы (HTML, CSS, JS). Должно стоять ПОСЛЕ всех /api маршрутов.
app.mount("/", StaticFiles(directory=FRONT_DIR, html=True), name="front")

# Страницы (HTML, CSS, JS). Должно стоять ПОСЛЕ всех /api маршрутов.
app.mount("/", StaticFiles(directory=FRONT_DIR, html=True), name="front")
