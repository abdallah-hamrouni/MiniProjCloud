from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Stage
from schemas import StageInput, StageRead
from security import load_api_key, require_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.api_key = load_api_key()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="API de gestion des stages",
    description="Mini-projet : développer et déployer une API REST dans le Cloud.",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
    responses={401: {"description": "Clé API absente ou invalide."}},
)

DbSession = Annotated[Session, Depends(get_db)]


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def get_stage_or_404(id: int, db: Session) -> Stage:
    stage = db.get(Stage, id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage introuvable.")
    return stage


@app.get("/stages", response_model=list[StageRead], summary="Lister les stages")
def list_stages(db: DbSession):
    return db.scalars(select(Stage).order_by(Stage.id)).all()


@app.get("/stages/{id}", response_model=StageRead, summary="Consulter un stage")
def read_stage(id: int, db: DbSession):
    return get_stage_or_404(id, db)


@app.post(
    "/stages",
    response_model=StageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un stage",
)
def create_stage(data: StageInput, db: DbSession):
    stage = Stage(**data.model_dump())
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


@app.put("/stages/{id}", response_model=StageRead, summary="Modifier un stage")
def update_stage(id: int, data: StageInput, db: DbSession):
    stage = get_stage_or_404(id, db)
    for field, value in data.model_dump().items():
        setattr(stage, field, value)
    db.commit()
    db.refresh(stage)
    return stage


@app.delete(
    "/stages/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Supprimer un stage",
)
def delete_stage(id: int, db: DbSession):
    stage = get_stage_or_404(id, db)
    db.delete(stage)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
