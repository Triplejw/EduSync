"""
Vision-based Head Pose Estimation for Attention Monitoring

ECE Core Component - Computer Vision Techniques:
- MediaPipe Face Mesh (2D face landmarks)
- Generic 3D face model mapping
- cv2.solvePnP for pose estimation
- Euler angles (yaw, pitch, roll) for attention scoring
- Moving Average filter for temporal smoothing (reduces jitter/false positives)

Runs on CPU only to leave GPU free for Llama-3.

Literature References for Threshold Selection:
----------------------------------------------
1. Attention Thresholds (Yaw ±20°, Pitch ±15°):
   - Murphy-Chutorian, E., & Trivedi, M.M. (2009). "Head Pose Estimation in Computer
     Vision: A Survey". IEEE Transactions on Pattern Analysis and Machine Intelligence.
   - Looking away horizontally >20° typically indicates attention shift from screen.

   - Whitehill, J., et al. (2014). "The Faces of Engagement: Automatic Recognition of
     Student Engagement from Facial Expressions". IEEE Trans. Affective Computing.
   - Pitch >15° suggests looking at something else (phone, notes) or disengagement.

2. Moving Average Smoothing (Buffer Size 10):
   - Sariyanidi, E., et al. (2015). "Automatic Analysis of Facial Affect: A Survey
     of Registration, Representation, and Recognition". IEEE TPAMI.
   - Temporal smoothing reduces false positives from momentary glances while
     preserving detection of sustained distraction.
   - At 0.5Hz capture rate, 10 frames = 20 second window for stable classification.
"""

import base64
import time
from collections import defaultdict
from dataclasses import dataclass, field

import cv2
import numpy as np
import mediapipe as mp

# Import centralized config (with fallback for standalone testing)
try:
    from config import vision_config
    YAW_THRESHOLD = vision_config.yaw_threshold
    PITCH_THRESHOLD = vision_config.pitch_threshold
    MA_BUFFER_SIZE = vision_config.ma_buffer_size
    MA_BUFFER_TTL_SEC = vision_config.ma_buffer_ttl_sec
except ImportError:
    # Fallback defaults for standalone testing
    YAW_THRESHOLD = 20.0
    PITCH_THRESHOLD = 15.0
    MA_BUFFER_SIZE = 10
    MA_BUFFER_TTL_SEC = 300.0

# MediaPipe face mesh landmark indices for head pose
# See: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
NOSE_TIP = 1
CHIN = 152
LEFT_EYE_LEFT = 33
RIGHT_EYE_RIGHT = 263
LEFT_MOUTH = 61
RIGHT_MOUTH = 291

# Generic 3D face model (approximate, in mm) for solvePnP
# Order matches the 2D landmarks we extract
FACE_3D_MODEL = np.array([
    (0.0, 0.0, 0.0),           # Nose tip
    (0.0, -330.0, -65.0),      # Chin
    (-225.0, 170.0, -135.0),   # Left eye left corner
    (225.0, 170.0, -135.0),    # Right eye right corner
    (-150.0, -150.0, -125.0),  # Left mouth corner
    (150.0, -150.0, -125.0),   # Right mouth corner
], dtype=np.float64)

LANDMARK_INDICES = [NOSE_TIP, CHIN, LEFT_EYE_LEFT, RIGHT_EYE_RIGHT, LEFT_MOUTH, RIGHT_MOUTH]


@dataclass
class _StudentBuffer:
    """Per-student ring buffer for yaw and pitch values."""

    yaw_buf: list = field(default_factory=list)
    pitch_buf: list = field(default_factory=list)
    last_access: float = field(default_factory=time.monotonic)

    def push(self, yaw: float, pitch: float) -> None:
        self.last_access = time.monotonic()
        self.yaw_buf.append(yaw)
        self.pitch_buf.append(pitch)
        # Keep last N values
        if len(self.yaw_buf) > MA_BUFFER_SIZE:
            self.yaw_buf = self.yaw_buf[-MA_BUFFER_SIZE:]
        if len(self.pitch_buf) > MA_BUFFER_SIZE:
            self.pitch_buf = self.pitch_buf[-MA_BUFFER_SIZE:]


class HeadPoseSmoother:
    """
    Moving Average filter for head pose angles.

    Stores the last N frames of yaw and pitch per student. Thresholds are applied
    to the averaged values rather than raw values to reduce false positives from
    single-frame noise.

    Viva/Presentation explanation:
    "Head pose angles from MediaPipe can be noisy frame-to-frame. We apply a
    Moving Average filter over the last 10 frames of yaw and pitch. The smoothed
    values are compared to thresholds (|yaw| > 20° or |pitch| > 15°) to classify
    focus vs distraction. This reduces false positives from transient head
    movements while preserving the ability to detect sustained distraction."
    """

    def __init__(self, buffer_size: int = MA_BUFFER_SIZE, ttl_sec: float = MA_BUFFER_TTL_SEC):
        self._buffers: dict[str, _StudentBuffer] = defaultdict(_StudentBuffer)
        self._buffer_size = buffer_size
        self._ttl_sec = ttl_sec

    def _evict_stale(self) -> None:
        """Remove buffers not accessed in ttl_sec."""
        now = time.monotonic()
        stale = [k for k, v in self._buffers.items() if now - v.last_access > self._ttl_sec]
        for k in stale:
            del self._buffers[k]

    def update(self, yaw: float, pitch: float, student_id: str) -> dict:
        """
        Add raw angles, compute moving average, apply thresholds.

        Returns:
            Dict with yaw_avg, pitch_avg, attention_score, raw_yaw, raw_pitch.
        """
        self._evict_stale()
        buf = self._buffers[student_id]
        buf.push(yaw, pitch)

        n = len(buf.yaw_buf)
        yaw_avg = sum(buf.yaw_buf) / n if n else yaw
        pitch_avg = sum(buf.pitch_buf) / n if n else pitch

        if abs(yaw_avg) > YAW_THRESHOLD or abs(pitch_avg) > PITCH_THRESHOLD:
            attention_score = 0
        else:
            attention_score = 100

        return {
            "yaw_avg": round(yaw_avg, 2),
            "pitch_avg": round(pitch_avg, 2),
            "attention_score": attention_score,
            "raw_yaw": round(yaw, 2),
            "raw_pitch": round(pitch, 2),
        }


# Module-level singleton for per-request use
_head_pose_smoother = HeadPoseSmoother()


def _rotation_vector_to_euler(rvec: np.ndarray) -> tuple[float, float, float]:
    """Convert OpenCV rotation vector to Euler angles (yaw, pitch, roll) in degrees."""
    rmat, _ = cv2.Rodrigues(rvec)
    # Extract Euler angles from rotation matrix
    # Convention: yaw (Y), pitch (X), roll (Z)
    sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
    singular = sy < 1e-6
    if not singular:
        yaw = np.degrees(np.arctan2(rmat[1, 0], rmat[0, 0]))
        pitch = np.degrees(np.arctan2(-rmat[2, 0], sy))
        roll = np.degrees(np.arctan2(rmat[2, 1], rmat[2, 2]))
    else:
        yaw = np.degrees(np.arctan2(-rmat[1, 2], rmat[1, 1]))
        pitch = np.degrees(np.arctan2(-rmat[2, 0], sy))
        roll = 0.0
    return float(yaw), float(pitch), float(roll)


def estimate_pose(image_input: str | bytes, student_id: str | None = None) -> dict:
    """
    Estimate head pose from an image.

    Args:
        image_input: Base64-encoded image string or raw bytes
        student_id: Optional student identifier. When provided, applies Moving Average
            smoothing over the last N frames before threshold check.

    Returns:
        {"yaw": float, "pitch": float, "roll": float, "attention_score": int, ...}
        attention_score: 100 if focused (within thresholds), 0 if distracted or no face
        When student_id is provided, yaw/pitch are smoothed values; raw_yaw/raw_pitch
        are also included for logging.
    """
    # Decode image
    if isinstance(image_input, str):
        img_bytes = base64.b64decode(image_input)
    else:
        img_bytes = image_input
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "attention_score": 0}

    h, w, _ = img.shape
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        min_detection_confidence=0.5,
        refine_landmarks=True,
    ) as face_mesh:
        results = face_mesh.process(img_rgb)
        if not results.multi_face_landmarks:
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "attention_score": 0}

        landmarks = results.multi_face_landmarks[0]
        # Convert normalized coords to pixel coords
        points_2d = []
        for idx in LANDMARK_INDICES:
            lm = landmarks.landmark[idx]
            x = int(lm.x * w)
            y = int(lm.y * h)
            points_2d.append([x, y])
        points_2d = np.array(points_2d, dtype=np.float64)

    # Camera matrix (approximate for typical phone camera)
    focal_length = w
    cam_center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, cam_center[0]],
        [0, focal_length, cam_center[1]],
        [0, 0, 1],
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))

    success, rvec, tvec = cv2.solvePnP(
        FACE_3D_MODEL,
        points_2d,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not success:
        return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "attention_score": 0}

    yaw, pitch, roll = _rotation_vector_to_euler(rvec)
    roll_rounded = round(roll, 2)

    if student_id:
        # Use Moving Average smoothing; apply threshold to averaged values
        smoothed = _head_pose_smoother.update(yaw, pitch, student_id)
        return {
            "yaw": smoothed["yaw_avg"],
            "pitch": smoothed["pitch_avg"],
            "roll": roll_rounded,
            "attention_score": smoothed["attention_score"],
            "raw_yaw": smoothed["raw_yaw"],
            "raw_pitch": smoothed["raw_pitch"],
        }
    # No smoothing: apply threshold directly to raw values
    if abs(yaw) > YAW_THRESHOLD or abs(pitch) > PITCH_THRESHOLD:
        attention_score = 0
    else:
        attention_score = 100
    return {
        "yaw": round(yaw, 2),
        "pitch": round(pitch, 2),
        "roll": roll_rounded,
        "attention_score": attention_score,
    }
