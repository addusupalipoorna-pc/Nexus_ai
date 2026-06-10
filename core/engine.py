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

# ================= AI INFERENCE ENGINE WORKER =================

class InferenceEngine(QThread):
    frame_ready = pyqtSignal(object, dict)  # Sends annotated frame and metadata payload
    status_msg = pyqtSignal(str)               # Status message updates
    telemetry_ready = pyqtSignal(float, float)  # Emits (inference_latency_ms, fps)

    def __init__(self, db_logger: DatabaseLogger):
        super().__init__()
        self.db = db_logger
        
        # Engine configurations
        self.source_type = "synthetic"  # "synthetic", "webcam", "file", "rtsp"
        self.source_path = "0"
        self.conf_threshold = 0.25
        
        # Toggles
        self.show_trails = True
        self.show_labels = True
        self.show_intrusion = True
        self.is_running = False
        self.is_paused = False
        
        # Intrusion Zone
        self.intrusion_zone = IntrusionZone()
        self.is_intrusion_alarm = False
        
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
        
        # Folder structures
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.recordings_dir = os.path.join(self.root_dir, "recordings")
        self.screenshots_dir = os.path.join(self.root_dir, "screenshots")
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

        # MediaPipe Hands and Face Mesh initialization
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Air Writing Canvas State
        self.draw_paths = []
        self.current_path = []
        self.cursor_point = None
        self.writing_mode = False

    def _auto_detect_hardware(self) -> str:
        """Determines best acceleration available (CUDA, MPS, or CPU)."""
        if torch.cuda.is_available():
            # Check FP16 support
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def apply_settings(self, config):
        """Applies dynamic runtime configurations."""
        self.conf_threshold = config.get("conf_threshold", self.conf_threshold)
        self.show_trails = config.get("show_trails", self.show_trails)
        self.show_labels = config.get("show_labels", self.show_labels)
        self.show_intrusion = config.get("show_intrusion", self.show_intrusion)
        
        # Trigger video source restart if modified
        new_src_type = config.get("source_type", self.source_type)
        new_src_path = str(config.get("source_path", self.source_path))
        
        if (new_src_type != self.source_type or new_src_path != self.source_path) and self.is_running:
            self.status_msg.emit("Re-routing video source...")
            self.source_type = new_src_type
            self.source_path = new_src_path
            # We signal loop to re-initialize camera capture stream
            self.restart_source_flag = True
        else:
            self.source_type = new_src_type
            self.source_path = new_src_path

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
        try:
            self.status_msg.emit(f"Loading YOLO Core ({self.device.upper()})...")
            model_path = os.path.join(self.root_dir, "models", "yolov8n.pt")
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            self.model = YOLO(model_path)
            self.model.to(self.device)
            self.status_msg.emit(f"YOLO engine online ({self.device.upper()}).")
            return True
        except Exception as e:
            self.status_msg.emit(f"YOLO Init Failed: {e}. Falling back to synthetic source.")
            self.source_type = "synthetic"
            return False

    def run(self):
        self.is_running = True
        self.is_paused = False
        self.restart_source_flag = False
        self.tracker = ByteTracker(track_thresh=self.conf_threshold)
        
        # Initialize YOLO Model only if not synthetic
        if self.source_type != "synthetic":
            self._load_yolo_model()

        # Initialize Capture Stream
        cap = self._init_capture()
        sim_tick = 0
        prev_time = time.time()
        
        while self.is_running:
            if self.restart_source_flag:
                self.restart_source_flag = False
                if cap:
                    cap.release()
                if self.source_type != "synthetic":
                    self._load_yolo_model()
                cap = self._init_capture()
                
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
                    continue
                    
                ret, frame = cap.read()
                if not ret:
                    if self.source_type == "file":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop file
                        continue
                    else:
                        self.status_msg.emit("Capture Frame Drop. Attempting Recovery...")
                        time.sleep(0.5)
                        continue
                
                raw_frame = frame.copy()
                
                # 2. YOLO Model Prediction
                try:
                    # Run FP16 inference on GPU
                    half_precision = (self.device == "cuda")
                    predict_results = self.model.predict(
                        source=frame,
                        conf=self.conf_threshold,
                        classes=list(TARGET_CLASSES.keys()),
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
                            label = TARGET_CLASSES.get(cls_id, "unknown")
                            
                            yolo_results.append({
                                'box': [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                                'score': score,
                                'class_id': label
                            })
                except Exception as e:
                    self.status_msg.emit(f"Model Inference Failure: {e}")

            # 3. Process ByteTrack
            active_tracks = self.tracker.update(yolo_results)
            
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
                        
                active_metadata[track.track_id] = {
                    "bbox": tlwh.tolist(),
                    "class": class_label,
                    "confidence": float(track.score),
                    "intrusion": is_intruding
                }
                
            # Process MediaPipe models on live camera
            annotated_frame = frame.copy()
            if self.source_type != "synthetic":
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self._process_mood_detection(frame_rgb, annotated_frame, active_metadata)
                self._process_hand_writing(frame_rgb, annotated_frame)
                
            # Now build db_inserts, using custom mood-augmented labels for persons
            for track in active_tracks:
                if track.hits == 2 or (track.hits % 30 == 0):
                    meta = active_metadata.get(track.track_id)
                    logged_label = track.class_id
                    if meta and "mood" in meta and logged_label == "person":
                        logged_label = f"person ({meta['mood'].lower()})"
                    db_inserts.append((logged_label, track.track_id, float(track.score)))

            # Batch push to SQLite Logger Queue
            for c_lbl, t_id, score in db_inserts:
                self.db.log_event(c_lbl, t_id, score)

            # Compute System Framerate
            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time + 1e-6)
            prev_time = curr_time
            
            # Emit live latency & FPS signals
            self.telemetry_ready.emit(inference_latency, fps)

            # 5. Visual Render Overlay Layouts
            
            # A. Draw Intrusion Zone overlay
            if self.show_intrusion:
                self.intrusion_zone.draw_zone(annotated_frame, self.is_intrusion_alarm)
                
            # B. Draw Tracks and Gradient Trails
            self._render_tracks(annotated_frame, active_tracks, active_metadata)
            
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
        """Initializes OpenCV Video Capture based on source settings."""
        if self.source_type == "synthetic":
            return SyntheticCapture()
        elif self.source_type == "webcam":
            try:
                idx = int(self.source_path)
            except ValueError:
                idx = 0
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                self.status_msg.emit(f"Webcam {idx} Connected successfully.")
                return cap
        elif self.source_type in ["file", "rtsp"]:
            cap = cv2.VideoCapture(self.source_path)
            if cap.isOpened():
                self.status_msg.emit(f"Stream {self.source_path} Connected successfully.")
                return cap
                
        self.status_msg.emit("Failed to open video source. Falling back to Synthetic Simulator.")
        self.source_type = "synthetic"
        return SyntheticCapture()

    def _render_tracks(self, frame, tracks, metadata):
        """Draws bounding boxes, classification labels, and trail vectors."""
        for track in tracks:
            meta = metadata.get(track.track_id)
            if not meta:
                continue
                
            tlbr = track.to_tlbr().astype(int)
            is_intruding = meta["intrusion"]
            
            # Neon Crimson for Intrusion Zone violators, Electric Cyan for normal states
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

            # B. Draw Bounding Box HUD Outline
            cv2.rectangle(frame, (tlbr[0], tlbr[1]), (tlbr[2], tlbr[3]), color, 2)
            
            # Corner HUD highlights
            corner_len = min(20, int((tlbr[2]-tlbr[0])*0.2))
            # Corners outline
            cv2.line(frame, (tlbr[0], tlbr[1]), (tlbr[0] + corner_len, tlbr[1]), color, 4)
            cv2.line(frame, (tlbr[0], tlbr[1]), (tlbr[0], tlbr[1] + corner_len), color, 4)
            cv2.line(frame, (tlbr[2], tlbr[1]), (tlbr[2] - corner_len, tlbr[1]), color, 4)
            cv2.line(frame, (tlbr[2], tlbr[1]), (tlbr[2], tlbr[1] + corner_len), color, 4)
            cv2.line(frame, (tlbr[0], tlbr[3]), (tlbr[0] + corner_len, tlbr[3]), color, 4)
            cv2.line(frame, (tlbr[0], tlbr[3]), (tlbr[0], tlbr[3] - corner_len), color, 4)
            cv2.line(frame, (tlbr[2], tlbr[3]), (tlbr[2] - corner_len, tlbr[3]), color, 4)
            cv2.line(frame, (tlbr[2], tlbr[3]), (tlbr[2], tlbr[3] - corner_len), color, 4)

            # C. Draw labels on screen
            if self.show_labels:
                label_text = f"{meta['class'].upper()} ID: {track.track_id} [{int(meta['confidence']*100)}%]"
                (t_w, t_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                
                # Draw filled banner tag
                cv2.rectangle(frame, (tlbr[0], tlbr[1] - t_h - 10), (tlbr[0] + t_w + 10, tlbr[1]), color, -1)
                cv2.putText(frame, label_text, (tlbr[0] + 5, tlbr[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    def _process_hand_writing(self, frame_rgb, annotated_frame):
        # Run MediaPipe Hands
        h, w, _ = annotated_frame.shape
        results = self.hands.process(frame_rgb)
        
        self.cursor_point = None
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                landmarks = hand_landmarks.landmark
                
                # Check if index finger is extended
                index_tip = landmarks[8]
                index_pip = landmarks[6]
                index_extended = index_tip.y < index_pip.y
                
                # Check if middle finger is extended
                middle_tip = landmarks[12]
                middle_pip = landmarks[10]
                middle_extended = middle_tip.y < middle_pip.y
                
                # Check if ring finger and pinky are extended
                ring_extended = landmarks[16].y < landmarks[14].y
                pinky_extended = landmarks[20].y < landmarks[18].y
                
                # Coordinates of index tip
                ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                self.cursor_point = (ix, iy)
                
                # Determine mode:
                # 1. Writing Mode: Only Index Finger is extended, middle and others are closed.
                if index_extended and not middle_extended and not ring_extended and not pinky_extended:
                    self.writing_mode = True
                    self.current_path.append((ix, iy))
                    # Draw a red circle around the index tip as cursor
                    cv2.circle(annotated_frame, (ix, iy), 8, (0, 0, 255), -1)
                else:
                    self.writing_mode = False
                    if self.current_path:
                        self.draw_paths.append(self.current_path)
                        self.current_path = []
                    
                    # 2. Clear Mode: All fingers extended (open hand)
                    if index_extended and middle_extended and ring_extended and pinky_extended:
                        self.draw_paths = []
                        self.current_path = []
                        cv2.putText(annotated_frame, "CLEAR CANVAS", (w - 220, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                    else:
                        # Draw a blue circle to show hover cursor
                        cv2.circle(annotated_frame, (ix, iy), 6, (255, 0, 0), -1)
                        
                # Draw hand skeleton (premium cyan/white neon)
                mp_draw = mp.solutions.drawing_utils
                mp_draw.draw_landmarks(
                    annotated_frame, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=(255, 229, 0), thickness=2, circle_radius=2), # Cyan outline
                    mp_draw.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=1) # White connections
                )
        else:
            self.writing_mode = False
            if self.current_path:
                self.draw_paths.append(self.current_path)
                self.current_path = []
                
        # Draw all existing paths on annotated_frame
        for path in self.draw_paths:
            for i in range(1, len(path)):
                cv2.line(annotated_frame, path[i-1], path[i], (0, 255, 0), 4, lineType=cv2.LINE_AA)
                
        # Draw current path
        for i in range(1, len(self.current_path)):
            cv2.line(annotated_frame, self.current_path[i-1], self.current_path[i], (0, 255, 0), 4, lineType=cv2.LINE_AA)

        # Draw HUD writing instructions
        cv2.rectangle(annotated_frame, (20, 20), (520, 50), (22, 27, 38), -1)
        cv2.rectangle(annotated_frame, (20, 20), (520, 50), (0, 229, 255), 1)
        cv2.putText(
            annotated_frame, 
            "AIR WRITING ACTIVE // INDEX UP = WRITE, OPEN HAND = CLEAR", 
            (30, 40), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.4, 
            (0, 229, 255), 
            1, 
            cv2.LINE_AA
        )

    def _process_mood_detection(self, frame_rgb, annotated_frame, active_metadata):
        # Run Face Mesh
        h, w, _ = annotated_frame.shape
        results = self.face_mesh.process(frame_rgb)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                landmarks = face_landmarks.landmark
                
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
                
                # Draw box around face
                cv2.rectangle(annotated_frame, (min_x, min_y), (max_x, max_y), color, 1)
                
                label_text = f"MOOD: {mood.upper()}"
                (t_w, t_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(annotated_frame, (min_x, min_y - t_h - 6), (min_x + t_w + 10, min_y), color, -1)
                cv2.putText(annotated_frame, label_text, (min_x + 5, min_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
                
                # Map face mood to the tracked person
                face_center_x = (min_x + max_x) / 2.0
                face_center_y = (min_y + max_y) / 2.0
                for track_id, info in active_metadata.items():
                    bbox = info["bbox"]
                    tx, ty, tw, th = bbox
                    if tx <= face_center_x <= tx + tw and ty <= face_center_y <= ty + th:
                        info["mood"] = mood

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
            self.video_writer = cv2.VideoWriter(filepath, fourcc, 30.0, (w, h))
        self.video_writer.write(frame)
