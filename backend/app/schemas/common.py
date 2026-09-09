from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TargetClass(str, Enum):
    PERSON = "person"
    VEHICLE = "vehicle"
    ANIMAL = "animal"
    UNKNOWN = "unknown"


class LightingCondition(str, Enum):
    DAY = "day"
    DUSK_DAWN = "dusk_dawn"
    NIGHT = "night"
    LOW_LIGHT = "low_light"
    UNKNOWN = "unknown"


class VisibilityQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INSUFFICIENT = "insufficient"


class WeatherHint(str, Enum):
    CLEAR = "clear"
    RAIN = "rain"
    FOG = "fog"
    SNOW = "snow"
    UNKNOWN = "unknown"


class TerrainProfile(str, Enum):
    FOREST = "forest"
    MOUNTAIN = "mountain"
    SNOW = "snow"
    OPEN_GROUND = "open_ground"
    WATER_BODY = "water_body"
    CUSTOM = "custom"


class TrackStatus(str, Enum):
    CANDIDATE = "candidate"
    TRACKED = "tracked"
    LOST = "lost"
    EXPIRED = "expired"


class ZoneType(str, Enum):
    SAFE = "safe"
    RESTRICTED = "restricted"
    BUFFER = "buffer"
    CRITICAL = "critical"


class BehaviorType(str, Enum):
    NORMAL = "normal"
    LOITERING = "loitering"
    PERSISTENT_APPROACH = "persistent_approach"
    RESTRICTED_ENTRY = "restricted_entry"
    RESTRICTED_OCCUPANCY = "restricted_occupancy"
    FENCE_CROSSED = "fence_crossed"
    FENCE_BREACH = "fence_breach"
    BORDER_CROSSING = "border_crossing"
    REPEATED_APPROACH = "repeated_approach"
    SPEED_ANOMALY = "speed_anomaly"
    UNKNOWN = "unknown"


class EventPriority(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StreamStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    OFFLINE = "offline"
