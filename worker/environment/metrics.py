from typing import Tuple, Dict, Any
import cv2
import numpy as np
from .schemas import LightingCondition, VisibilityQuality


def compute_luminance_stats(gray_image: np.ndarray) -> Tuple[float, float, float, float]:
    """
    Computes normalized mean luminance, std deviation, and 10th/90th percentiles.
    Returns: (mean [0, 1], std [0, 1], p10 [0, 1], p90 [0, 1])
    """
    if gray_image.size == 0:
        return 0.0, 0.0, 0.0, 0.0

    mean_val = float(np.mean(gray_image)) / 255.0
    std_val = float(np.std(gray_image)) / 255.0
    p10 = float(np.percentile(gray_image, 10)) / 255.0
    p90 = float(np.percentile(gray_image, 90)) / 255.0
    return mean_val, std_val, p10, p90


def compute_rms_contrast(gray_image: np.ndarray) -> float:
    """
    Computes normalized RMS (Root Mean Square) contrast: std(I) / 255.0
    Returns float in range [0.0, 1.0].
    """
    if gray_image.size == 0:
        return 0.0
    return float(np.std(gray_image)) / 255.0


def compute_sharpness_laplacian(gray_image: np.ndarray) -> float:
    """
    Computes blur / sharpness score as the variance of the Laplacian filter.
    Higher values indicate sharp edges; lower values indicate severe blur or flat fields.
    """
    if gray_image.size == 0 or gray_image.shape[0] < 3 or gray_image.shape[1] < 3:
        return 0.0
    laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
    return float(np.var(laplacian))


def estimate_image_noise(gray_image: np.ndarray) -> float:
    """
    Fast noise standard deviation estimation using Immerkær's 3x3 residual mask.
    Returns normalized noise estimate in [0.0, 1.0].
    """
    h, w = gray_image.shape[:2]
    if h < 5 or w < 5:
        return 0.0

    # Immerkær noise kernel
    kernel = np.array([
        [1, -2, 1],
        [-2, 4, -2],
        [1, -2, 1],
    ], dtype=np.float32)

    sigma = np.sum(np.abs(cv2.filter2D(gray_image.astype(np.float32), -1, kernel)))
    sigma = sigma * np.sqrt(0.5 * np.pi) / (6.0 * (w - 2) * (h - 2))

    # Normalize standard deviation (0 to ~25.5 mapped to 0.0 to 1.0)
    return float(np.clip(sigma / 25.5, 0.0, 1.0))


def classify_lighting_condition(
    mean_luminance: float,
    day_threshold: float = 0.40,
    dusk_threshold: float = 0.20,
    low_light_threshold: float = 0.08,
) -> LightingCondition:
    """
    Classifies lighting condition based on mean frame luminance.
    """
    if mean_luminance >= day_threshold:
        return LightingCondition.DAY
    elif mean_luminance >= dusk_threshold:
        return LightingCondition.DUSK_DAWN
    elif mean_luminance >= low_light_threshold:
        return LightingCondition.LOW_LIGHT
    else:
        return LightingCondition.NIGHT


def compute_aggregate_quality(
    brightness: float,
    contrast: float,
    blur_score: float,
    noise_estimate: float,
    blur_midpoint: float = 100.0,
) -> float:
    """
    Computes an aggregate visual quality score [0.0, 1.0] from composite metrics.
    Penalizes extreme dark/washout, low contrast, severe blur, and excessive noise.
    """
    # 1. Exposure score: optimal brightness around 0.45 - 0.65
    exposure_penalty = 1.0 - 2.0 * abs(brightness - 0.50)
    exposure_score = np.clip(exposure_penalty, 0.0, 1.0)

    # 2. Contrast score: linear scale up to 0.35 (normal contrast is ~0.15 - 0.30)
    contrast_score = np.clip(contrast / 0.25, 0.0, 1.0)

    # 3. Sharpness score: sigmoid curve around blur_midpoint
    sharpness_score = 1.0 / (1.0 + np.exp(-4.0 * (blur_score - blur_midpoint) / blur_midpoint))
    sharpness_score = float(np.clip(sharpness_score, 0.0, 1.0))

    # 4. Noise score: 1.0 is clean, 0.0 is very noisy
    noise_score = float(np.clip(1.0 - noise_estimate * 2.0, 0.0, 1.0))

    # Weighted combination: 30% exposure, 25% contrast, 35% sharpness, 10% noise
    quality = (
        0.30 * exposure_score
        + 0.25 * contrast_score
        + 0.35 * sharpness_score
        + 0.10 * noise_score
    )
    return float(np.clip(quality, 0.0, 1.0))


def classify_visibility_quality(quality_score: float) -> VisibilityQuality:
    """
    Maps continuous quality score [0.0, 1.0] to standard VisibilityQuality enum.
    """
    if quality_score >= 0.80:
        return VisibilityQuality.EXCELLENT
    elif quality_score >= 0.60:
        return VisibilityQuality.GOOD
    elif quality_score >= 0.40:
        return VisibilityQuality.FAIR
    elif quality_score >= 0.20:
        return VisibilityQuality.POOR
    else:
        return VisibilityQuality.INSUFFICIENT
