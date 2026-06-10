import os
from ultralytics import YOLO
from .tracker import Detection

# Target class mappings based on COCO indices
# 0: person, 1: bicycle, 2: car, 3: motorcycle, 5: bus, 7: truck, 15: cat, 16: dog, 56: chair, 67: cell phone, 73: laptop
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

class ObjectDetector:
    def __init__(self, model_name="yolov8n.pt", conf_threshold=0.25):
        # Establish models folder
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        os.makedirs(model_dir, exist_ok=True)
        
        self.model_path = os.path.join(model_dir, model_name)
        self.conf_threshold = conf_threshold
        
        # Load the model (YOLO will download it into model_path if not present)
        # Note: Ultralytics expects a path or standard name. We load it using the path.
        self.model = YOLO(self.model_path)

    def set_conf_threshold(self, value):
        self.conf_threshold = value

    def detect(self, frame) -> list:
        """Runs inference on a frame and returns a list of Detection objects."""
        # Run inference filtering by target classes
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            classes=list(TARGET_CLASSES.keys()),
            verbose=False
        )
        
        detections = []
        if len(results) == 0:
            return detections
            
        result = results[0]
        boxes = result.boxes
        
        for box in boxes:
            # Box in xyxy format
            xyxy = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            
            # Map class ID to readable label
            label = TARGET_CLASSES.get(cls_id, "unknown")
            
            # Convert xyxy to tlwh (top-left x, top-left y, width, height)
            xmin, ymin, xmax, ymax = xyxy
            w = xmax - xmin
            h = ymax - ymin
            tlwh = [xmin, ymin, w, h]
            
            detections.append(Detection(tlwh, conf, label))
            
        return detections
