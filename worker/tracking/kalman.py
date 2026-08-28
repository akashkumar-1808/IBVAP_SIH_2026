import numpy as np


class KalmanBoxTracker:
    """
    Kalman Filter representation for 2D bounding box tracking.
    State space: [center_x, center_y, aspect_ratio, height, vx, vy, va, vh]
    Measurement space: [center_x, center_y, aspect_ratio, height]
    """

    def __init__(self, bbox_xyxy: np.ndarray):
        # 8-dim state vector
        self._motion_mat = np.eye(8, 8)
        for i in range(4):
            self._motion_mat[i, i + 4] = 1.0

        self._update_mat = np.eye(4, 8)

        # Standard deviation factors for process and measurement noise
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

        self.mean, self.covariance = self._init_state(bbox_xyxy)

    def _convert_bbox_to_z(self, bbox_xyxy: np.ndarray) -> np.ndarray:
        """Converts [x1, y1, x2, y2] to measurement [cx, cy, aspect_ratio, height]."""
        w = max(1e-4, bbox_xyxy[2] - bbox_xyxy[0])
        h = max(1e-4, bbox_xyxy[3] - bbox_xyxy[1])
        cx = bbox_xyxy[0] + w / 2.0
        cy = bbox_xyxy[1] + h / 2.0
        a = w / h
        return np.array([cx, cy, a, h])

    def _convert_x_to_bbox(self, state_mean: np.ndarray) -> np.ndarray:
        """Converts state [cx, cy, a, h, ...] back to [x1, y1, x2, y2]."""
        cx, cy, a, h = state_mean[:4]
        w = max(1e-4, a * h)
        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        x2 = cx + w / 2.0
        y2 = cy + h / 2.0
        return np.array([x1, y1, x2, y2])

    def _init_state(self, bbox_xyxy: np.ndarray):
        measurement = self._convert_bbox_to_z(bbox_xyxy)
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(self) -> np.ndarray:
        """Runs the Kalman predict step and returns predicted [x1, y1, x2, y2]."""
        std_pos = [
            self._std_weight_position * self.mean[3],
            self._std_weight_position * self.mean[3],
            1e-2,
            self._std_weight_position * self.mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * self.mean[3],
            self._std_weight_velocity * self.mean[3],
            1e-5,
            self._std_weight_velocity * self.mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))

        self.mean = np.dot(self._motion_mat, self.mean)
        self.covariance = np.linalg.multi_dot([self._motion_mat, self.covariance, self._motion_mat.T]) + motion_cov
        return self._convert_x_to_bbox(self.mean)

    def update(self, bbox_xyxy: np.ndarray) -> np.ndarray:
        """Runs the Kalman update step with a new measurement [x1, y1, x2, y2]."""
        measurement = self._convert_bbox_to_z(bbox_xyxy)
        std = [
            self._std_weight_position * self.mean[3],
            self._std_weight_position * self.mean[3],
            1e-1,
            self._std_weight_position * self.mean[3],
        ]
        measurement_cov = np.diag(np.square(std))

        projected_mean = np.dot(self._update_mat, self.mean)
        projected_cov = np.linalg.multi_dot([self._update_mat, self.covariance, self._update_mat.T]) + measurement_cov

        kalman_gain = np.linalg.multi_dot([self.covariance, self._update_mat.T, np.linalg.inv(projected_cov)])
        innovation = measurement - projected_mean

        self.mean = self.mean + np.dot(kalman_gain, innovation)
        self.covariance = self.covariance - np.linalg.multi_dot([kalman_gain, projected_cov, kalman_gain.T])

        return self._convert_x_to_bbox(self.mean)

    @property
    def current_bbox(self) -> np.ndarray:
        return self._convert_x_to_bbox(self.mean)
