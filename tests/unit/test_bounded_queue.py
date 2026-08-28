import pytest
import numpy as np
from datetime import datetime, timezone
from worker.ingestion import BoundedFrameQueue, FramePacket, QueueClosedError


def _make_dummy_frame(frame_id: int, camera_id: str = "cam_01") -> FramePacket:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    return FramePacket(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp_utc=datetime.now(timezone.utc),
        image=img,
        width=100,
        height=100,
        source_type="file",
    )


def test_queue_initialization():
    q = BoundedFrameQueue(max_size=5)
    assert q.max_size == 5
    assert q.size() == 0
    assert q.is_empty() is True
    assert q.is_closed is False


def test_queue_invalid_max_size():
    with pytest.raises(ValueError):
        BoundedFrameQueue(max_size=0)


def test_queue_put_and_get():
    q = BoundedFrameQueue(max_size=5)
    f0 = _make_dummy_frame(0)
    f1 = _make_dummy_frame(1)

    assert q.put(f0) is True
    assert q.put(f1) is True
    assert q.size() == 2

    out0 = q.get(timeout=0.1)
    assert out0 is not None
    assert out0.frame_id == 0

    out1 = q.get(timeout=0.1)
    assert out1 is not None
    assert out1.frame_id == 1

    assert q.is_empty() is True


def test_queue_drop_oldest_policy():
    """
    CRITICAL TEST:
    Verify that when queue capacity (e.g. 3) is exceeded,
    the OLDEST frames are dropped, total_dropped is incremented,
    and the newest frames are retained in order.
    """
    q = BoundedFrameQueue(max_size=3)

    # Insert 5 frames (0, 1, 2, 3, 4) into capacity 3
    q.put(_make_dummy_frame(0))
    q.put(_make_dummy_frame(1))
    q.put(_make_dummy_frame(2))

    # Next two should trigger drops of frame 0 and frame 1
    assert q.put(_make_dummy_frame(3)) is False  # False means drop occurred
    assert q.put(_make_dummy_frame(4)) is False

    stats = q.stats()
    assert stats["current_size"] == 3
    assert stats["total_inserted"] == 5
    assert stats["total_dropped"] == 2

    # Remaining frames should be 2, 3, 4
    f_first = q.get(timeout=0.1)
    f_second = q.get(timeout=0.1)
    f_third = q.get(timeout=0.1)

    assert f_first.frame_id == 2
    assert f_second.frame_id == 3
    assert f_third.frame_id == 4
    assert q.is_empty() is True


def test_queue_close_behavior():
    q = BoundedFrameQueue(max_size=5)
    q.put(_make_dummy_frame(0))
    q.close()
    assert q.is_closed is True

    # Existing items can still be drained
    item = q.get(timeout=0.1)
    assert item is not None
    assert item.frame_id == 0

    # Once empty, get returns None immediately
    assert q.get(timeout=0.1) is None

    # Put on closed queue raises QueueClosedError
    with pytest.raises(QueueClosedError):
        q.put(_make_dummy_frame(1))
