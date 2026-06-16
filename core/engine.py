import os
import time
import numpy as np
import cv2
import torch
import mediapipe as mp
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from collections import deque
from scipy.optimize import linear_sum_assignment

from database.logger import DatabaseLogger
from core.zones import IntrusionZone
from ultralytics import YOLO
from core.notifier import Notifier

# Target Category Filtering
TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    15: "cat",
    16: "dog",
    56: "chair",
    67: "mobile phone",
    73: "laptop"
}

# ================= BYTE TRACK IMPLEMENTATION =================

class ByteTrackState:
    Tentative = 1
    Confirmed = 2
    Lost = 3

class ByteKalmanFilter:
    """Standard Kalman Filter for tracking bounding boxes in image space (x, y, a, h)."""
    def __init__(self):
        ndim, dt = 4, 1.0
        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt
        self._update_mat = np.eye(ndim, 2 * ndim)
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

    def initiate(self, measurement):
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

    def predict(self, mean, covariance):
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))
        mean = np.dot(self._motion_mat, mean)
        covariance = np.linalg.multi_dot((self._motion_mat, covariance, self._motion_mat.T)) + motion_cov
        return mean, covariance

    def project(self, mean, covariance):
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))
        mean = np.dot(self._update_mat, mean)
        covariance = np.linalg.multi_dot((self._update_mat, covariance, self._update_mat.T)) + innovation_cov
        return mean, covariance

    def update(self, mean, covariance, measurement):
        projected_mean, projected_cov = self.project(mean, covariance)
        kalman_gain = np.linalg.solve(projected_cov, np.dot(covariance, self._update_mat.T).T).T
        innovation = measurement - projected_mean
        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_covariance = covariance - np.linalg.multi_dot((kalman_gain, projected_cov, kalman_gain.T))
        return new_mean, new_covariance

class ByteTrack:
    """Represents a single track in ByteTrack."""
    def __init__(self, tlwh, score, class_id, track_id):
        self.track_id = track_id
        self.class_id = class_id
        self.score = score
        self.state = ByteTrackState.Tentative
        
        # Kalman filter variables
        self.mean = None
        self.covariance = None
        
        # convert tlwh to xyah
        self.tlwh = np.array(tlwh, dtype=np.float32)
        self.xyah = self.to_xyah(self.tlwh)
        
        self.age = 1
        self.time_since_update = 0
        self.hits = 1
        
        # History queue for visual gradient trailing trails (stores centers)
        self.history = deque(maxlen=30)
        center = (int(tlwh[0] + tlwh[2]/2), int(tlwh[1] + tlwh[3]/2))
        self.history.append(center)

    def to_xyah(self, tlwh):
        ret = tlwh.copy()
        ret[0] += ret[2] / 2
        ret[1] += ret[3] / 2
        ret[2] /= ret[3] + 1e-5
        return ret

    def to_tlwh(self):
        if self.mean is None:
            return self.tlwh
        ret = self.mean[:4].copy()
        ret[2] *= ret[3]
        ret[0] -= ret[2] / 2
        ret[1] -= ret[3] / 2
        return ret

    def to_tlbr(self):
        tlwh = self.to_tlwh()
        return np.array([tlwh[0], tlwh[1], tlwh[0] + tlwh[2], tlwh[1] + tlwh[3]], dtype=np.float32)

    def activate(self, kalman_filter, frame_id):
        self.mean, self.covariance = kalman_filter.initiate(self.xyah)
        self.time_since_update = 0
        self.state = ByteTrackState.Confirmed if self.hits >= 2 else ByteTrackState.Tentative

    def predict(self, kalman_filter):
        if self.state != ByteTrackState.Lost:
            self.mean, self.covariance = kalman_filter.predict(self.mean, self.covariance)
        self.time_since_update += 1
        self.age += 1

    def update(self, kalman_filter, new_track, frame_id):
        self.time_since_update = 0
        self.hits += 1
        self.score = new_track.score
        self.class_id = new_track.class_id
        
        new_xyah = self.to_xyah(new_track.tlwh)
        self.mean, self.covariance = kalman_filter.update(self.mean, self.covariance, new_xyah)
        self.state = ByteTrackState.Confirmed
        
        # Store center to history
        tlwh = self.to_tlwh()
        center = (int(tlwh[0] + tlwh[2]/2), int(tlwh[1] + tlwh[3]/2))
        self.history.append(center)

    def mark_lost(self):
        self.state = ByteTrackState.Lost

    def mark_removed(self):
        self.state = ByteTrackState.Lost # Treat removed as lost, cleaned up by tracker

class ByteTracker:
    def __init__(self, track_thresh=0.5, track_buffer=30, match_thresh=0.8):
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.kalman_filter = ByteKalmanFilter()
        
        self.tracked_stracks = []  # Confirmed tracks
        self.lost_stracks = []     # Lost tracks
        self.frame_id = 0
        self.max_id = 1

    def update(self, output_results):
        """
        output_results: list of dict containing {'box': [x1,y1,x2,y2], 'score': s, 'class_id': c}
        """
        self.frame_id += 1
        activated_stracks = []
        refind_stracks = []
        lost_stracks = []
        removed_stracks = []
        
        # Separate detections by threshold
        detections_high = []
        detections_low = []
        
        for res in output_results:
            box = res['box']
            tlwh = [box[0], box[1], box[2] - box[0], box[3] - box[1]]
            score = res['score']
            class_id = res['class_id']
            
            track_candidate = ByteTrack(tlwh, score, class_id, -1)
            
            if score >= self.track_thresh:
                detections_high.append(track_candidate)
            else:
                detections_low.append(track_candidate)

        # Predict current tracks
        unconfirmed = []
        tracked_stracks = []  # Confirmed active tracks
        
        for track in self.tracked_stracks:
            if track.state == ByteTrackState.Confirmed:
                tracked_stracks.append(track)
            else:
                unconfirmed.append(track)
                
        # Merge confirmed active tracks and lost tracks for prediction
        strack_pool = joint_stracks(tracked_stracks, self.lost_stracks)
        
        # Predict states
        for strack in strack_pool:
            strack.predict(self.kalman_filter)

        # --- First association: High-confidence detections and track pool ---
        matches, u_track, u_detection = linear_assignment_iou(strack_pool, detections_high, self.match_thresh)
        
        for itracked, idet in matches:
            track = strack_pool[itracked]
            det = detections_high[idet]
            if track.state == ByteTrackState.Confirmed:
                track.update(self.kalman_filter, det, self.frame_id)
                activated_stracks.append(track)
            else:
                # Refind lost track
                track.update(self.kalman_filter, det, self.frame_id)
                refind_stracks.append(track)

        # --- Second association: Low-confidence detections and remaining tracks ---
        # Match only with confirmed tracks that were not matched in Level 1
        r_tracked_stracks = [strack_pool[i] for i in u_track if strack_pool[i].state == ByteTrackState.Confirmed]
        matches_low, u_track_low, u_detection_low = linear_assignment_iou(r_tracked_stracks, detections_low, 0.5)
        
        for itracked, idet in matches_low:
            track = r_tracked_stracks[itracked]
            det = detections_low[idet]
            track.update(self.kalman_filter, det, self.frame_id)
            activated_stracks.append(track)

        # Handle lost/unmatched confirmed tracks
        for itracked in u_track_low:
            track = r_tracked_stracks[itracked]
            if track.state != ByteTrackState.Lost:
                track.mark_lost()
                lost_stracks.append(track)

        # --- Handle unconfirmed tracks: Match with remaining high-confidence detections ---
        unconfirmed_candidates = [detections_high[i] for i in u_detection]
        matches_unconf, u_unconf, u_detection_high = linear_assignment_iou(unconfirmed, unconfirmed_candidates, 0.7)
        
        for itracked, idet in matches_unconf:
            track = unconfirmed[itracked]
            det = unconfirmed_candidates[idet]
            track.update(self.kalman_filter, det, self.frame_id)
            activated_stracks.append(track)
            
        # Delete unconfirmed tracks that were not matched
        for itracked in u_unconf:
            track = unconfirmed[itracked]
            track.mark_removed()
            removed_stracks.append(track)

        # Spawn new tracks for unmatched high-confidence detections
        for idet in u_detection_high:
            det = unconfirmed_candidates[idet]
            if det.score < 0.6:  # Strict threshold for starting new tracks
                continue
            det.track_id = self.max_id
            self.max_id += 1
            det.activate(self.kalman_filter, self.frame_id)
            activated_stracks.append(det)

        # Clean up lost tracks that exceeded track_buffer age
        for track in self.lost_stracks:
            if self.frame_id - track.frame_id > self.track_buffer:
                track.mark_removed()
                removed_stracks.append(track)

        # Update active and lost tracks lists
        self.tracked_stracks = [t for t in self.tracked_stracks if t.state == ByteTrackState.Confirmed]
        self.tracked_stracks = joint_stracks(self.tracked_stracks, activated_stracks)
        self.tracked_stracks = joint_stracks(self.tracked_stracks, refind_stracks)
        
        self.lost_stracks = sub_stracks(self.lost_stracks, self.tracked_stracks)
        self.lost_stracks.extend(lost_stracks)
        self.lost_stracks = sub_stracks(self.lost_stracks, removed_stracks)
        
        self.tracked_stracks, self.lost_stracks = remove_duplicate_stracks(self.tracked_stracks, self.lost_stracks)
        
        # Assign current frame_id to tracks
        for track in self.tracked_stracks:
            track.frame_id = self.frame_id

        # Return list of active confirmed tracks
        return [t for t in self.tracked_stracks if t.state == ByteTrackState.Confirmed]

def joint_stracks(tlist_a, tlist_b):
    exists = {}
    dest = []
    for t in tlist_a:
        exists[t.track_id] = True
        dest.append(t)
    for t in tlist_b:
        if not exists.get(t.track_id, False):
            dest.append(t)
    return dest

def sub_stracks(tlist_a, tlist_b):
    exists = {t.track_id: True for t in tlist_b}
    return [t for t in tlist_a if not exists.get(t.track_id, False)]

def remove_duplicate_stracks(tlist_a, tlist_b):
    # Quick duplicate clean based on overlap
    # We can skip for simplicity or do simple spatial distance cleaning
    return tlist_a, tlist_b

def linear_assignment_iou(tracks, detections, threshold):
    if not tracks or not detections:
        return [], list(range(len(tracks))), list(range(len(detections)))
        
    cost_matrix = np.zeros((len(tracks), len(detections)), dtype=np.float32)
    for i, t in enumerate(tracks):
        tbox = t.to_tlbr()
        for j, d in enumerate(detections):
            dbox = d.to_tlbr()
            # IoU distance
            cost_matrix[i, j] = 1.0 - iou(tbox, dbox)
            
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    matches = []
    u_track = list(range(len(tracks)))
    u_detection = list(range(len(detections)))
    
    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] < threshold:
            matches.append((r, c))
            u_track.remove(r)
            u_detection.remove(c)
            
    return matches, u_track, u_detection

def iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / (union + 1e-5)

class SyntheticCapture:
    def isOpened(self):
        return True
    def read(self):
        return True, np.zeros((720, 1280, 3), dtype=np.uint8)
    def release(self):
        pass

def draw_glowing_hud_box(frame, x1, y1, x2, y2, color, label_lines=None, progress=1.0):
    """
    Renders a high-fidelity cyberpunk/HUD-style glowing bounding box.
    Features:
      - Double-layer neon borders (outer thick, inner sharp)
      - Dynamic, progressive corner brackets
      - Translucent dark obsidian label backplate cards
      - Left colored accent bars
    """
    h_f, w_f = frame.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w_f - 1, int(x2)), min(h_f - 1, int(y2))
    
    # 1. Double-layer neon border glow
    fade_color = (int(color[0] * 0.25), int(color[1] * 0.25), int(color[2] * 0.25))
    cv2.rectangle(frame, (x1, y1), (x2, y2), fade_color, 3, cv2.LINE_AA)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)
    
    # 2. Glowing corner brackets
    box_w, box_h = x2 - x1, y2 - y1
    corner_len = min(16, int(box_w * 0.25), int(box_h * 0.25))
    dx = int(corner_len + (box_w / 2 - corner_len) * progress)
    dy = int(corner_len + (box_h / 2 - corner_len) * progress)
    
    # Top Left
    cv2.line(frame, (x1, y1), (x1 + dx, y1), color, 2, cv2.LINE_AA)
    cv2.line(frame, (x1, y1), (x1, y1 + dy), color, 2, cv2.LINE_AA)
    # Top Right
    cv2.line(frame, (x2, y1), (x2 - dx, y1), color, 2, cv2.LINE_AA)
    cv2.line(frame, (x2, y1), (x2, y1 + dy), color, 2, cv2.LINE_AA)
    # Bottom Left
    cv2.line(frame, (x1, y2), (x1 + dx, y2), color, 2, cv2.LINE_AA)
    cv2.line(frame, (x1, y2), (x1, y2 - dy), color, 2, cv2.LINE_AA)
    # Bottom Right
    cv2.line(frame, (x2, y2), (x2 - dx, y2), color, 2, cv2.LINE_AA)
    cv2.line(frame, (x2, y2), (x2, y2 - dy), color, 2, cv2.LINE_AA)
    
    # 3. Label/Metadata Stack
    if label_lines:
        line_height = 13
        total_height = len(label_lines) * line_height
        
        y_offset = y2 + 6
        if y_offset + total_height > h_f - 10:
            y_offset = y1 - total_height - 6
            if y_offset < 10:
                y_offset = y1 + 15
                
        for line in label_lines:
            (t_w, t_h), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
            cv2.rectangle(frame, (x1, y_offset - t_h - 2), (x1 + t_w + 8, y_offset + 3), (24, 19, 14), -1)
            cv2.line(frame, (x1, y_offset - t_h - 2), (x1, y_offset + 3), color, 2, cv2.LINE_AA)
            cv2.putText(frame, line, (x1 + 6, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
            y_offset += line_height


class InferenceEngine(QThread):
    frame_ready = pyqtSignal(object, dict)  # Sends annotated frame and metadata payload
    status_msg = pyqtSignal(str)               # Status message updates
    telemetry_ready = pyqtSignal(float, float)  # Emits (inference_latency_ms, fps)

    def __init__(self, db_logger: DatabaseLogger):
        super().__init__()
        self.db = db_logger
        
        # Thread safety lock for drawings
        import threading
        self.canvas_lock = threading.Lock()
        
        # Framerate tracking
        self.current_fps = 30.0
        
        # Last cursor tracking for smoothing
        self.last_cursor = None
        
        # Engine configurations
        self.source_type = "webcam"  # "synthetic", "webcam", "file", "rtsp"
        self.source_path = "0"
        self.camera_backend = "auto"  # "auto", "msmf", "dshow"
        self.conf_threshold = 0.25
        
        # Toggles
        self.show_trails = True
        self.show_labels = True
        self.show_intrusion = True
        self.multi_camera_mode = False
        self.is_running = False
        self.is_paused = False
        
        # Intrusion Zone
        self.intrusion_zone = IntrusionZone()
        self.is_intrusion_alarm = False
        
        # Heatmap and tracking animations
        self.track_animations = {}
        self.heatmap_accum = None
        self.show_heatmap = False
        
        # Hardware Auto-Detect
        self.device = self._auto_detect_hardware()
        
        # Model and Tracker
        self.model = None
        self.tracker = None
        
        # Video Capture & Recording
        self.is_recording = False
        self.video_writer = None
        self.take_screenshot_flag = False
        self.screenshot_type = "annotated"
        
        # Behavior & Face analytics
        self.track_zone_timers = {}
        self.face_registry_profiles = []
        self.register_face_name = ""
        self.notified_alerts = set()
        
        # Folder structures
        import sys
        self.is_frozen = getattr(sys, 'frozen', False)
        if self.is_frozen:
            self.bundle_dir = sys._MEIPASS
            self.root_dir = os.path.dirname(sys.executable)
        else:
            self.bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.root_dir = self.bundle_dir
            
        self.recordings_dir = os.path.join(self.root_dir, "recordings")
        self.screenshots_dir = os.path.join(self.root_dir, "screenshots")
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

        # MediaPipe Tasks initialization
        self.hand_detector = None
        self.face_detector = None
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            
            hand_model_path = os.path.join(self.bundle_dir, "models", "hand_landmarker.task")
            if os.path.exists(hand_model_path):
                hand_base_options = python.BaseOptions(model_asset_path=hand_model_path)
                hand_options = vision.HandLandmarkerOptions(
                    base_options=hand_base_options,
                    num_hands=1,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.5
                )
                self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)
                
            face_model_path = os.path.join(self.bundle_dir, "models", "face_landmarker.task")
            if os.path.exists(face_model_path):
                face_base_options = python.BaseOptions(model_asset_path=face_model_path)
                face_options = vision.FaceLandmarkerOptions(
                    base_options=face_base_options,
                    num_faces=5,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5
                )
                self.face_detector = vision.FaceLandmarker.create_from_options(face_options)
        except Exception as e:
            print(f"[InferenceEngine] MediaPipe Tasks init failed: {e}")
            
        # Air Writing Canvas State
        self.air_writing_enabled = True  # ON by default — toggle via UI button
        self.draw_paths = []
        self.current_path = []
        self.cursor_point = None
        self.writing_mode = False
        self.brush_color = (0, 255, 0)
        self.brush_thickness = 4

    def _auto_detect_hardware(self) -> str:
        """Determines best acceleration available (CUDA, MPS, or CPU)."""
        if torch.cuda.is_available():
            # Check FP16 support
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _trigger_audio_beep(self):
        try:
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            pass

    def apply_settings(self, config):
        """Applies dynamic runtime configurations."""
        Notifier.configure(config)
        self.conf_threshold = config.get("conf_threshold", self.conf_threshold)
        self.show_trails = config.get("show_trails", self.show_trails)
        self.show_labels = config.get("show_labels", self.show_labels)
        self.show_intrusion = config.get("show_intrusion", self.show_intrusion)
        self.multi_camera_mode = config.get("multi_camera", self.multi_camera_mode)
        self.show_heatmap = config.get("show_heatmap", self.show_heatmap)
        self.brush_color = config.get("brush_color", self.brush_color)
        self.brush_thickness = config.get("brush_thickness", self.brush_thickness)
        self.register_face_name = config.get("register_face_name", self.register_face_name)
        if config.get("clear_canvas", False):
            with self.canvas_lock:
                self.draw_paths = []
                self.current_path = []
        
        # Trigger video source restart if modified
        new_src_type = config.get("source_type", self.source_type)
        new_src_path = str(config.get("source_path", self.source_path))
        new_backend = config.get("camera_backend", self.camera_backend)
        
        if (new_src_type != self.source_type or new_src_path != self.source_path or new_backend != self.camera_backend) and self.is_running:
            self.status_msg.emit("Re-routing video source...")
            self.source_type = new_src_type
            self.source_path = new_src_path
            self.camera_backend = new_backend
            # We signal loop to re-initialize camera capture stream
            self.restart_source_flag = True
        else:
            self.source_type = new_src_type
            self.source_path = new_src_path
            self.camera_backend = new_backend

    def trigger_screenshot(self, s_type="annotated"):
        self.take_screenshot_flag = True
        self.screenshot_type = s_type

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.status_msg.emit("MP4 Core Recording Started.")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.status_msg.emit("Recording Saved successfully.")

    def _load_yolo_model(self):
        if self.model is not None:
            return True
        
        # Bypass SSL verification checks globally for downloads in Python
        import ssl
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass

        # Try to load yolo11n.pt first
        try:
            self.status_msg.emit(f"Loading YOLO11 Core ({self.device.upper()})...")
            model_path = os.path.join(self.bundle_dir, "models", "yolo11n.pt")
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            self.model = YOLO(model_path)
            self.model.to(self.device)
            self.status_msg.emit(f"YOLO11 engine online ({self.device.upper()}).")
            return True
        except Exception as e:
            print(f"[Engine] YOLO11 load failed: {e}. Attempting fallback to local YOLOv8...")
            self.status_msg.emit("YOLO11 download/load failed. Loading local YOLOv8 fallback...")

        # Fallback to yolov8n.pt which is already local in models/
        try:
            model_path = os.path.join(self.bundle_dir, "models", "yolov8n.pt")
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                self.model.to(self.device)
                self.status_msg.emit(f"YOLOv8 fallback engine online ({self.device.upper()}).")
                return True
            else:
                self.status_msg.emit("YOLOv8 fallback model file not found.")
        except Exception as ex:
            print(f"[Engine] YOLOv8 fallback failed: {ex}")

        self.status_msg.emit("YOLO Init Failed. Falling back to synthetic source.")
        self.source_type = "synthetic"
        return False

    def run(self):
        try:
            self._run_loop()
        except Exception as fatal:
            self.status_msg.emit(f"[FATAL] Engine thread crashed: {fatal}")
            print(f"[Engine] FATAL unhandled exception in run(): {fatal}")
            import traceback
            traceback.print_exc()

    def _run_loop(self):
        self.is_running = True
        self.is_paused = False
        self.restart_source_flag = False
        self.tracker = ByteTracker(track_thresh=self.conf_threshold)

        # Initialize Face registry profiles
        self.face_registry_profiles = self.db.get_face_registry()

        # Initialize YOLO Model only if not synthetic
        if self.source_type != "synthetic":
            self._load_yolo_model()

        # Initialize Capture Stream
        cap = self._init_capture()
        sim_tick = 0
        loop_cnt = 0
        consecutive_drops = 0
        prev_time = time.time()
        
        while self.is_running:
            loop_cnt += 1
            if loop_cnt % 150 == 0:
                self.face_registry_profiles = self.db.get_face_registry()
            if self.restart_source_flag:
                self.restart_source_flag = False
                if cap:
                    cap.release()
                if self.source_type != "synthetic":
                    self._load_yolo_model()
                cap = self._init_capture()
                consecutive_drops = 0
                
            if self.is_paused:
                time.sleep(0.1)
                continue
                
            frame = None
            raw_frame = None
            yolo_results = []
            
            start_inference_time = time.time()
            
            # 1. Capture Frame & Detect
            if self.source_type == "synthetic":
                frame, yolo_results = self._generate_synthetic_frame(sim_tick)
                raw_frame = frame.copy()
                sim_tick += 1
                time.sleep(0.03)  # Maintain ~30 FPS
            else:
                if cap is None or not cap.isOpened():
                    self.status_msg.emit("Core Capture Offline. Re-initializing...")
                    time.sleep(1.0)
                    cap = self._init_capture()
                    consecutive_drops = 0
                    continue
                    
                ret, frame = cap.read()
                if not ret:
                    if self.source_type == "file":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop file
                        continue
                    else:
                        consecutive_drops += 1
                        self.status_msg.emit(f"Capture Frame Drop ({consecutive_drops}/5). Attempting Recovery...")
                        if consecutive_drops >= 5:
                            self.status_msg.emit("Persistent frame drops. Re-initializing capture device...")
                            if cap:
                                cap.release()
                            cap = None
                            consecutive_drops = 0
                            time.sleep(1.0)
                        else:
                            time.sleep(0.2)
                        continue
                
                # If frame is read successfully, reset drops
                consecutive_drops = 0
                
                # Flip webcam horizontally for natural mirrored view
                if self.source_type == "webcam":
                    frame = cv2.flip(frame, 1)
                
                raw_frame = frame.copy()
                
                # 2. YOLO Model Prediction
                try:
                    if self.model is None:
                        raise RuntimeError("YOLO model not loaded")
                    # Run FP16 inference on GPU
                    half_precision = (self.device == "cuda")
                    predict_results = self.model.predict(
                        source=frame,
                        conf=self.conf_threshold,
                        classes=None,  # None loads all 80 COCO categories dynamically
                        half=half_precision,
                        device=self.device,
                        verbose=False
                    )

                    if predict_results:
                        boxes = predict_results[0].boxes
                        for box in boxes:
                            xyxy = box.xyxy[0].cpu().numpy()
                            score = float(box.conf[0].cpu().numpy())
                            cls_id = int(box.cls[0].cpu().numpy())
                            label = self.model.names.get(cls_id, "unknown")

                            yolo_results.append({
                                'box': [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                                'score': score,
                                'class_id': label
                            })
                except Exception as e:
                    self.status_msg.emit(f"Model Inference Failure: {e}")

            # 3. Guard: skip this loop iteration if frame is None
            if frame is None:
                time.sleep(0.03)
                continue

            # 3. Process ByteTrack
            active_tracks = self.tracker.update(yolo_results)
            h, w, _ = frame.shape
            
            # Heatmap accumulation
            if self.show_heatmap:
                if self.heatmap_accum is None or self.heatmap_accum.shape[:2] != frame.shape[:2]:
                    self.heatmap_accum = np.zeros(frame.shape[:2], dtype=np.float32)
                
                self.heatmap_accum *= 0.98 # decay factor
                for track in active_tracks:
                    tlbr = track.to_tlbr().astype(int)
                    cx = int((tlbr[0] + tlbr[2]) // 2)
                    cy = int((tlbr[1] + tlbr[3]) // 2)
                    # Accumulate density within a radius of 30 pixels
                    cv2.circle(self.heatmap_accum, (cx, cy), 30, 0.5, -1)
            
            inference_latency = (time.time() - start_inference_time) * 1000.0
            
            # 4. Check Intrusion Zone & Log Events
            self.is_intrusion_alarm = False
            active_metadata = {}
            db_inserts = []
            
            for track in active_tracks:
                tlwh = track.to_tlwh()
                class_label = track.class_id
                
                # Check intrusion violation
                is_intruding = False
                if self.show_intrusion:
                    is_intruding = self.intrusion_zone.contains_bbox(tlwh)
                    if is_intruding:
                        self.is_intrusion_alarm = True
                        
                # 1. Behavior: Loitering Detection
                behavior = "normal"
                if is_intruding:
                    if track.track_id not in self.track_zone_timers:
                        self.track_zone_timers[track.track_id] = time.time()
                    elapsed = time.time() - self.track_zone_timers[track.track_id]
                    if elapsed > 10.0:
                        behavior = "loitering"
                else:
                    self.track_zone_timers.pop(track.track_id, None)
                    
                # 2. Behavior: Running Detection
                if len(track.history) >= 10:
                    p_old = track.history[-10]
                    p_new = track.history[-1]
                    dist = np.sqrt((p_new[0] - p_old[0])**2 + (p_new[1] - p_old[1])**2)
                    speed = dist / 10.0
                    if speed > 12.0:
                        behavior = "running"
                        
                active_metadata[track.track_id] = {
                    "bbox": tlwh.tolist(),
                    "class": class_label,
                    "confidence": float(track.score),
                    "intrusion": is_intruding,
                    "behavior": behavior,
                    "user_name": "Unknown"
                }

                # Trigger alerts
                # A. Intrusion Alert
                if is_intruding:
                    alert_key = f"intrusion_{track.track_id}"
                    if alert_key not in self.notified_alerts:
                        self.notified_alerts.add(alert_key)
                        alert_msg = f"Security Violation: Object ID {track.track_id} ({class_label}) entered the restricted intrusion zone."
                        Notifier.send_telegram(alert_msg)
                        Notifier.send_email(f"Intrusion Alert (ID: {track.track_id})", alert_msg)
                        self._trigger_audio_beep()
                
                # B. Loitering Alert
                if behavior == "loitering":
                    alert_key = f"loitering_{track.track_id}"
                    if alert_key not in self.notified_alerts:
                        self.notified_alerts.add(alert_key)
                        alert_msg = f"Loitering Violation: Object ID {track.track_id} ({class_label}) has loitered in the intrusion zone for over 10 seconds."
                        Notifier.send_telegram(alert_msg)
                        Notifier.send_email(f"Loitering Alert (ID: {track.track_id})", alert_msg)
                        self._trigger_audio_beep()
                
                # C. Running Alert
                if behavior == "running":
                    alert_key = f"running_{track.track_id}"
                    if alert_key not in self.notified_alerts:
                        self.notified_alerts.add(alert_key)
                        alert_msg = f"Behavior Alert: Object ID {track.track_id} ({class_label}) is running at high speed."
                        Notifier.send_telegram(alert_msg)
                        Notifier.send_email(f"Running Behavior Alert (ID: {track.track_id})", alert_msg)
                        self._trigger_audio_beep()
                
            # Clean up notified alerts for tracks that are no longer active
            active_track_ids = {track.track_id for track in active_tracks}
            keys_to_remove = []
            for key in list(self.notified_alerts):
                try:
                    parts = key.split('_')
                    if len(parts) >= 2:
                        tid = int(parts[-1])
                        if tid not in active_track_ids:
                            keys_to_remove.append(key)
                except ValueError:
                    pass
            for key in keys_to_remove:
                self.notified_alerts.discard(key)
                
            # Process MediaPipe models on live camera
            annotated_frame = frame.copy()
            if self.source_type != "synthetic":
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self._process_mood_detection(frame_rgb, annotated_frame, active_metadata)
                if self.air_writing_enabled:
                    self._process_hand_writing(frame_rgb, annotated_frame)
                else:
                    self._render_drawings(annotated_frame)
            else:
                self._render_drawings(annotated_frame)
                
            # Now build db_inserts, using custom mood/behavior-augmented labels for persons
            for track in active_tracks:
                if track.hits == 2 or (track.hits % 30 == 0):
                    meta = active_metadata.get(track.track_id)
                    logged_label = track.class_id
                    if meta and logged_label == "person":
                        annotations = []
                        if "user_name" in meta and meta["user_name"] != "Unknown":
                            annotations.append(meta["user_name"].lower())
                        if "behavior" in meta and meta["behavior"] != "normal":
                            annotations.append(meta["behavior"])
                        if "mood" in meta:
                            annotations.append(meta["mood"].lower())
                        
                        if annotations:
                            logged_label = f"person ({' - '.join(annotations)})"
                    db_inserts.append((logged_label, track.track_id, float(track.score)))

            # Batch push to SQLite Logger Queue
            for c_lbl, t_id, score in db_inserts:
                self.db.log_event(c_lbl, t_id, score)

            # Compute System Framerate
            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time + 1e-6)
            prev_time = curr_time
            
            # Smooth current FPS running average
            self.current_fps = 0.9 * self.current_fps + 0.1 * fps
            
            # Emit live latency & FPS signals
            self.telemetry_ready.emit(inference_latency, fps)

            # 5. Visual Render Overlay Layouts
            
            # Heatmap Superimpose Blend
            if self.show_heatmap and self.heatmap_accum is not None:
                heatmap_norm = np.clip(self.heatmap_accum * 255.0, 0, 255).astype(np.uint8)
                heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
                # Blend heatmap color map onto the annotated frame at 0.3 opacity
                cv2.addWeighted(heatmap_color, 0.3, annotated_frame, 0.7, 0, annotated_frame)
                
            # A. Draw Intrusion Zone overlay
            if self.show_intrusion:
                self.intrusion_zone.draw_zone(annotated_frame, self.is_intrusion_alarm)
                
            # B. Draw Tracks and Gradient Trails
            self._render_tracks(annotated_frame, active_tracks, active_metadata)
            
            # C. Multi-Camera Grid Wall Composition
            if self.multi_camera_mode:
                h_half, w_half = h // 2, w // 2
                
                f1 = cv2.resize(annotated_frame, (w_half, h_half))
                cv2.putText(f1, "FEED 01 // PRIMARY OPTICAL", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 229, 255), 1, cv2.LINE_AA)
                
                # Feed 2: Synthetic Simulator
                f2_raw, _ = self._generate_synthetic_frame(sim_tick)
                f2 = cv2.resize(f2_raw, (w_half, h_half))
                cv2.putText(f2, "FEED 02 // SYNTHETIC TARGETING", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 229, 255), 1, cv2.LINE_AA)
                
                # Feed 3: Thermal representation
                f3_raw = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)
                f3_colored = cv2.applyColorMap(f3_raw, cv2.COLORMAP_JET)
                f3 = cv2.resize(f3_colored, (w_half, h_half))
                cv2.putText(f3, "FEED 03 // THERMAL SPECTRUM", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 229, 255), 1, cv2.LINE_AA)
                
                # Feed 4: System Vector Radar Scan
                f4 = np.zeros((h_half, w_half, 3), dtype=np.uint8)
                f4[:, :] = [12, 16, 24] # Dark Slate Grey
                sweep_x = int((sim_tick * 4) % w_half)
                cv2.line(f4, (sweep_x, 0), (sweep_x, h_half), (0, 229, 255), 1)
                for gx in range(0, w_half, 40):
                    cv2.line(f4, (gx, 0), (gx, h_half), (30, 41, 59), 1)
                for gy in range(0, h_half, 40):
                    cv2.line(f4, (0, gy), (w_half, gy), (30, 41, 59), 1)
                cv2.putText(f4, "FEED 04 // DIAGNOSTIC RADAR", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 229, 255), 1, cv2.LINE_AA)
                cv2.putText(f4, f"RADAR SCAN POS: {sweep_x}", (15, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1, cv2.LINE_AA)
                
                top_row = np.hstack((f1, f2))
                bottom_row = np.hstack((f3, f4))
                annotated_frame = np.vstack((top_row, bottom_row))
            
            # Save screenshots
            if self.take_screenshot_flag:
                self.take_screenshot_flag = False
                self._save_image(raw_frame if self.screenshot_type == "raw" else annotated_frame)
                
            # Write video frames
            if self.is_recording:
                self._write_frame_to_video(annotated_frame)
                
            # Emit Frame Signal
            payload = {
                "active_objects": active_metadata,
                "fps": fps,
                "latency_ms": inference_latency,
                "intrusion_alert": self.is_intrusion_alarm
            }
            self.frame_ready.emit(annotated_frame, payload)

        # Release resource assets
        if cap:
            cap.release()
        if self.video_writer:
            self.video_writer.release()

    def _init_capture(self):
        """Initializes OpenCV Video Capture based on source settings.
        
        Enhanced with multi-index and multi-backend fallback for maximum
        compatibility when launched from different environments (IDE, batch file,
        double-click, etc.).
        """
        if self.source_type == "synthetic":
            return SyntheticCapture()
        elif self.source_type == "webcam":
            try:
                preferred_idx = int(self.source_path)
            except ValueError:
                preferred_idx = 0

            # Build ordered list of (camera_index, backend) tuples to try.
            # We try preferred idx first across all backends, then fallback indices.
            candidate_indices = [preferred_idx]
            for alt in range(4):
                if alt != preferred_idx:
                    candidate_indices.append(alt)

            # Backend preference order: CAP_DSHOW (fastest on Windows),
            # then default (auto), then CAP_MSMF as last resort.
            dshow_val = getattr(cv2, "CAP_DSHOW", 700)
            msmf_val  = getattr(cv2, "CAP_MSMF",  1400)

            for cam_idx in candidate_indices:
                if self.camera_backend == "dshow":
                    backends = [(cam_idx, dshow_val, f"CAP_DSHOW@{cam_idx}")]
                elif self.camera_backend == "msmf":
                    backends = [(cam_idx, msmf_val, f"CAP_MSMF@{cam_idx}")]
                else:  # auto
                    backends = [
                        (cam_idx, None,      f"DEFAULT@{cam_idx}"),
                        (cam_idx, msmf_val,  f"CAP_MSMF@{cam_idx}"),
                        (cam_idx, dshow_val, f"CAP_DSHOW@{cam_idx}"),
                    ]
                for cam_val, api_val, backend_name in backends:
                    try:
                        self.status_msg.emit(f"Trying camera {backend_name}...")
                        if api_val is not None:
                            cap = cv2.VideoCapture(cam_val, api_val)
                        else:
                            cap = cv2.VideoCapture(cam_val)
                        if cap.isOpened():
                            # Verify we can actually read multiple frames (some cameras
                            # report isOpened=True but fail on subsequent reads).
                            success = True
                            for _ in range(3):
                                ret, test_frame = cap.read()
                                if not ret or test_frame is None:
                                    success = False
                                    break
                                time.sleep(0.01)
                            
                            if success:
                                self.source_path = str(cam_idx)
                                self.status_msg.emit(
                                    f"Camera online: index={cam_idx} backend={backend_name}."
                                )
                                return cap
                            else:
                                cap.release()
                    except Exception as e:
                        print(f"[Engine] Camera probe failed ({backend_name}): {e}")


        elif self.source_type in ["file", "rtsp"]:
            cap = cv2.VideoCapture(self.source_path)
            if cap.isOpened():
                self.status_msg.emit(f"Stream {self.source_path} Connected successfully.")
                return cap

        self.status_msg.emit(
            "No camera found. Falling back to Synthetic Simulator. "
            "Check that your webcam is plugged in and not used by another app."
        )
        self.source_type = "synthetic"
        return SyntheticCapture()

    def _render_tracks(self, frame, tracks, metadata):
        """Draws bounding boxes, classification labels, and trail vectors."""
        for track in tracks:
            meta = metadata.get(track.track_id)
            if not meta:
                continue
                
            tlbr = track.to_tlbr().astype(int)
            w = tlbr[2] - tlbr[0]
            h = tlbr[3] - tlbr[1]
            if w <= 0 or h <= 0:
                continue
                
            is_intruding = meta["intrusion"]
            
            # Neon Crimson for Intrusion Zone violators, Electric Cyan/Blue for normal states
            color = (60, 0, 255) if is_intruding else (255, 229, 0)
            
            # A. Draw Gradient Trailing Trails
            if self.show_trails and len(track.history) > 1:
                hist_len = len(track.history)
                for i in range(1, hist_len):
                    pt1 = track.history[i-1]
                    pt2 = track.history[i]
                    
                    # Calculate fading alpha/thickness based on index
                    alpha_factor = i / hist_len
                    thickness = int(np.clip(alpha_factor * 3, 1, 3))
                    
                    # Draw fading trail segment
                    cv2.line(frame, pt1, pt2, color, thickness, lineType=cv2.LINE_AA)

            # Initialize track-specific animation state if not exists
            if track.track_id not in self.track_animations:
                self.track_animations[track.track_id] = {
                    'progress': 0.0,
                    'conf': 0.1
                }
                
            anim = self.track_animations[track.track_id]
            # Speed of bounding box drawing
            anim['progress'] = min(1.0, anim['progress'] + 0.08)
            # Speed of confidence count-up
            target_conf = float(meta['confidence'])
            anim['conf'] = min(target_conf, anim['conf'] + (target_conf - anim['conf']) * 0.15)

            # B. Draw Bounding Box HUD Outline & Labels
            label_lines = None
            if self.show_labels:
                label_lines = [f"{meta['class'].upper()} ID: {track.track_id}"]
                conf_val = int(anim['conf'] * 100)
                if 'user_name' in meta and meta['user_name'] != 'Unknown':
                    label_lines.append(f"USER: {meta['user_name'].upper()} [{conf_val}%]")
                else:
                    label_lines.append(f"CONFIDENCE: {conf_val}%")
                    
                if 'behavior' in meta and meta['behavior'] != 'normal':
                    label_lines.append(f"BEHAVIOR: {meta['behavior'].upper()}")
                    
                if 'mood' in meta:
                    label_lines.append(f"MOOD: {meta['mood'].upper()}")

            draw_glowing_hud_box(
                frame, 
                tlbr[0], tlbr[1], tlbr[2], tlbr[3], 
                color, 
                label_lines, 
                anim['progress']
            )

        # Cleanup cached animation profiles for tracks no longer active
        active_ids = {track.track_id for track in tracks}
        for tid in list(self.track_animations.keys()):
            if tid not in active_ids:
                self.track_animations.pop(tid, None)

    def _draw_hud_cursor(self, frame, center, color, writing=False):
        """Draws a premium cybernetic reticle cursor on the screen."""
        cx, cy = center
        # Center dot
        cv2.circle(frame, (cx, cy), 2, color, -1)
        # Outer ring
        cv2.circle(frame, (cx, cy), 10, color, 1, lineType=cv2.LINE_AA)
        
        # Crosshair lines
        cv2.line(frame, (cx - 15, cy), (cx - 5, cy), color, 1)
        cv2.line(frame, (cx + 5, cy), (cx + 15, cy), color, 1)
        cv2.line(frame, (cx, cy - 15), (cx, cy - 5), color, 1)
        cv2.line(frame, (cx, cy + 5), (cx, cy + 15), color, 1)
        
        # Cursor Mode Label Text
        label = "WRITE" if writing else "HOVER"
        cv2.putText(frame, label, (cx + 18, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

    def _process_hand_writing(self, frame_rgb, annotated_frame):
        if self.hand_detector is None:
            return
        # Run MediaPipe Hands via Tasks API
        h, w, _ = annotated_frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        results = self.hand_detector.detect(mp_image)
        
        self.cursor_point = None
        
        if results.hand_landmarks:
            for hand_landmarks in results.hand_landmarks:
                landmarks = hand_landmarks
                
                # Robust 3D distance check relative to wrist (landmark 0)
                def is_finger_extended(pip_idx, tip_idx):
                    p_wrist = landmarks[0]
                    p_pip = landmarks[pip_idx]
                    p_tip = landmarks[tip_idx]
                    d_tip = np.sqrt((p_tip.x - p_wrist.x)**2 + (p_tip.y - p_wrist.y)**2 + (p_tip.z - p_wrist.z)**2)
                    d_pip = np.sqrt((p_pip.x - p_wrist.x)**2 + (p_pip.y - p_wrist.y)**2 + (p_pip.z - p_wrist.z)**2)
                    return d_tip > d_pip
                
                index_tip = landmarks[8]
                index_extended = is_finger_extended(6, 8)
                middle_extended = is_finger_extended(10, 12)
                ring_extended = is_finger_extended(14, 16)
                
                # Coordinates of index tip
                ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                
                # Apply smoothing filter (exponential moving average) to reduce jitter
                if self.last_cursor is not None:
                    dist = np.sqrt((ix - self.last_cursor[0])**2 + (iy - self.last_cursor[1])**2)
                    if dist < 150: # Smooth only small jitters, don't lag on big jumps
                        ix = int(self.last_cursor[0] * 0.75 + ix * 0.25)
                        iy = int(self.last_cursor[1] * 0.75 + iy * 0.25)
                        
                self.last_cursor = (ix, iy)
                self.cursor_point = (ix, iy)
                
                # Determine mode using robust three-finger system:
                # 1. Writing Mode: Index extended, Middle closed
                if index_extended and not middle_extended:
                    self.writing_mode = True
                    with self.canvas_lock:
                        self.current_path.append((ix, iy))
                    # Draw a high-tech red reticle cursor
                    self._draw_hud_cursor(annotated_frame, (ix, iy), (0, 0, 255), writing=True)
                else:
                    self.writing_mode = False
                    with self.canvas_lock:
                        if self.current_path:
                            self.draw_paths.append(self.current_path)
                            self.current_path = []
                    
                    # 2. Clear Mode: Index, Middle, and Ring all extended (open hand)
                    if index_extended and middle_extended and ring_extended:
                        with self.canvas_lock:
                            self.draw_paths = []
                            self.current_path = []
                        cv2.putText(annotated_frame, "CLEAR CANVAS", (w - 220, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                    else:
                        # 3. Hover Mode: Index and Middle extended, Ring closed
                        # Draw a high-tech blue reticle cursor
                        self._draw_hud_cursor(annotated_frame, (ix, iy), (255, 0, 0), writing=False)
                        
                # Draw hand skeleton (premium cyan/white neon)
                connections = [
                    (0, 1), (1, 2), (2, 3), (3, 4),
                    (0, 5), (5, 6), (6, 7), (7, 8),
                    (9, 10), (10, 11), (11, 12),
                    (13, 14), (14, 15), (15, 16),
                    (0, 17), (17, 18), (18, 19), (19, 20),
                    (5, 9), (9, 13), (13, 17)
                ]
                for start_idx, end_idx in connections:
                    lm_start = landmarks[start_idx]
                    lm_end = landmarks[end_idx]
                    pt1 = (int(lm_start.x * w), int(lm_start.y * h))
                    pt2 = (int(lm_end.x * w), int(lm_end.y * h))
                    cv2.line(annotated_frame, pt1, pt2, (255, 229, 0), 2, lineType=cv2.LINE_AA)
                for lm in landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(annotated_frame, (cx, cy), 3, (255, 255, 255), -1)
        else:
            self.writing_mode = False
            self.last_cursor = None
            with self.canvas_lock:
                if self.current_path:
                    self.draw_paths.append(self.current_path)
                    self.current_path = []
                    
        self._render_drawings(annotated_frame)

    def _render_drawings(self, annotated_frame):
        # Draw all existing paths on annotated_frame
        with self.canvas_lock:
            for path in self.draw_paths:
                for i in range(1, len(path)):
                    cv2.line(annotated_frame, path[i-1], path[i], self.brush_color, self.brush_thickness, lineType=cv2.LINE_AA)

            # Draw current path
            for i in range(1, len(self.current_path)):
                cv2.line(annotated_frame, self.current_path[i-1], self.current_path[i], self.brush_color, self.brush_thickness, lineType=cv2.LINE_AA)

        # Only show HUD instruction when air writing is active
        if self.air_writing_enabled:
            cv2.rectangle(annotated_frame, (20, 20), (520, 50), (22, 27, 38), -1)
            cv2.rectangle(annotated_frame, (20, 20), (520, 50), (0, 229, 255), 1)
            cv2.putText(
                annotated_frame,
                "AIR WRITING ON // INDEX UP=WRITE  INDEX+MID=HOVER  OPEN HAND=CLEAR",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 229, 255),
                1,
                cv2.LINE_AA
            )

    def _process_mood_detection(self, frame_rgb, annotated_frame, active_metadata):
        if self.face_detector is None:
            return
        # Run Face Mesh via Tasks API
        h, w, _ = annotated_frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        results = self.face_detector.detect(mp_image)
        
        if results.face_landmarks:
            for face_landmarks in results.face_landmarks:
                landmarks = face_landmarks
                
                # 1. Extract Key Coordinates
                m_left = landmarks[61]
                m_right = landmarks[291]
                m_top = landmarks[0]
                m_bottom = landmarks[17]
                eye_left_outer = landmarks[33]
                eye_right_outer = landmarks[263]
                eb_left = landmarks[70]
                eb_right = landmarks[300]
                eye_left_top = landmarks[159]
                eye_left_bottom = landmarks[145]
                eye_right_top = landmarks[386]
                eye_right_bottom = landmarks[374]
                
                # 2. Compute Distances
                face_width = np.sqrt((eye_left_outer.x - eye_right_outer.x)**2 + (eye_left_outer.y - eye_right_outer.y)**2)
                if face_width < 1e-5:
                    face_width = 1.0
                    
                mouth_width = np.sqrt((m_left.x - m_right.x)**2 + (m_left.y - m_right.y)**2) / face_width
                mouth_open = np.sqrt((m_top.x - m_bottom.x)**2 + (m_top.y - m_bottom.y)**2) / face_width
                
                left_corner_rel_y = (m_left.y - m_top.y) / face_width
                right_corner_rel_y = (m_right.y - m_top.y) / face_width
                corners_avg_y = (left_corner_rel_y + right_corner_rel_y) / 2.0
                
                eb_left_dist = np.abs(eb_left.y - eye_left_top.y) / face_width
                eb_right_dist = np.abs(eb_right.y - eye_right_top.y) / face_width
                eb_avg_dist = (eb_left_dist + eb_right_dist) / 2.0
                
                # 3. Classify Mood
                mood = "Neutral"
                
                if mouth_width > 0.45 and corners_avg_y < 0.14:
                    mood = "Happy"
                elif corners_avg_y > 0.18:
                    mood = "Sad"
                elif mouth_open > 0.15 and eb_avg_dist > 0.22:
                    mood = "Surprised"
                elif eb_avg_dist < 0.16:
                    mood = "Angry"
                
                # Find face bounding box
                xs = [lm.x for lm in landmarks]
                ys = [lm.y for lm in landmarks]
                min_x, max_x = int(min(xs) * w), int(max(xs) * w)
                min_y, max_y = int(min(ys) * h), int(max(ys) * h)
                
                # Draw facial landmarks (subtle dot grid)
                for idx in [33, 263, 61, 291, 0, 17, 70, 300, 159, 145, 386, 374]:
                    lm = landmarks[idx]
                    cv2.circle(annotated_frame, (int(lm.x * w), int(lm.y * h)), 2, (0, 229, 255), -1)
                
                color_map = {
                    "Happy": (16, 185, 129),   # Emerald Green
                    "Sad": (59, 130, 246),     # Blue
                    "Surprised": (245, 158, 11), # Orange
                    "Angry": (60, 0, 255),     # Crimson Red
                    "Neutral": (0, 229, 255)   # Cyan
                }
                color = color_map.get(mood, (0, 229, 255))
                
                # 4. Face Recognition Matching
                nose = landmarks[4]
                ref_w = np.sqrt((landmarks[33].x - landmarks[263].x)**2 + (landmarks[33].y - landmarks[263].y)**2)
                if ref_w < 1e-5:
                    ref_w = 1.0
                
                key_indices = [33, 263, 61, 291, 159, 386, 0, 17, 70, 300]
                descriptor = []
                for idx in key_indices:
                    lm = landmarks[idx]
                    dist = np.sqrt((lm.x - nose.x)**2 + (lm.y - nose.y)**2) / ref_w
                    descriptor.append(dist)
                    
                matched_name = "Unknown"
                min_diff = 0.25
                for profile in self.face_registry_profiles:
                    reg_descriptor = profile["landmarks"]
                    diff = np.sqrt(sum((a - b)**2 for a, b in zip(descriptor, reg_descriptor)))
                    if diff < min_diff:
                        min_diff = diff
                        matched_name = profile["name"]
                        
                # Enroll current face if requested
                if self.register_face_name:
                    self.db.register_face(self.register_face_name, descriptor)
                    self.register_face_name = ""
                    self.face_registry_profiles = self.db.get_face_registry()
                    
                # Draw box around face and labels
                label_lines = [
                    f"USER: {matched_name.upper()}",
                    f"MOOD: {mood.upper()}"
                ]
                draw_glowing_hud_box(annotated_frame, min_x, min_y, max_x, max_y, color, label_lines)

                # Map face mood and user_name to the tracked person
                face_center_x = (min_x + max_x) / 2.0
                face_center_y = (min_y + max_y) / 2.0
                for track_id, info in active_metadata.items():
                    bbox = info["bbox"]
                    tx, ty, tw, th = bbox
                    if tx <= face_center_x <= tx + tw and ty <= face_center_y <= ty + th:
                        info["mood"] = mood
                        info["user_name"] = matched_name

    def _generate_synthetic_frame(self, tick):
        """Generates a high-tech synthetic surveillance frame with moving shapes."""
        h, w = 720, 1280
        # Dark tech background with radar lines
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = [15, 23, 42]  # Dark Slate Blue (#0f172a)
        
        # Grid lines
        for x in range(0, w, 80):
            cv2.line(frame, (x, 0), (x, h), (30, 41, 59), 1)
        for y in range(0, h, 80):
            cv2.line(frame, (0, y), (w, y), (30, 41, 59), 1)
            
        # Draw circular grid in the center
        cv2.circle(frame, (w//2, h//2), 250, (30, 41, 59), 1)
        cv2.circle(frame, (w//2, h//2), 150, (30, 41, 59), 1)
        cv2.circle(frame, (w//2, h//2), 50, (30, 41, 59), 1)
        
        # Simulate simulated moving objects
        # 1. Person: moving in a circle
        angle = tick * 0.02
        p1_x = int(w//2 + 200 * np.cos(angle))
        p1_y = int(h//2 + 150 * np.sin(angle))
        p1_w, p1_h = 45, 120
        cv2.ellipse(frame, (p1_x, p1_y), (p1_w//2, p1_h//2), 0, 0, 360, (59, 130, 246), -1) # Blue fill
        
        # 2. Car: moving from left to right
        car_x = (tick * 8) % (w + 200) - 100
        car_y = 520
        car_w, car_h = 160, 80
        cv2.rectangle(frame, (car_x - car_w//2, car_y - car_h//2), (car_x + car_w//2, car_y + car_h//2), (16, 185, 129), -1) # Emerald fill
        
        # 3. Dog: following the person with some offset
        d_x = int(p1_x + 60 * np.cos(angle + np.pi/4))
        d_y = int(p1_y + 60 * np.sin(angle + np.pi/4) + 30)
        d_w, d_h = 50, 40
        cv2.rectangle(frame, (d_x - d_w//2, d_y - d_h//2), (d_x + d_w//2, d_y + d_h//2), (245, 158, 11), -1) # Orange fill
        
        # Packaging simulated Detections
        # Add random noise to make tracking realistic
        noise = lambda max_val: np.random.randint(-3, 4)
        
        yolo_results = [
            {
                'box': [float(p1_x - p1_w//2 + noise(3)), float(p1_y - p1_h//2 + noise(3)), float(p1_x + p1_w//2 + noise(3)), float(p1_y + p1_h//2 + noise(3))],
                'score': 0.94 + 0.05 * np.random.rand(),
                'class_id': "person"
            },
            {
                'box': [float(car_x - car_w//2 + noise(3)), float(car_y - car_h//2 + noise(3)), float(car_x + car_w//2 + noise(3)), float(car_y + car_h//2 + noise(3))],
                'score': 0.96 + 0.03 * np.random.rand(),
                'class_id': "car"
            }
        ]
        
        # Dog only visible 80% of the time (simulates occlusion/missed detection)
        if tick % 10 != 0:
            yolo_results.append({
                'box': [float(d_x - d_w//2 + noise(3)), float(d_y - d_h//2 + noise(3)), float(d_x + d_w//2 + noise(3)), float(d_y + d_h//2 + noise(3))],
                'score': 0.82 + 0.1 * np.random.rand(),
                'class_id': "dog"
            })
            
        return frame, yolo_results

    def _save_image(self, frame):
        filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        cv2.imwrite(filepath, frame)
        self.status_msg.emit(f"Snapshot Saved: {filename}")

    def _write_frame_to_video(self, frame):
        h, w, _ = frame.shape
        if self.video_writer is None:
            filename = f"surveillance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = os.path.join(self.recordings_dir, filename)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            # Use dynamic current FPS of the engine (clamped to realistic values)
            rec_fps = max(1.0, min(60.0, self.current_fps))
            self.video_writer = cv2.VideoWriter(filepath, fourcc, rec_fps, (w, h))
        self.video_writer.write(frame)
