"""
Shared detection helper for running YOLO models on images.
Used by VideoProcessor and by live detection (WebSocket + REST).
"""
import os
import base64
import cv2
import numpy as np
from django.conf import settings

# PyTorch 2.6+ compatibility: patch torch.load to allow YOLO .pt files (weights_only=False for trusted checkpoints)
def _patch_torch_load_for_yolo():
    try:
        import torch
        if getattr(torch.load, '_eyeguard_patched', False):
            return
        _original = torch.load
        def _patched(*args, **kwargs):
            if 'weights_only' not in kwargs:
                kwargs['weights_only'] = False
            return _original(*args, **kwargs)
        _patched._eyeguard_patched = True
        torch.load = _patched
    except Exception:
        pass

# Conditional YOLO import (same as video_processor)
YOLO = None
if os.environ.get('SKIP_MODEL_LOAD') != '1':
    try:
        _patch_torch_load_for_yolo()
        from ultralytics import YOLO as _YOLO
        YOLO = _YOLO
    except Exception:
        YOLO = None

from .models import DetectionModel, CameraDetectionModel, Camera


# Color mapping for detection types (BGR)
COLOR_MAP = {
    'shoplifting': (0, 0, 255),   # Red
    'balaclava': (255, 0, 0),     # Blue
    'weapon': (0, 255, 255),      # Yellow
    'custom': (255, 0, 255),      # Magenta
    'motion': (0, 255, 0),        # Green
}


def draw_boxes_on_frame(annotated, results, label_name, color, conf_threshold):
    """
    Draw bounding boxes on frame and collect detected objects.
    Returns: (annotated_frame, detected_objects_list)
    """
    detected_objects = []
    if results is None or len(results) == 0 or results[0].boxes.conf is None:
        return annotated, detected_objects

    for box in results[0].boxes:
        conf = float(box.conf[0])
        if conf < conf_threshold:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{label_name} {conf:.2f}"
        cv2.putText(
            annotated,
            label,
            (x1, max(y1 - 8, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
        detected_objects.append({
            'label': label_name,
            'confidence': conf,
            'bbox': [x1, y1, x2, y2],
            'type': label_name.lower(),
        })
    return annotated, detected_objects


def load_detection_models_for_live(camera_id=None, model_ids=None):
    """
    Load detection model configs for live inference.

    Args:
        camera_id: If set, load models assigned to this camera (with per-camera confidence).
        model_ids: If set (and camera_id is None), load these DetectionModel IDs with default confidence.
        If both None, load all active DetectionModels with default confidence.

    Returns:
        List of dicts: [{'model': YOLO instance, 'name': str, 'confidence': float, 'type': str}, ...]
        Empty list if YOLO unavailable or no models found.
    """
    if YOLO is None:
        return []

    model_infos = []

    if camera_id is not None:
        cms = CameraDetectionModel.objects.filter(
            camera_id=camera_id,
            is_enabled=True,
            detection_model__is_active=True,
        ).select_related('detection_model')
        for cm in cms:
            model = cm.detection_model
            model_path = model.model_path
            if not os.path.isabs(model_path):
                model_path = os.path.join(settings.MEDIA_ROOT, 'models', model_path)
            try:
                model_infos.append({
                    'model': YOLO(model_path),
                    'name': model.name,
                    'confidence': cm.get_confidence_threshold(),
                    'type': model.model_type,
                })
            except Exception as e:
                print(f"⚠️ Failed to load {model.name}: {e}")
        return model_infos

    if model_ids is not None:
        qs = DetectionModel.objects.filter(id__in=model_ids, is_active=True)
    else:
        qs = DetectionModel.objects.filter(is_active=True)

    for model in qs:
        model_path = model.model_path
        if not os.path.isabs(model_path):
            model_path = os.path.join(settings.MEDIA_ROOT, 'models', model_path)
        try:
            model_infos.append({
                'model': YOLO(model_path),
                'name': model.name,
                'confidence': model.confidence_threshold,
                'type': model.model_type,
            })
        except Exception as e:
            print(f"⚠️ Failed to load {model.name}: {e}")

    return model_infos


def run_detection_on_frame(frame_bgr, model_infos_list, return_annotated=True):
    """
    Run detection models on a single BGR image (numpy array).

    Args:
        frame_bgr: numpy array (H, W, 3) BGR (e.g. from cv2.imdecode or cv2.VideoCapture.read).
        model_infos_list: List from load_detection_models_for_live().
        return_annotated: If True, draw boxes and return base64 JPEG.

    Returns:
        dict: {
            'detections': [{'label', 'confidence', 'bbox', 'type'}, ...],
            'annotated_image_b64': optional base64 JPEG string (if return_annotated=True),
        }
    """
    all_detections = []
    annotated = frame_bgr.copy() if return_annotated else None

    for info in model_infos_list:
        yolo_model = info['model']
        name = info['name']
        conf_threshold = info['confidence']
        model_type = info['type']
        try:
            results = yolo_model(frame_bgr, conf=conf_threshold, verbose=False)
            color = COLOR_MAP.get(model_type, (0, 255, 0))
            if return_annotated and annotated is not None:
                annotated, objs = draw_boxes_on_frame(
                    annotated, results, name.upper(), color, conf_threshold
                )
            else:
                _, objs = draw_boxes_on_frame(
                    frame_bgr.copy(), results, name.upper(), color, conf_threshold
                )
            all_detections.extend(objs)
        except Exception as e:
            print(f"⚠️ Detection error ({name}): {e}")

    out = {'detections': all_detections}
    if return_annotated and annotated is not None:
        success, buffer = cv2.imencode('.jpg', annotated)
        if success:
            out['annotated_image_b64'] = base64.b64encode(buffer.tobytes()).decode('ascii')
    return out


def decode_image_from_bytes(data):
    """Decode BGR image from bytes (JPEG/PNG). Returns numpy array or None."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def decode_image_from_base64(b64_string):
    """Decode BGR image from base64 string (e.g. data URL or raw base64). Returns numpy array or None."""
    # Strip data URL prefix if present
    if b64_string.startswith('data:'):
        b64_string = b64_string.split(',', 1)[-1]
    try:
        data = base64.b64decode(b64_string)
        return decode_image_from_bytes(data)
    except Exception:
        return None
