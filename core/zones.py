import cv2
import numpy as np

class IntrusionZone:
    def __init__(self, polygon_points=None):
        """
        polygon_points: list of tuples/lists containing (x, y) coordinates.
        Defaults to a central trapezoidal area on a 1280x720 frame if None.
        """
        if polygon_points is None:
            # Default trapezoid secure zone in center-bottom of 1280x720 frame
            self.points = np.array([
                [350, 300],    # Top Left
                [930, 300],    # Top Right
                [1150, 680],   # Bottom Right
                [130, 680]     # Bottom Left
            ], dtype=np.int32)
        else:
            self.points = np.array(polygon_points, dtype=np.int32)

    def contains_point(self, point) -> bool:
        """Returns True if the coordinate (x, y) is inside the polygon zone."""
        # cv2.pointPolygonTest expects float32 coords and returns positive for inside, 0 for edge, negative for outside
        dist = cv2.pointPolygonTest(self.points.astype(np.float32), (float(point[0]), float(point[1])), False)
        return dist >= 0

    def contains_bbox(self, tlwh) -> bool:
        """
        Returns True if the bottom-center of the object's bounding box is inside the zone.
        In security systems, using the bottom-center (where the feet or wheels touch the ground) 
        provides the most accurate intrusion assessment.
        """
        x, y, w, h = tlwh
        bottom_center = (int(x + w / 2), int(y + h))
        return self.contains_point(bottom_center)

    def draw_zone(self, frame, is_alarm_active=False):
        """Draws the polygon zone on the frame with translucent overlay."""
        # Choose color: Crimson for alarm, Cyan for normal secure monitoring
        # OpenCV uses BGR: Crimson=(60, 0, 255) -> #FF003C, Cyan=(255, 229, 0) -> #00E5FF
        color = (60, 0, 255) if is_alarm_active else (255, 229, 0)
        thickness = 3 if is_alarm_active else 2
        
        # Draw translucent filled overlay
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.points], color)
        # Apply alpha transparency (0.1)
        cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
        
        # Draw solid outline
        cv2.polylines(frame, [self.points], True, color, thickness, lineType=cv2.LINE_AA)
        
        # Draw small header text on top of the zone
        top_left_point = self.points[0]
        label = "SECURE INTRUSION ZONE - ACTIVE" if not is_alarm_active else "!!! WARNING: ZONE INTRUSION ALERT !!!"
        cv2.putText(
            frame, label, 
            (top_left_point[0] + 5, top_left_point[1] - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1 if not is_alarm_active else 2, 
            cv2.LINE_AA
        )
