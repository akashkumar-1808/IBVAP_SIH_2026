from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .common import LightingCondition, VisibilityQuality, WeatherHint, TerrainProfile


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EnvironmentState(BaseModel):
    camera_id: str
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    lighting: LightingCondition = LightingCondition.UNKNOWN
    brightness: float = Field(default=0.5, ge=0.0, le=1.0, description="Mean luminance normalized [0, 1]")
    contrast: float = Field(default=0.5, ge=0.0, le=1.0, description="RMS contrast normalized [0, 1]")
    blur_score: float = Field(default=100.0, ge=0.0, description="Laplacian variance (sharpness)")
    noise_estimate: float = Field(default=0.0, ge=0.0, le=1.0, description="Estimated high-frequency noise")
    visibility: VisibilityQuality = VisibilityQuality.GOOD
    weather_hint: WeatherHint = WeatherHint.CLEAR
    terrain_profile: TerrainProfile = TerrainProfile.OPEN_GROUND
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Aggregate visual reliability score [0, 1]")
    is_enhancement_applied: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
