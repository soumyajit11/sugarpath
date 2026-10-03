from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_dashboard
from app.services.cgm import demo_provider
from app.services.health import activities, confirm_medication, list_meals, log_meal, medications, sleep
from app.schemas.health import ActivityOut, ConfirmMedicationIn, GlucoseReadingOut, MealCreate, MealOut, MedicationOut, SleepOut
from app.schemas.assistant import ChatRequest, ChatResponse
from app.agents import SugarPathAgent
from app.schemas.memory import MemoryCreate, MemoryOut, MemoryUpdate
from app.services.memory import create_memory, delete_memory, list_memories, update_memory

router = APIRouter(prefix="/api")


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)):
    try:
        return get_dashboard(db)
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/glucose/latest", response_model=GlucoseReadingOut)
def glucose_latest(db: Session = Depends(get_db)):
    return demo_provider(db).readings(datetime.now() - timedelta(minutes=5), datetime.now())[-1]


@router.get("/glucose/history", response_model=list[GlucoseReadingOut])
def glucose_history(hours: int = Query(default=24, ge=1, le=168), db: Session = Depends(get_db)):
    now = datetime.now()
    return demo_provider(db).readings(now - timedelta(hours=hours), now)


@router.get("/glucose/range", response_model=list[GlucoseReadingOut])
def glucose_range(start: datetime, end: datetime, db: Session = Depends(get_db)):
    if end <= start or end - start > timedelta(days=7):
        raise HTTPException(status_code=422, detail="Choose a valid range of up to seven days.")
    return demo_provider(db).readings(start, end)


@router.get("/medicines", response_model=list[MedicationOut])
def medicine_list(db: Session = Depends(get_db)):
    return medications(db)


@router.post("/medicines/{medication_id}/confirm", response_model=MedicationOut)
def medicine_confirm(medication_id: int, payload: ConfirmMedicationIn, db: Session = Depends(get_db)):
    try:
        return confirm_medication(db, medication_id, payload.time_of_day)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/meals", response_model=list[MealOut])
def meal_list(days: int = Query(default=7, ge=1, le=31), db: Session = Depends(get_db)):
    return list_meals(db, days)


@router.post("/meals", response_model=MealOut, status_code=201)
def meal_create(payload: MealCreate, db: Session = Depends(get_db)):
    try:
        return log_meal(db, payload.description, payload.meal_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/activities", response_model=list[ActivityOut])
def activity_list(days: int = Query(default=7, ge=1, le=31), db: Session = Depends(get_db)):
    return activities(db, days)


@router.get("/sleep", response_model=list[SleepOut])
def sleep_list(days: int = Query(default=7, ge=1, le=31), db: Session = Depends(get_db)):
    return sleep(db, days)


@router.get("/memories", response_model=list[MemoryOut])
def memory_list(db: Session = Depends(get_db)):
    return list_memories(db)


@router.post("/memories", response_model=MemoryOut, status_code=201)
def memory_create(payload: MemoryCreate, db: Session = Depends(get_db)):
    try:
        memory, _ = create_memory(db, payload)
        return memory
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/memories/{memory_id}", response_model=MemoryOut)
def memory_update(memory_id: int, payload: MemoryUpdate, db: Session = Depends(get_db)):
    try:
        return update_memory(db, memory_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/memories/{memory_id}", status_code=204)
def memory_delete(memory_id: int, db: Session = Depends(get_db)):
    try:
        delete_memory(db, memory_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/assistant/chat", response_model=ChatResponse)
def assistant_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    return SugarPathAgent().respond(db, payload.message)
