import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentMemory, PatientProfile
from app.schemas.memory import MemoryCreate, MemoryUpdate

APPROVED_TYPES = {"routine", "preference", "patient_fact", "system_observation"}
APPROVED_SOURCES = {"user_explicit", "user_confirmed", "system_observation"}
MEDICAL_MEMORY_PATTERN = re.compile(r"\b(diagnos(?:is|ed)|dose|dosage|increase|decrease|extra|medication change|treatment instruction|insulin)\b", re.I)


def demo_patient_id(db: Session) -> int:
    profile = db.scalar(select(PatientProfile).limit(1))
    if not profile: raise LookupError("Demo patient is unavailable.")
    return profile.id


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _validate(memory_type: str, source: str, content: str) -> None:
    if memory_type not in APPROVED_TYPES or source not in APPROVED_SOURCES: raise ValueError("That memory category or source is not allowed.")
    if memory_type == "system_observation" and source != "system_observation": raise ValueError("Derived observations must be labeled as observed data.")
    if memory_type != "system_observation" and source == "system_observation": raise ValueError("Observed data must be stored as a derived observation.")
    if MEDICAL_MEMORY_PATTERN.search(content): raise ValueError("Medical instructions, diagnoses, and dose changes cannot be stored as memory.")


def list_memories(db: Session, patient_id: int | None = None) -> list[AgentMemory]:
    patient_id = patient_id or demo_patient_id(db)
    return list(db.scalars(select(AgentMemory).where(AgentMemory.patient_id == patient_id).order_by(AgentMemory.updated_at.desc())).all())


def create_memory(db: Session, payload: MemoryCreate, patient_id: int | None = None) -> tuple[AgentMemory, bool]:
    patient_id = patient_id or demo_patient_id(db); _validate(payload.memory_type, payload.source, payload.content)
    canonical = _normalized(payload.content)
    existing = db.scalars(select(AgentMemory).where(AgentMemory.patient_id == patient_id, AgentMemory.memory_type == payload.memory_type)).all()
    duplicate = next((item for item in existing if _normalized(item.content) == canonical), None)
    if duplicate: return duplicate, False
    memory = AgentMemory(patient_id=patient_id, memory_type=payload.memory_type, content=payload.content, source=payload.source)
    db.add(memory); db.commit(); db.refresh(memory)
    return memory, True


def update_memory(db: Session, memory_id: int, payload: MemoryUpdate, patient_id: int | None = None) -> AgentMemory:
    patient_id = patient_id or demo_patient_id(db)
    memory = db.scalar(select(AgentMemory).where(AgentMemory.id == memory_id, AgentMemory.patient_id == patient_id))
    if not memory: raise LookupError("Memory not found.")
    values = payload.model_dump(exclude_unset=True); memory_type = values.get("memory_type", memory.memory_type); source = values.get("source", memory.source); content = values.get("content", memory.content)
    _validate(memory_type, source, content)
    for field, value in values.items(): setattr(memory, field, value)
    db.commit(); db.refresh(memory); return memory


def delete_memory(db: Session, memory_id: int, patient_id: int | None = None) -> None:
    patient_id = patient_id or demo_patient_id(db); memory = db.scalar(select(AgentMemory).where(AgentMemory.id == memory_id, AgentMemory.patient_id == patient_id))
    if not memory: raise LookupError("Memory not found.")
    db.delete(memory); db.commit()


def retrieve_memories(db: Session, query: str = "", memory_type: str | None = None, patient_id: int | None = None) -> list[AgentMemory]:
    if memory_type and memory_type not in APPROVED_TYPES: raise ValueError("That memory category is not allowed.")
    memories = list_memories(db, patient_id)
    if memory_type: memories = [memory for memory in memories if memory.memory_type == memory_type]
    terms = set(_normalized(query).split())
    if not terms or "remember" in terms: return memories
    matches = [memory for memory in memories if terms & set(_normalized(memory.content).split())]
    return memories if not matches and {"what", "me"}.issubset(terms) else matches
