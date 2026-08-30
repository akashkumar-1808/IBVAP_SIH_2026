"""
Sector Normality Baseline Engine.

Evaluates observed border activity against defined/learned hourly baselines
without deep black-box anomaly models. Distinguishes COLD_START from abnormal.

Architecture Decision: DEC-0009
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timezone

from .schemas import SectorProfile, SectorContext, NormalityStatus
from backend.app.schemas.common import TargetClass

logger = logging.getLogger(__name__)


class SectorNormalityEngine:
    """
    Evaluates whether an observed target activity deviates from expected sector baselines.
    Supports seeded hackathon demo baselines and explicit cold-start status.
    """

    def __init__(self):
        self.profiles: Dict[str, SectorProfile] = {}
        # Pre-seed default sector profiles
        self._seed_default_profiles()

    def _seed_default_profiles(self) -> None:
        """Seeds standard border sectors with sensible baseline profiles."""
        default_sectors = ["sector_north_alpha", "sector_east_bravo", "default_sector", "sector_01"]
        for s_id in default_sectors:
            self.profiles[s_id] = SectorProfile(
                sector_id=s_id,
                name=f"Border {s_id.replace('_', ' ').title()}",
                sample_count=20,
                is_seeded_demo=True,
            )

    def register_profile(self, profile: SectorProfile) -> None:
        """Registers or updates a sector profile."""
        self.profiles[profile.sector_id] = profile

    def evaluate_activity(
        self,
        sector_id: str,
        timestamp_utc: datetime,
        target_class: TargetClass,
        observed_count: int = 1,
    ) -> SectorContext:
        """
        Evaluates normality of activity at the given timestamp for a sector.
        """
        hour = timestamp_utc.hour
        profile = self.profiles.get(sector_id)

        if not profile:
            # Fallback to default if available, or UNKNOWN
            profile = self.profiles.get("default_sector")
            if not profile:
                return SectorContext(
                    sector_id=sector_id,
                    timestamp_utc=timestamp_utc,
                    hour_of_day=hour,
                    status=NormalityStatus.UNKNOWN,
                    observed_rate=float(observed_count),
                    expected_rate=1.0,
                    deviation_ratio=1.0,
                    reason=f"Sector '{sector_id}' has no registered profile.",
                )

        # Check for Cold-Start
        if profile.sample_count < profile.min_samples_for_baseline:
            return SectorContext(
                sector_id=sector_id,
                timestamp_utc=timestamp_utc,
                hour_of_day=hour,
                status=NormalityStatus.COLD_START,
                observed_rate=float(observed_count),
                expected_rate=1.0,
                deviation_ratio=1.0,
                reason=f"Sector '{sector_id}' is in cold-start ({profile.sample_count}/{profile.min_samples_for_baseline} samples).",
            )

        expected_rate = profile.hour_activity_rates.get(hour, 1.0)
        deviation_ratio = observed_count / max(0.01, expected_rate)

        # Evaluate deviation thresholds:
        # If expected rate is low (e.g. night hours < 0.3) and human/vehicle observed -> UNUSUAL
        is_unusual = False
        reason = None

        if target_class in (TargetClass.PERSON, TargetClass.VEHICLE):
            if expected_rate < 0.25 and observed_count >= 1:
                is_unusual = True
                reason = f"Unusual {target_class.value} activity during low-baseline night hours ({hour:02d}:00 UTC, expected {expected_rate:.2f}/hr)."
            elif deviation_ratio > 3.0:
                is_unusual = True
                reason = f"Activity rate ({observed_count}) is {deviation_ratio:.1f}x higher than expected baseline ({expected_rate:.2f}/hr)."

        status = NormalityStatus.UNUSUAL if is_unusual else NormalityStatus.NORMAL
        if not reason:
            reason = f"Activity within normal parameters ({observed_count} observed vs {expected_rate:.2f} expected at {hour:02d}:00)."

        return SectorContext(
            sector_id=sector_id,
            timestamp_utc=timestamp_utc,
            hour_of_day=hour,
            status=status,
            observed_rate=float(observed_count),
            expected_rate=expected_rate,
            deviation_ratio=round(deviation_ratio, 2),
            reason=reason,
        )
