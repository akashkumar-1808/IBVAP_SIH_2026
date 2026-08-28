import pytest
import cv2
import numpy as np
from datetime import datetime, timezone

from worker.environment import (
    EnvironmentAnalyzer,
    EnvironmentConfig,
    EnvironmentState,
    LightingCondition,
    VisibilityQuality,
    InvalidFrameError,
    compute_luminance_stats,
    compute_rms_contrast,
    compute_sharpness_laplacian,
    estimate_image_noise,
)
from worker.ingestion import FramePacket


def _make_frame(image: np.ndarray, camera_id: str = "cam_env_01", frame_id: int = 0) -> FramePacket:
    h, w = image.shape[:2]
    return FramePacket(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp_utc=datetime.now(timezone.utc),
        image=image,
        width=w,
        height=h,
        source_type="test",
    )


def test_metrics_luminance_and_contrast():
    # Pure black image
    black_img = np.zeros((100, 100), dtype=np.uint8)
    mean_lum, std_lum, _, _ = compute_luminance_stats(black_img)
    assert mean_lum == 0.0
    assert std_lum == 0.0
    assert compute_rms_contrast(black_img) == 0.0

    # High contrast checkerboard
    checker = np.zeros((100, 100), dtype=np.uint8)
    checker[::2, ::2] = 255
    checker[1::2, 1::2] = 255
    mean_lum, std_lum, _, _ = compute_luminance_stats(checker)
    assert 0.45 <= mean_lum <= 0.55
    assert std_lum > 0.40
    assert compute_rms_contrast(checker) > 0.40


def test_metrics_sharpness_and_blur():
    # Sharp edge image
    sharp_img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(sharp_img, (50, 50), (150, 150), 255, -1)
    sharp_score = compute_sharpness_laplacian(sharp_img)

    # Blurred version
    blurred_img = cv2.GaussianBlur(sharp_img, (21, 21), 0)
    blurred_score = compute_sharpness_laplacian(blurred_img)

    assert sharp_score > blurred_score * 5.0


def test_metrics_noise_estimation():
    # Clean flat image
    clean_img = np.full((100, 100), 128, dtype=np.uint8)
    clean_noise = estimate_image_noise(clean_img)

    # Noisy image
    noisy_img = np.clip(clean_img.astype(np.int16) + np.random.randint(-30, 30, (100, 100)), 0, 255).astype(np.uint8)
    noisy_noise = estimate_image_noise(noisy_img)

    assert noisy_noise > clean_noise
    assert clean_noise < 0.01


def test_analyzer_day_and_night_lighting():
    analyzer = EnvironmentAnalyzer()

    # Bright daylight frame (mean ~ 180 / 255 = 0.70)
    day_img = np.full((240, 320, 3), 180, dtype=np.uint8)
    state_day = analyzer.analyze(_make_frame(day_img, camera_id="cam_day"))
    assert state_day.lighting == LightingCondition.DAY
    assert state_day.brightness > 0.60

    # Night frame (mean ~ 10 / 255 = 0.04)
    night_img = np.full((240, 320, 3), 10, dtype=np.uint8)
    state_night = analyzer.analyze(_make_frame(night_img, camera_id="cam_night"))
    assert state_night.lighting == LightingCondition.NIGHT
    assert state_night.brightness < 0.08


def test_analyzer_camera_isolation_and_get_state():
    analyzer = EnvironmentAnalyzer()

    img_a = np.full((240, 320, 3), 200, dtype=np.uint8)
    img_b = np.full((240, 320, 3), 20, dtype=np.uint8)

    analyzer.analyze(_make_frame(img_a, camera_id="cam_A"))
    analyzer.analyze(_make_frame(img_b, camera_id="cam_B"))

    state_a = analyzer.get_state("cam_A")
    state_b = analyzer.get_state("cam_B")

    assert state_a is not None
    assert state_b is not None
    assert state_a.lighting == LightingCondition.DAY
    assert state_b.lighting == LightingCondition.NIGHT


def test_analyzer_reset():
    analyzer = EnvironmentAnalyzer()
    img = np.full((240, 320, 3), 150, dtype=np.uint8)
    analyzer.analyze(_make_frame(img, camera_id="cam_reset_01"))
    assert analyzer.get_state("cam_reset_01") is not None

    analyzer.reset("cam_reset_01")
    assert analyzer.get_state("cam_reset_01") is None


def test_analyzer_invalid_inputs():
    analyzer = EnvironmentAnalyzer()

    with pytest.raises(InvalidFrameError):
        analyzer.analyze(None)

    empty_pkt = FramePacket(
        camera_id="cam_err",
        frame_id=0,
        timestamp_utc=datetime.now(timezone.utc),
        image=np.array([], dtype=np.uint8),
        width=0,
        height=0,
    )
    with pytest.raises(InvalidFrameError):
        analyzer.analyze(empty_pkt)
