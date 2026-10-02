"""Local CGM adapter boundary. DexcomProvider belongs here in a future integration."""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from math import sin
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GlucoseReading, PatientProfile
from app.schemas.health import GlucoseReadingOut


class CGMProvider(ABC):
    @abstractmethod
    def readings(self, start: datetime, end: datetime) -> list[GlucoseReadingOut]: ...


class MockCGMProvider(CGMProvider):
    """Deterministic, explicitly synthetic readings at five-minute intervals."""
    def __init__(self, db: Session, patient_id: int):
        self.db, self.patient_id = db, patient_id

    def readings(self, start: datetime, end: datetime) -> list[GlucoseReadingOut]:
        saved = self.db.scalars(select(GlucoseReading).where(
            GlucoseReading.patient_id == self.patient_id,
            GlucoseReading.timestamp >= start,
            GlucoseReading.timestamp <= end,
        ).order_by(GlucoseReading.timestamp)).all()
        by_time = {row.timestamp.replace(second=0, microsecond=0): row for row in saved}
        output: list[GlucoseReadingOut] = []
        cursor = start.replace(second=0, microsecond=0) - timedelta(minutes=start.minute % 5)
        while cursor <= end:
            row = by_time.get(cursor)
            if row:
                output.append(GlucoseReadingOut(timestamp=cursor, value_mg_dl=row.value_mg_dl, trend=row.trend, source=row.source, synthetic=True))
            else:
                # A small, repeatable daily curve; this is not physiological modelling.
                minutes = cursor.hour * 60 + cursor.minute
                breakfast = 26 if 8 * 60 <= minutes < 10 * 60 else 0
                dinner = 22 if 21 * 60 <= minutes < 23 * 60 else 0
                activity_dip = -8 if 18 * 60 <= minutes < 19 * 60 else 0
                value = round(108 + 7 * sin(minutes / 1440 * 6.283) + breakfast + dinner + activity_dip)
                trend = "Rising" if breakfast or dinner else "Falling" if activity_dip else "Stable"
                output.append(GlucoseReadingOut(timestamp=cursor, value_mg_dl=value, trend=trend, source="mock_cgm", synthetic=True))
            cursor += timedelta(minutes=5)
        return output


def demo_provider(db: Session) -> MockCGMProvider:
    patient = db.scalar(select(PatientProfile).limit(1))
    if patient is None:
        raise LookupError("Demo patient has not been seeded")
    return MockCGMProvider(db, patient.id)
