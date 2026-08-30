"""
Pydantic schemas and contracts for Sector Normality and Context Baseline.

Architecture Decision: DEC-0009
"""

from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.app.schemas.common import TargetClass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NormalityStatus(str, Enum):
    """Categorical evaluation of sector activity relative to baseline expectations."""
    NORMAL = "normal"            # Activity aligns with historical/defined expectations
    UNUSUAL = "unusual"          # Significant deviation from expected baseline (e.g. 02:00 human movement)
    COLD_START = "cold_start"    # Insufficient historical baseline data to determine deviation
    UNKNOWN = "unknown"          # Sector not configured or invalid query


class SectorProfile(BaseModel):
    """Defines hourly expected activity rate and class profile for a monitored sector."""
    sector_id: str
    name: str = "Monitored Sector"
    hour_activity_rates: Dict[int, float] = Field(
        default_factory=lambda: {h: (0.1 if (0 <= h <= 5 or 21 <= h <= 23) else 2.0) for h in range(24)},
        description="Expected movements per hour for hours 0..23"
    )
    expected_classes: List[TargetClass] = Field(
        default_factory=lambda: [TargetClass.PERSON, TargetClass.VEHICLE, TargetClass.ANIMAL]
    )
    min_samples_for_baseline: int = Field(default=5, ge=1)
    sample_count: int = Field(default=10, ge=0)
    is_seeded_demo: bool = True


class SectorContext(BaseModel):
    """Evaluated normality context for an active event candidate or track."""
    sector_id: str
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    hour_of_day: int = Field(default=0, ge=0, le=23)
    status: NormalityStatus = NormalityStatus.NORMAL
    observed_rate: float = 1.0
    expected_rate: float = 1.0
    deviation_ratio: float = 1.0
    reason: Optional[str] = None
