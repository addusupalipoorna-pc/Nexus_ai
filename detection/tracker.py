import numpy as np
import cv2
from scipy.optimize import linear_sum_assignment


class KalmanFilter:
    """
    A simple Kalman filter for tracking bounding boxes in image space.

    The 8-dimensional state space
        x, y, a, h, vx, vy, va, vh
    contains the bounding box center position (x, y), aspect ratio a, height h,
    and their respective velocities.

    Object motion is modeled by constant velocity.
    """

    def __init__(self):
        ndim, dt = 4, 1.0

        # Motion model transition matrix
        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt

        # Observation model matrix
        self._update_mat = np.eye(ndim, 2 * ndim)

        # Motion and observation noise parameters
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

    def initiate(self, measurement):
        """Create track from first measurement.

        Parameters
        ----------
        measurement : ndarray
            Bounding box coordinates (x, y, a, h) with center position (x, y),
            aspect ratio a, and height h.

        Returns
        -------
        (ndarray, ndarray)
            Returns the mean vector (8 dimensional) and covariance matrix (8x8
            dimensional) of the new track.
        """
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
        """Run Kalman filter prediction step.

        Parameters
        ----------
        mean : ndarray
            The 8-dimensional mean vector of the object state at the previous
            time step.
        covariance : ndarray
            The 8x8 covariance matrix of the object state at the previous
            time step.

        Returns
        -------
        (ndarray, ndarray)
            Returns the predicted state mean and covariance of the object state.
        """
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
        covariance = (
            np.linalg.multi_dot((self._motion_mat, covariance, self._motion_mat.T))
            + motion_cov
        )
        return mean, covariance

    def project(self, mean, covariance):
        """Project state distribution to measurement space.

        Parameters
        ----------
        mean : ndarray
            The state's mean vector (8 dimensional vector).
        covariance : ndarray
            The state's covariance matrix (8x8 dimensional).

        Returns
        -------
        (ndarray, ndarray)
            Returns the projected mean and covariance matrix of the given state
            estimate.
        """
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))

        mean = np.dot(self._update_mat, mean)
        covariance = (
            np.linalg.multi_dot((self._update_mat, covariance, self._update_mat.T))
            + innovation_cov
        )
        return mean, covariance

    def update(self, mean, covariance, measurement):
        """Run Kalman filter correction step.

        Parameters
        ----------
        mean : ndarray
            The predicted state's mean vector (8 dimensional).
        covariance : ndarray
            The state's covariance matrix (8x8 dimensional).
        measurement : ndarray
            The 4-dimensional measurement vector (x, y, a, h), where (x, y)
            is the center position, a the aspect ratio, and h the height of the
            bounding box.

        Returns
        -------
        (ndarray, ndarray)
            Returns the measurement-corrected state mean and covariance.
        """
        projected_mean, projected_cov = self.project(mean, covariance)

        chol_factor, lower = scipy_cholesky(projected_cov, lower=True)
        kalman_gain = np.linalg.solve(
            projected_cov, np.dot(covariance, self._update_mat.T).T
        ).T
        innovation = measurement - projected_mean

        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_covariance = covariance - np.linalg.multi_dot(
            (kalman_gain, projected_cov, kalman_gain.T)
        )
        return new_mean, new_covariance

    def gating_distance(self, mean, covariance, measurements, only_position=False):
        """Compute gating distance between state distribution and measurements.

        A gating threshold of 9.4877 is the 0.95 quantile of the chi-squared
        distribution with 4 degrees of freedom.
        """
        mean, covariance = self.project(mean, covariance)
        if only_position:
            mean, covariance = mean[:2], covariance[:2, :2]
            measurements = measurements[:, :2]

        cholesky_factor = np.linalg.cholesky(covariance)
        d = measurements - mean
        z = np.linalg.solve(cholesky_factor, d.T)
        squared_mahalanobis = np.sum(z * z, axis=0)
        return squared_mahalanobis


def scipy_cholesky(matrix, lower=True):
    """Fallback Cholesky decomposition using numpy."""
    return np.linalg.cholesky(matrix), lower


class TrackState:
    Tentative = 1
    Confirmed = 2
    Deleted = 3


class Track:
    """
    An individual tracked object state.
    """

    def __init__(self, mean, covariance, track_id, n_init, max_age, class_id, feature=None):
        self.mean = mean
        self.covariance = covariance
        self.track_id = track_id
        self.hits = 1
        self.age = 1
        self.time_since_update = 0
        self.state = TrackState.Tentative
        self.class_id = class_id
        self.confidence = 0.0

        self.history = []  # List of (x_center, y_center) for drawing trails
        self.features = []  # Appearance features list (HSV histograms)
        if feature is not None:
            self.features.append(feature)

        self._n_init = n_init
        self._max_age = max_age

    def to_tlwh(self):
        """Get bounding box representation in Top-Left, Width, Height (tlwh)."""
        ret = self.mean[:4].copy()
        ret[2] *= ret[3]  # w = a * h
        ret[0] -= ret[2] / 2
        ret[1] -= ret[3] / 2
        return ret

    def to_tlbr(self):
        """Get bounding box representation in Top-Left, Bottom-Right (tlbr)."""
        ret = self.to_tlwh()
        ret[2] = ret[0] + ret[2]
        ret[3] = ret[1] + ret[3]
        return ret

    def predict(self, kf):
        """Predict state mean and covariance using Kalman Filter."""
        self.mean, self.covariance = kf.predict(self.mean, self.covariance)
        self.age += 1
        self.time_since_update += 1

    def update(self, kf, detection, feature=None):
        """Update track state using detection measurement."""
        self.mean, self.covariance = kf.update(self.mean, self.covariance, detection.to_xyah())
        self.hits += 1
        self.time_since_update = 0
        self.class_id = detection.class_id
        self.confidence = detection.confidence

        # Save center position in history
        tlwh = self.to_tlwh()
        center = (int(tlwh[0] + tlwh[2] / 2), int(tlwh[1] + tlwh[3] / 2))
        self.history.append(center)
        if len(self.history) > 30:  # Cap movement trail at 30 frames
            self.history.pop(0)

        # Update features
        if feature is not None:
            self.features.append(feature)
            if len(self.features) > 10:  # Keep last 10 appearance profiles
                self.features.pop(0)

        # Confirm track if it has enough hits
        if self.state == TrackState.Tentative and self.hits >= self._n_init:
            self.state = TrackState.Confirmed

    def mark_deleted(self):
        self.state = TrackState.Deleted


class Detection:
    """
    Representation of a single bounding box detection.
    """

    def __init__(self, tlwh, confidence, class_id, feature=None):
        self.tlwh = np.asarray(tlwh, dtype=np.float32)
        self.confidence = float(confidence)
        self.class_id = class_id
        self.feature = feature

    def to_tlbr(self):
        ret = self.tlwh.copy()
        ret[2] = ret[0] + ret[2]
        ret[3] = ret[1] + ret[3]
        return ret

    def to_xyah(self):
        """Convert bounding box to format (center x, center y, aspect ratio, height)."""
        ret = self.tlwh.copy()
        ret[0] += ret[2] / 2
        ret[1] += ret[3] / 2
        ret[2] /= ret[3] + 1e-5  # w / h
        return ret


class Tracker:
    """
    Multi-object tracker with custom Deep SORT logic.
    """

    def __init__(self, max_age=30, n_init=3, max_iou_distance=0.7, max_hist_distance=0.4):
        self.max_age = max_age
        self.n_init = n_init
        self.max_iou_distance = max_iou_distance
        self.max_hist_distance = max_hist_distance

        self.kf = KalmanFilter()
        self.tracks = []
        self._next_id = 1

    def predict(self):
        """Predict state distributions for all active tracks."""
        for track in self.tracks:
            track.predict(self.kf)

    def update(self, detections, frame=None):
        """Perform matching and update track states."""
        # Extract features for detections if frame is provided
        if frame is not None:
            for det in detections:
                det.feature = self._extract_color_histogram(frame, det.tlwh)

        # Run Hungarian matching
        matches, unmatched_tracks, unmatched_detections = self._match(detections)

        # 1. Update matched tracks
        for track_idx, det_idx in matches:
            self.tracks[track_idx].update(self.kf, detections[det_idx], detections[det_idx].feature)

        # 2. Mark unmatched tracks as missed, delete if older than max_age
        for track_idx in unmatched_tracks:
            track = self.tracks[track_idx]
            if track.state == TrackState.Tentative or track.time_since_update > self.max_age:
                track.mark_deleted()

        # 3. Create new tracks for unmatched detections
        for det_idx in unmatched_detections:
            self._initiate_track(detections[det_idx])

        # Remove deleted tracks
        self.tracks = [t for t in self.tracks if t.state != TrackState.Deleted]

    def _match(self, detections):
        """Perform data association."""
        confirmed_tracks = [i for i, t in enumerate(self.tracks) if t.state == TrackState.Confirmed]
        unconfirmed_tracks = [i for i, t in enumerate(self.tracks) if t.state == TrackState.Tentative]

        # Level 1: Match confirmed tracks using appearance feature (histogram) and motion gating
        matches_a, unmatched_tracks_a, unmatched_dets = self._match_appearance(confirmed_tracks, detections)

        # Level 2: Match remaining confirmed tracks + unconfirmed tracks using IoU
        iou_track_candidates = unmatched_tracks_a + unconfirmed_tracks
        matches_b, unmatched_tracks_b, unmatched_dets = self._match_iou(iou_track_candidates, detections, unmatched_dets)

        # Combine matches
        matches = matches_a + matches_b
        unmatched_tracks = list(set(unmatched_tracks_b))

        return matches, unmatched_tracks, unmatched_dets

    def _match_appearance(self, track_indices, detections):
        """Match tracks to detections using appearance feature (histogram) gated by Kalman distance."""
        if not track_indices or not detections:
            return [], track_indices, list(range(len(detections)))

        # Create cost matrix using cosine distance of color histograms
        cost_matrix = np.zeros((len(track_indices), len(detections)), dtype=np.float32)
        for i, track_idx in enumerate(track_indices):
            track = self.tracks[track_idx]
            for j, det in enumerate(detections):
                # Cosine distance
                cost_matrix[i, j] = self._histogram_distance(track, det)

        # Motion gating: gate cost matrix using Mahalanobis distance
        # If detection is outside the gate, set cost to high value
        gating_threshold = 9.4877  # 0.95 quantile of chi-squared with 4 degrees of freedom
        for i, track_idx in enumerate(track_indices):
            track = self.tracks[track_idx]
            measurements = np.array([d.to_xyah() for d in detections])
            gating_dist = self.kf.gating_distance(track.mean, track.covariance, measurements)
            for j in range(len(detections)):
                if gating_dist[j] > gating_threshold:
                    cost_matrix[i, j] = 1.0  # Maximum cost if outside prediction gate

        # Solve linear assignment
        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        matches = []
        unmatched_tracks = list(track_indices)
        unmatched_detections = list(range(len(detections)))

        for r, c in zip(row_indices, col_indices):
            track_idx = track_indices[r]
            det_idx = c
            if cost_matrix[r, c] < self.max_hist_distance:
                matches.append((track_idx, det_idx))
                unmatched_tracks.remove(track_idx)
                unmatched_detections.remove(det_idx)

        return matches, unmatched_tracks, unmatched_detections

    def _match_iou(self, track_indices, detections, unmatched_dets_indices):
        """Match tracks to detections using Intersection-over-Union (IoU) overlap."""
        if not track_indices or not unmatched_dets_indices:
            return [], track_indices, unmatched_dets_indices

        # Create cost matrix using IoU distance (1 - IoU)
        cost_matrix = np.zeros((len(track_indices), len(unmatched_dets_indices)), dtype=np.float32)
        for i, track_idx in enumerate(track_indices):
            track = self.tracks[track_idx]
            for j, det_idx in enumerate(unmatched_dets_indices):
                cost_matrix[i, j] = 1.0 - iou(track.to_tlbr(), detections[det_idx].to_tlbr())

        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        matches = []
        unmatched_tracks = list(track_indices)
        unmatched_detections = list(unmatched_dets_indices)

        for r, c in zip(row_indices, col_indices):
            track_idx = track_indices[r]
            det_idx = unmatched_dets_indices[c]
            if cost_matrix[r, c] < self.max_iou_distance:
                matches.append((track_idx, det_idx))
                unmatched_tracks.remove(track_idx)
                unmatched_detections.remove(det_idx)

        return matches, unmatched_tracks, unmatched_detections

    def _initiate_track(self, detection):
        """Create a new track from a detection."""
        mean, covariance = self.kf.initiate(detection.to_xyah())
        self.tracks.append(
            Track(
                mean,
                covariance,
                self._next_id,
                self.n_init,
                self.max_age,
                detection.class_id,
                detection.feature
            )
        )
        self._next_id += 1

    def _extract_color_histogram(self, frame, tlwh):
        """Extract a normalized 3D color histogram in HSV space from box crop."""
        h, w, _ = frame.shape
        x1, y1, width, height = map(int, tlwh)
        
        # Clip to frame boundaries
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x1 + width, w))
        y2 = max(0, min(y1 + height, h))
        
        if (x2 - x1) < 2 or (y2 - y1) < 2:
            return np.zeros(24, dtype=np.float32)

        crop = frame[y1:y2, x1:x2]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        
        # Compute histograms for H, S, V channels
        # H bin range is [0, 180], S and V ranges are [0, 256]
        hist_h = cv2.calcHist([hsv], [0], None, [8], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [8], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [8], [0, 256])
        
        # Concatenate and normalize
        hist = np.concatenate([hist_h, hist_s, hist_v]).flatten()
        norm = np.linalg.norm(hist)
        if norm > 0:
            hist /= norm
        return hist

    def _histogram_distance(self, track, detection):
        """Compute the minimum cosine distance between detection feature and track features."""
        if detection.feature is None or not track.features:
            return 1.0
        
        distances = []
        for track_feat in track.features:
            # Cosine distance = 1 - Cosine Similarity
            dot_product = np.dot(track_feat, detection.feature)
            norm_track = np.linalg.norm(track_feat)
            norm_det = np.linalg.norm(detection.feature)
            if norm_track > 0 and norm_det > 0:
                similarity = dot_product / (norm_track * norm_det)
                distances.append(1.0 - similarity)
            else:
                distances.append(1.0)
                
        return min(distances) if distances else 1.0


def iou(box1, box2):
    """
    Compute intersection over union between two boxes.
    Boxes should be in format Top-Left, Bottom-Right: [x1, y1, x2, y2].
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    union = area1 + area2 - intersection
    if union <= 0:
        return 0.0
    return intersection / union
