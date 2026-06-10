import os
import time
import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime

from .tracker import Tracker, Detection
from .detector import ObjectDetector, TARGET_CLASSES
from database.db_manager import DBManager

class CameraThread(QThread):
    # Signals to send data back to the UI thread
    frame_ready = pyqtSignal(np.ndarray)  # Sends the annotated frame
    stats_ready = pyqtSignal(dict)        # Sends live statistics dictionary
    status_msg = pyqtSignal(str)          # Sends status messages to the status bar

    def __init__(self, db_manager: DBManager):
        super().__init__()
        self.db = db_manager
        
        # Default settings
        self.source = "webcam"  # "synthetic", "webcam", or path to file
        self.camera_idx = 0
        self.video_path = ""
        
        self.is_running = False
        self.is_paused = False
        
        # Detector and Tracker
        self.detector = None
        self.tracker = None
        self.conf_threshold = 0.25
        
        # Visual settings
        self.show_trails = True
        self.show_heatmap = False
        self.heatmap_opacity = 0.4
        
        # Recording & Screenshots
        self.is_recording = False
        self.video_writer = None
        self.take_screenshot_flag = False
        self.screenshot_type = "annotated"  # "raw" or "annotated"
        
        # Folders
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.recordings_dir = os.path.join(self.root_dir, "recordings")
        self.screenshots_dir = os.path.join(self.root_dir, "screenshots")
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Heatmap grid (downsampled resolution)
        self.heatmap_grid = None
        self.heatmap_size = (72, 128)  # 720x1280 downsampled by 10
        
        # Stats tracking
        self.fps = 0.0
        
        # Alerts settings
        self.alert_person_threshold = 5
        self.alert_vehicle_detect = False
        self.alert_unknown_detect = False
        
    def set_source(self, source_type, path_or_idx=0):
        self.source = source_type
        if source_type == "webcam":
            self.camera_idx = int(path_or_idx)
        elif source_type == "file":
            self.video_path = str(path_or_idx)

    def set_detector_conf(self, conf):
        self.conf_threshold = conf
        if self.detector:
            self.detector.set_conf_threshold(conf)

    def trigger_screenshot(self, s_type="annotated"):
        self.take_screenshot_flag = True
        self.screenshot_type = s_type

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.status_msg.emit("Recording started.")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.status_msg.emit("Recording saved.")

    def run(self):
        self.is_running = True
        self.is_paused = False
        
        # Reset tracker and heatmap
        self.tracker = Tracker()
        self.heatmap_grid = np.zeros(self.heatmap_size, dtype=np.float32)
        
        # Try to load detector for real sources, fallback to synthetic if fails
        if self.source != "synthetic":
            try:
                self.status_msg.emit("Initializing YOLOv8 model...")
                self.detector = ObjectDetector(conf_threshold=self.conf_threshold)
                self.status_msg.emit("YOLOv8 initialized.")
            except Exception as e:
                self.status_msg.emit(f"Failed to load YOLO model: {e}. Falling back to synthetic source.")
                self.source = "synthetic"

        # Initialize video capture if not synthetic
        cap = None
        if self.source == "webcam":
            cap = cv2.VideoCapture(self.camera_idx)
            if not cap.isOpened():
                self.status_msg.emit("Failed to open webcam. Falling back to synthetic stream.")
                self.source = "synthetic"
        elif self.source == "file":
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.status_msg.emit("Failed to open video file. Falling back to synthetic stream.")
                self.source = "synthetic"

        # Frame timing
        prev_time = time.time()
        
        # Synthetic simulation variables
        sim_tick = 0
        
        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue
                
            frame = None
            raw_frame = None
            detections = []
            
            # 1. Acquire Frame & Detections
            if self.source == "synthetic":
                frame, detections = self._generate_synthetic_frame(sim_tick)
                raw_frame = frame.copy()
                sim_tick += 1
                time.sleep(0.03)  # Maintain ~30 FPS
            else:
                ret, frame = cap.read()
                if not ret:
                    if self.source == "file":
                        # Loop video file
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        self.status_msg.emit("Camera feed disconnected.")
                        time.sleep(0.5)
                        continue
                
                raw_frame = frame.copy()
                # Run YOLO detector
                try:
                    detections = self.detector.detect(frame)
                except Exception as e:
                    self.status_msg.emit(f"Inference error: {e}")
                    detections = []

            # 2. Run Tracker (Deep SORT)
            # Extracted features are matched inside tracker
            self.tracker.predict()
            self.tracker.update(detections, frame)
            
            # 3. Log detections to DB and count stats
            active_counts = {}
            total_active = 0
            log_batch = []
            
            for track in self.tracker.tracks:
                if track.state == 2:  # Confirmed
                    total_active += 1
                    active_counts[track.class_id] = active_counts.get(track.class_id, 0) + 1
                    
                    # Accumulate for heatmap (center of bbox mapped to downsampled grid)
                    tlwh = track.to_tlwh()
                    cx = int((tlwh[0] + tlwh[2]/2) / frame.shape[1] * self.heatmap_size[1])
                    cy = int((tlwh[1] + tlwh[3]/2) / frame.shape[0] * self.heatmap_size[0])
                    
                    if 0 <= cx < self.heatmap_size[1] and 0 <= cy < self.heatmap_size[0]:
                        self.heatmap_grid[cy, cx] += 1
                        
                    # Queue logging database update (skip if redundant in consecutive frames)
                    # We log to DB once every 30 hits to avoid SQLite performance issues, 
                    # or when track is brand new (hits == 3)
                    if track.hits == 3 or (track.hits % 30 == 0):
                        log_batch.append((track.class_id, track.track_id, track.confidence))

            if log_batch:
                self.db.log_detections_batch(log_batch)

            # Calculate FPS
            curr_time = time.time()
            self.fps = 1.0 / (curr_time - prev_time + 1e-6)
            prev_time = curr_time
            
            # 4. Drawing & Post-Processing
            annotated_frame = frame.copy()
            self._draw_overlay(annotated_frame)
            
            # Save screenshots
            if self.take_screenshot_flag:
                self.take_screenshot_flag = False
                self._save_screenshot(raw_frame if self.screenshot_type == "raw" else annotated_frame)

            # Manage Video Recording
            if self.is_recording:
                self._write_video_frame(annotated_frame)

            # 5. Emit Frame and Stats
            self.frame_ready.emit(annotated_frame)
            
            # Compute stats dict
            avg_conf = np.mean([t.confidence for t in self.tracker.tracks if t.state == 2]) if total_active > 0 else 0.0
            stats = {
                "fps": self.fps,
                "active_objects": total_active,
                "class_counts": active_counts,
                "avg_confidence": avg_conf,
                "alerts": self._check_alerts(active_counts)
            }
            self.stats_ready.emit(stats)

        # Cleanup
        if cap:
            cap.release()
        if self.video_writer:
            self.video_writer.release()

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
        
        detections = [
            Detection([p1_x - p1_w//2 + noise(3), p1_y - p1_h//2 + noise(3), p1_w, p1_h], 0.94 + 0.05 * np.random.rand(), "person"),
            Detection([car_x - car_w//2 + noise(3), car_y - car_h//2 + noise(3), car_w, car_h], 0.96 + 0.03 * np.random.rand(), "car")
        ]
        
        # Dog only visible 80% of the time (simulates occlusion/missed detection)
        if tick % 10 != 0:
            detections.append(Detection([d_x - d_w//2 + noise(3), d_y - d_h//2 + noise(3), d_w, d_h], 0.82 + 0.1 * np.random.rand(), "dog"))
            
        return frame, detections

    def _draw_overlay(self, frame):
        """Draws tracking boxes, trails, heatmaps, and HUD overlays on the frame."""
        h, w, _ = frame.shape
        
        # 1. Overlay Heatmap
        if self.show_heatmap and self.heatmap_grid is not None:
            # Resize heatmap grid to frame size
            heatmap_resized = cv2.resize(self.heatmap_grid, (w, h))
            
            # Normalize to 0-255
            max_val = np.max(heatmap_resized)
            if max_val > 0:
                heatmap_norm = np.uint8(np.clip(heatmap_resized / (max_val / 5.0) * 255.0, 0, 255))
                # Apply color map
                heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
                
                # Overlay
                cv2.addWeighted(heatmap_color, self.heatmap_opacity, frame, 1.0 - self.heatmap_opacity, 0, frame)

        # 2. Draw Trails
        if self.show_trails:
            for track in self.tracker.tracks:
                if track.state == 2 and len(track.history) > 1:
                    # Choose color based on class
                    color = self._get_class_color(track.class_id)
                    for i in range(1, len(track.history)):
                        pt1 = track.history[i-1]
                        pt2 = track.history[i]
                        # Fading thickness
                        thickness = int(np.clip(i / len(track.history) * 3, 1, 3))
                        cv2.line(frame, pt1, pt2, color, thickness)

        # 3. Draw Bounding Boxes and IDs
        for track in self.tracker.tracks:
            if track.state == 2:  # Confirmed
                tlbr = track.to_tlbr().astype(int)
                color = self._get_class_color(track.class_id)
                
                # Draw box
                cv2.rectangle(frame, (tlbr[0], tlbr[1]), (tlbr[2], tlbr[3]), color, 2)
                
                # Draw high-tech corners
                len_corner = min(20, int((tlbr[2]-tlbr[0])*0.2))
                # Top-left corner
                cv2.line(frame, (tlbr[0], tlbr[1]), (tlbr[0] + len_corner, tlbr[1]), color, 4)
                cv2.line(frame, (tlbr[0], tlbr[1]), (tlbr[0], tlbr[1] + len_corner), color, 4)
                # Top-right corner
                cv2.line(frame, (tlbr[2], tlbr[1]), (tlbr[2] - len_corner, tlbr[1]), color, 4)
                cv2.line(frame, (tlbr[2], tlbr[1]), (tlbr[2], tlbr[1] + len_corner), color, 4)
                # Bottom-left corner
                cv2.line(frame, (tlbr[0], tlbr[3]), (tlbr[0] + len_corner, tlbr[3]), color, 4)
                cv2.line(frame, (tlbr[0], tlbr[3]), (tlbr[0], tlbr[3] - len_corner), color, 4)
                # Bottom-right corner
                cv2.line(frame, (tlbr[2], tlbr[3]), (tlbr[2] - len_corner, tlbr[3]), color, 4)
                cv2.line(frame, (tlbr[2], tlbr[3]), (tlbr[2], tlbr[3] - len_corner), color, 4)

                # Text label
                label = f"{track.class_id.upper()} ID: {track.track_id} [{int(track.confidence*100)}%]"
                
                # Draw tag banner
                (t_w, t_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame, (tlbr[0], tlbr[1] - t_h - 10), (tlbr[0] + t_w + 10, tlbr[1]), color, -1)
                cv2.putText(frame, label, (tlbr[0] + 5, tlbr[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # 4. HUD / Live telemetry on screen
        # Glowing green system status
        cv2.putText(frame, "AI SURVEILLANCE FEED ACTIVE", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (14, 165, 233), 2, cv2.LINE_AA)
        cv2.putText(frame, f"SOURCE: {self.source.upper()}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (203, 213, 225), 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (203, 213, 225), 1, cv2.LINE_AA)
        
        # Drawing crosshair/recording dot
        if self.is_recording:
            # Flashing red dot
            if int(time.time() * 2) % 2 == 0:
                cv2.circle(frame, (w - 150, 40), 6, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (w - 135, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)

    def _get_class_color(self, class_id):
        """Returns colors for different classes, giving a premium neon look."""
        colors = {
            "person": (239, 68, 68),       # Red
            "car": (16, 185, 129),         # Emerald Green
            "motorcycle": (59, 130, 246),  # Sky Blue
            "bicycle": (99, 102, 241),     # Indigo
            "bus": (245, 158, 11),         # Orange
            "truck": (168, 85, 247),       # Purple
            "dog": (236, 72, 153),         # Pink
            "cat": (14, 165, 233),         # Light Cyan
            "chair": (100, 116, 139),      # Slate Gray
            "laptop": (20, 184, 166),      # Teal
            "mobile phone": (234, 179, 8), # Yellow
        }
        # BGR representation of colors
        color = colors.get(class_id, (0, 255, 0))
        return (color[2], color[1], color[0])  # Convert RGB to BGR for OpenCV

    def _check_alerts(self, active_counts):
        """Checks for alert triggers and plays warning sounds if thresholds exceeded."""
        triggered = []
        
        # Person threshold alert
        persons = active_counts.get("person", 0)
        if persons > self.alert_person_threshold:
            triggered.append(f"PERSON OVERFLOW: {persons}/{self.alert_person_threshold}")
            
        # Vehicle detection alert
        if self.alert_vehicle_detect:
            vehicles = sum(active_counts.get(k, 0) for k in ["car", "motorcycle", "bus", "truck"])
            if vehicles > 0:
                triggered.append(f"VEHICLE DETECTED: {vehicles}")
                
        # Unknown/other alert
        if self.alert_unknown_detect:
            unknowns = active_counts.get("unknown", 0)
            if unknowns > 0:
                triggered.append(f"UNKNOWN ENTITY DETECTED: {unknowns}")

        # If any alert triggered on Windows, play a beep in a non-blocking thread
        if triggered:
            # Sound beep
            try:
                import winsound
                # Play short high-pitch alert beep
                winsound.Beep(1500, 100)
            except Exception:
                pass  # Ignore if winsound is not available or fails
                
        return triggered

    def _save_screenshot(self, frame):
        """Saves a frame to the screenshots directory."""
        filename = f"cap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        cv2.imwrite(filepath, frame)
        self.status_msg.emit(f"Screenshot saved: {filename}")

    def _write_video_frame(self, frame):
        """Writes frame to the video file."""
        h, w, _ = frame.shape
        if self.video_writer is None:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = os.path.join(self.recordings_dir, filename)
            # Use H264 / mp4v codec
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(filepath, fourcc, 30.0, (w, h))
            
        self.video_writer.write(frame)
