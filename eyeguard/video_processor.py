import cv2
import os
import time
from pathlib import Path
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from collections import deque
import numpy as np
import threading
from django.db import close_old_connections
import asyncio
from asgiref.sync import async_to_sync
from urllib.parse import quote

# PyTorch 2.6+ defaults to weights_only=True in torch.load; YOLO .pt files
# contain custom classes and require weights_only=False (safe for trusted checkpoints).
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

# Conditional import for YOLO/ultralytics. Some transformer/torch version
# mismatches can cause import-time failures (see transformers/torch '_pytree').
# Set environment variable `SKIP_MODEL_LOAD=1` to skip importing ultralytics
# and bypass model loading for smoke tests.
YOLO = None
if os.environ.get('SKIP_MODEL_LOAD') != '1':
    try:
        _patch_torch_load_for_yolo()
        from ultralytics import YOLO
    except Exception:
        YOLO = None

from .models import Camera, Alert, ProcessingLog, DetectionModel, CameraDetectionModel
from .alert_queue import AlertPriorityQueue


def build_hikvision_rtsp_url(ip_address, username, password, channel=1):
    """
    Build Hikvision RTSP stream URL from camera IP and credentials.
    Supports both standard ipcams and embedded DVRs with multiple channels.
    
    For embedded DVRs (16+ channels):
    rtsp://username:password@ip:554/h264/ch1/main/av_stream
    
    Args:
        ip_address: Camera/DVR IP address (e.g., '192.168.1.100')
        username: Camera username
        password: Camera password
        channel: Channel number (default 1)
    
    Returns:
        Complete RTSP URL with encoded credentials
    """
    if not all([ip_address, username, password]):
        raise ValueError("IP address, username, and password are required for Hikvision cameras")
    
    # URL-encode username and password to handle special characters
    safe_username = quote(username, safe='')
    safe_password = quote(password, safe='')
    
    # Hikvision embedded DVR RTSP URL format (works for 32+ channels)
    # Format: rtsp://user:pass@ip:554/h264/ch{channel}/main/av_stream
    rtsp_url = f"rtsp://{safe_username}:{safe_password}@{ip_address}:554/h264/ch{channel}/main/av_stream"
    
    return rtsp_url


class VideoProcessor:
    """
    Service to process video streams from cameras and generate alerts
    Integrates with existing YOLO detection code
    """
    
    def __init__(self, camera_id):
        """Initialize processor for a specific camera"""
        self.camera = Camera.objects.get(id=camera_id)
        self.business = self.camera.business
        
        # Check if subscription is valid
        if not self.business.is_valid_subscription:
            raise ValueError(f"Business {self.business.name} has invalid subscription")
        
        # Processing configuration
        self.target_fps = self.camera.target_fps
        self.motion_confidence = self.camera.motion_confidence
        self.persist_frames = self.camera.persist_frames
        
        # State
        self.motion_counter = 0
        self.frame_index = 0
        self.saved_index = 0
        
        # Video capture
        self.cap = None
        self.input_fps = None
        self.frame_skip = None
        
        # Models
        self.motion_model = None
        self.detection_models = {}
        
        # Processing log
        self.processing_log = None
        # Buffer of previous frames (raw BGR arrays). Keep last 40 frames
        self.prev_frames = deque(maxlen=40)
        # Stop event: set this to request graceful shutdown of run()
        self.stop_event = threading.Event()
        # Index for writing circular previous-frame files (0..maxlen-1)
        self.prev_write_index = 0
        
    def load_models(self):
        """Load all detection models for this camera"""
        print(f"Loading models for camera: {self.camera.name}")
        
        # Load motion detection model (YOLO11n)
        try:
            motion_model_path = os.path.join(settings.MEDIA_ROOT, 'models', 'yolo11n.pt')
            self.motion_model = YOLO(motion_model_path)
            print(f"✅ Motion model loaded from {motion_model_path}")
        except Exception as e:
            print(f"❌ Failed to load motion model: {e}")
            print(f"⚠️ Continuing without motion model")
        
        # Load camera-specific detection models
        camera_models = CameraDetectionModel.objects.filter(
            camera=self.camera,
            is_enabled=True,
            detection_model__is_active=True
        ).select_related('detection_model')
        
        for cm in camera_models:
            model = cm.detection_model
            try:
                model_path = model.model_path
                if not os.path.isabs(model_path):
                    model_path = os.path.join(settings.MEDIA_ROOT, 'models', model_path)
                
                self.detection_models[model.model_type] = {
                    'model': YOLO(model_path),
                    'name': model.name,
                    'confidence': cm.get_confidence_threshold(),
                    'type': model.model_type
                }
                print(f"✅ Loaded {model.name} (confidence: {cm.get_confidence_threshold()})")
            except Exception as e:
                print(f"❌ Failed to load {model.name}: {e}")
                print(f"⚠️ Skipping {model.name}, continuing with other models")
        
        if not self.motion_model and not self.detection_models:
            print(f"⚠️ WARNING: No models loaded! Processing will not detect anything.")
        else:
            print(f"✅ Models loaded (motion: {'yes' if self.motion_model else 'no'}, detection: {len(self.detection_models)})")
    
    def initialize_video_capture(self):
        """Initialize video capture from stream"""
        stream_url = self.camera.stream_url
        
        # Build RTSP URL for Hikvision if needed
        if self.camera.camera_type == 'hikvision' and self.camera.username and self.camera.password:
            print(f"Building Hikvision RTSP URL for camera: {self.camera.stream_url}")
            try:
                stream_url = build_hikvision_rtsp_url(
                    ip_address=self.camera.stream_url,
                    username=self.camera.username,
                    password=self.camera.password,
                    channel=self.camera.channel
                )
                print(f"✅ Hikvision URL built successfully")
            except ValueError as e:
                print(f"❌ Failed to build Hikvision URL: {e}")
                raise RuntimeError(f"Invalid Hikvision camera credentials: {e}")
        
        print(f"Initializing video capture from: {stream_url}")
        
        if self.camera.stream_type == 'webcam':
            # Webcam (usually 0)
            camera_index = int(stream_url) if str(stream_url).isdigit() else 0
            self.cap = cv2.VideoCapture(camera_index)
        elif self.camera.stream_type == 'file':
            # Video file
            self.cap = cv2.VideoCapture(stream_url)
        else:
            # RTSP/HTTP stream
            self.cap = cv2.VideoCapture(stream_url)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"❌ Could not open video stream: {stream_url}")
        
        self.input_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_skip = max(1, int(self.input_fps // self.target_fps))
        
        print(f"📹 Input FPS: {self.input_fps:.2f} → Processing at ~{self.target_fps} FPS")
        
        # Update camera status
        self.camera.status = 'active'
        self.camera.last_active = timezone.now()
        self.camera.save()
    
    def start_processing_log(self):
        """Create a processing log entry"""
        self.processing_log = ProcessingLog.objects.create(
            camera=self.camera,
            started_at=timezone.now(),
            status='running'
        )
    
    def end_processing_log(self, status='completed'):
        """End the processing log entry"""
        if self.processing_log:
            self.processing_log.ended_at = timezone.now()
            self.processing_log.status = status
            self.processing_log.save()
    
    def draw_boxes(self, annotated, results, label_name, color, conf_threshold):
        """
        Draw bounding boxes on frame and collect detected objects
        Returns: (annotated_frame, found, detected_objects_list)
        """
        found = False
        detected_objects = []
        
        if results[0].boxes.conf is None:
            return annotated, found, detected_objects
        
        for box in results[0].boxes:
            conf = float(box.conf[0])
            if conf < conf_threshold:
                continue
            
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Add label
            label = f"{label_name} {conf:.2f}"
            cv2.putText(
                annotated,
                label,
                (x1, max(y1 - 8, 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )
            
            # Track detection
            detected_objects.append({
                'label': label_name,
                'confidence': conf,
                'bbox': [x1, y1, x2, y2]
            })
            found = True
        
        return annotated, found, detected_objects
    
    def create_alert(self, alert_type, detected_objects, annotated_frame, avg_confidence):
        """Create an alert in the database with the annotated frame"""
        # Determine severity based on alert type and confidence
        severity = 'medium'
        if alert_type in ['weapon', 'multiple']:
            severity = 'critical'
        elif alert_type == 'balaclava':
            severity = 'high'
        elif avg_confidence > 0.8:
            severity = 'high'
        
        # Save annotated frame
        timestamp = timezone.now()
        filename = f"alert_{timestamp.strftime('%Y%m%d_%H%M%S')}_{self.saved_index}.jpg"
        # store alert images under media/alerts/
        filename = f"alerts/{filename}"
        
        # Encode frame to jpg
        success, buffer = cv2.imencode('.jpg', annotated_frame)
        if not success:
            print("❌ Failed to encode frame")
            return None
        
        # Create alert
        alert = Alert.objects.create(
            camera=self.camera,
            alert_type=alert_type,
            severity=severity,
            detected_objects=detected_objects,
            confidence_score=avg_confidence,
            frame_timestamp=timestamp,
            status='new'
        )
        
        # Previous frames are stored circularly in media/pastframes/ and are
        # overwritten as new frames arrive. They are not copied per-alert.

        # Save annotated frame as the primary alert image at MEDIA_ROOT root
        alert.frame_image.save(filename, ContentFile(buffer.tobytes()), save=True)
        
        self.saved_index += 1
        
        # Update processing log
        if self.processing_log:
            self.processing_log.alerts_generated += 1
            self.processing_log.save()
        
        print(f"🚨 ALERT CREATED: {alert_type} (ID: {alert.id}, Severity: {severity})")
        
        # Broadcast alert via WebSocket (non-blocking)
        try:
            from eyeguard.consumers import broadcast_alert
            async_to_sync(broadcast_alert)(alert, event_type='alert_created')
            print(f"📡 Alert {alert.id} broadcasted via WebSocket")
        except Exception as e:
            print(f"⚠️ Failed to broadcast alert via WebSocket: {e}")
        
        # After creating the alert, schedule confirmation in a background thread
        try:
            t = threading.Thread(
                target=self._confirm_alert_thread,
                args=(alert.id, alert_type, 2),
                daemon=True
            )
            t.start()
            print(f"🧵 Scheduled background confirmation for alert {alert.id}")
        except Exception as e:
            print(f"⚠️ Failed to schedule background confirmation for alert {alert.id}: {e}")

        return alert

    def _confirm_alert_thread(self, alert_id, alert_type, required_hits=2):
        """Thread target to safely run confirmation without blocking main loop.

        Re-fetches the `Alert` by id to avoid ORM objects crossing threads and
        ensures DB connections are handled properly.
        """
        try:
            close_old_connections()
        except Exception:
            pass

        try:
            alert = Alert.objects.get(id=alert_id)
            self.confirm_alert(alert, alert_type, required_hits=required_hits)
        except Exception as e:
            print(f"⚠️ Background confirmation failed for alert {alert_id}: {e}")
        finally:
            try:
                close_old_connections()
            except Exception:
                pass

    def confirm_alert(self, alert, alert_type, required_hits=2):
        """Re-run detection on the last up-to-10 frames to confirm alert validity.

        - If >= required_hits frames contain the same detection, mark the alert as
          'investigating' and add a note. If fewer hits, mark as 'false_positive'.
        - If matching detection model isn't available, leave alert as 'new'.
        """
        print(f"🔍 Confirming alert {alert.id} ({alert_type}) using last {len(self.prev_frames)} frames")

        # Gather frames to check: in-memory buffer first
        frames = list(self.prev_frames)

        # If no in-memory frames, try loading circular pastframe files
        if not frames:
            try:
                circ_dir = os.path.join(settings.MEDIA_ROOT, 'pastframes')
                for i in range(10):
                    circ_path = f"pastframes/camera_{self.camera.id}_prev_{i}.jpg"
                    if default_storage.exists(circ_path):
                        with default_storage.open(circ_path, 'rb') as fh:
                            data = fh.read()
                            arr = np.frombuffer(data, dtype=np.uint8)
                            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                            if img is not None:
                                frames.append(img)
            except Exception as e:
                print(f"⚠️ Could not load circular past frames: {e}")

        if not frames:
            print(f"⚠️ No frames available to confirm alert {alert.id}")
            return

        # Determine which model types to check
        if alert_type == 'multiple':
            model_types = list(self.detection_models.keys())
        else:
            model_types = [alert_type]

        # If no matching models are loaded, skip confirmation
        available = [m for m in model_types if m in self.detection_models]
        if not available:
            print(f"⚠️ No matching detection models loaded to confirm alert {alert.id}")
            return

        hits = 0
        checked_frames = 0

        for f in frames:
            frame_hit = False
            for mtype in available:
                model_info = self.detection_models.get(mtype)
                if not model_info:
                    continue
                try:
                    results = model_info['model'](f, conf=model_info['confidence'], verbose=False)
                    _, found, _ = self.draw_boxes(f.copy(), results, model_info['name'].upper(), (0, 255, 0), model_info['confidence'])
                    if found:
                        frame_hit = True
                        break
                except Exception as e:
                    print(f"⚠️ Error during confirmation detection ({mtype}): {e}")
                    continue

            checked_frames += 1
            if frame_hit:
                hits += 1

            # Early exit if we've already reached required hits
            if hits >= required_hits:
                break

        # Decide status based on hits
        note = f"Auto-confirmation: {hits}/{checked_frames} frames matched (required {required_hits})."
        if hits >= required_hits:
            # Mark for investigation (human review)
            alert.status = 'investigating'
            alert.resolution_notes = (alert.resolution_notes or '') + '\n' + note
            alert.save()
            print(f"✅ Alert {alert.id} confirmed by auto-check ({hits}/{checked_frames})")
        else:
            # Mark as false positive
            alert.status = 'false_positive'
            alert.resolution_notes = (alert.resolution_notes or '') + '\n' + note
            alert.save()
            print(f"❌ Alert {alert.id} marked false_positive by auto-check ({hits}/{checked_frames})")
    
    def process_frame(self, frame):
        """
        Process a single frame through the detection pipeline
        Returns: True if alert was generated, False otherwise
        """
        # STEP 1: MOTION DETECTION
        detected = False
        
        if self.motion_model:
            try:
                motion_results = self.motion_model(
                    frame,
                    conf=self.motion_confidence,
                    classes=[0, 2, 3, 5, 7],  # person, car, motorcycle, bus, truck
                    verbose=False
                )
                
                detected = (
                    motion_results[0].boxes.conf is not None and
                    len(motion_results[0].boxes.conf) > 0
                )
            except Exception as e:
                print(f"⚠️ Motion detection error: {e}")
                detected = False
        
        self.motion_counter = self.motion_counter + 1 if detected else 0
        
        # Update processing log
        if self.processing_log:
            self.processing_log.frames_processed += 1
            if self.processing_log.frames_processed % 100 == 0:
                self.processing_log.save()
        
        # STEP 2: SECONDARY DETECTION MODELS
        if self.motion_counter >= self.persist_frames:
            print(f"\n⚠️ Motion persisted for {self.motion_counter} frames")
            
            annotated = frame.copy()
            all_detected_objects = []
            alert_types = []
            confidences = []
            
            # Color mapping for different detection types
            color_map = {
                'shoplifting': (0, 0, 255),      # Red
                'balaclava': (255, 0, 0),        # Blue
                'weapon': (0, 255, 255),         # Yellow
                'custom': (255, 0, 255)          # Magenta
            }
            
            # Run all detection models
            for model_type, model_info in self.detection_models.items():
                results = model_info['model'](frame, conf=model_info['confidence'], verbose=False)
                color = color_map.get(model_type, (0, 255, 0))
                
                annotated, found, detected_objects = self.draw_boxes(
                    annotated,
                    results,
                    model_info['name'].upper(),
                    color,
                    model_info['confidence']
                )
                
                if found:
                    alert_types.append(model_type)
                    all_detected_objects.extend(detected_objects)
                    confidences.extend([obj['confidence'] for obj in detected_objects])
            
            # Create alert if anything was detected
            if alert_types:
                # Determine alert type
                if len(alert_types) > 1:
                    alert_type = 'multiple'
                else:
                    alert_type = alert_types[0]
                
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Create alert in database
                self.create_alert(
                    alert_type=alert_type,
                    detected_objects=all_detected_objects,
                    annotated_frame=annotated,
                    avg_confidence=avg_confidence
                )
                
                self.motion_counter = 0  # Reset after alert
                return True
        
        return False
    
    def run(self, max_frames=None):
        """
        Main processing loop
        
        Args:
            max_frames: Maximum number of frames to process (None for continuous)
        """
        try:
            print(f"\n{'='*50}")
            print(f"Starting video processing for camera: {self.camera.name}")
            print(f"Business: {self.business.name}")
            print(f"{'='*50}\n")
            
            self.load_models()
            self.initialize_video_capture()
            self.start_processing_log()
            
            while True:
                if self.stop_event.is_set():
                    print("Stop requested — exiting processing loop")
                    break

                ret, frame = self.cap.read()
                if not ret:
                    print("End of video stream")
                    break
                
                self.frame_index += 1
                
                # FPS throttling
                if self.frame_index % self.frame_skip != 0:
                    continue

                # Keep a rolling buffer of the last N processed frames
                # Store a copy so later modifications (annotations) don't affect saved raw frames
                prev = frame.copy()
                self.prev_frames.append(prev)

                # Also write the frame to a circular buffer of files under media/pastframes,
                # overwriting the same N filenames so the latest N frames are always available.
                try:
                    ok, prev_buf = cv2.imencode('.jpg', prev)
                    if ok:
                        # Ensure physical directory exists for local filesystem
                        try:
                            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'pastframes'), exist_ok=True)
                        except Exception:
                            pass

                        circ_path = f"pastframes/camera_{self.camera.id}_prev_{self.prev_write_index}.jpg"
                        try:
                            if default_storage.exists(circ_path):
                                default_storage.delete(circ_path)
                        except Exception:
                            pass
                        try:
                            default_storage.save(circ_path, ContentFile(prev_buf.tobytes()))
                        except Exception as e:
                            print(f"⚠️ Failed to save circular prev frame to storage: {e}")
                        self.prev_write_index = (self.prev_write_index + 1) % self.prev_frames.maxlen
                except Exception as e:
                    print(f"⚠️ Failed to write circular prev frame: {e}")

                # Process frame
                self.process_frame(frame)
                
                # Check max frames limit
                if max_frames and self.frame_index >= max_frames:
                    print(f"Reached max frames limit: {max_frames}")
                    break
                
                # Update camera last_active periodically
                if self.frame_index % 300 == 0:  # Every ~30 seconds at 10 FPS
                    self.camera.last_active = timezone.now()
                    self.camera.save()
            
            self.end_processing_log('completed')
            
        except KeyboardInterrupt:
            print("\n⚠️ Processing interrupted by user")
            self.end_processing_log('stopped')
            
        except Exception as e:
            print(f"\n❌ Error during processing: {e}")
            if self.processing_log:
                self.processing_log.errors.append({
                    'timestamp': timezone.now().isoformat(),
                    'error': str(e)
                })
            self.end_processing_log('error')
            self.camera.status = 'error'
            self.camera.save()
            raise
            
        finally:
            # Cleanup
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            print("\n✅ Processing completed")
            print(f"Total frames processed: {self.frame_index}")
            print(f"Alerts generated: {self.saved_index}")
    
    def reprocess_alert_from_queue(self, alert_id):
        """
        Reprocess a queued alert using current detection models.
        
        Loads the alert's frame image and re-runs all detection models on it,
        updating the alert with new detection results.
        
        Args:
            alert_id: ID of the alert to reprocess
        
        Returns:
            Alert instance or None if not found
        """
        try:
            alert = Alert.objects.get(id=alert_id)
        except Alert.DoesNotExist:
            print(f"❌ Alert {alert_id} not found")
            return None
        
        # Load the saved frame image
        try:
            if not alert.frame_image:
                print(f"⚠️ Alert {alert.id} has no frame image")
                AlertPriorityQueue.dequeue(alert.id)
                return alert
            
            # Read the frame from storage
            with alert.frame_image.open('rb') as fh:
                data = fh.read()
                arr = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    print(f"❌ Failed to decode frame image for alert {alert.id}")
                    AlertPriorityQueue.dequeue(alert.id)
                    return alert
        except Exception as e:
            print(f"❌ Failed to load frame for alert {alert.id}: {e}")
            AlertPriorityQueue.dequeue(alert.id)
            return alert
        
        print(f"🔄 Reprocessing alert {alert.id} ({alert.alert_type})...")
        
        # Run detection models
        annotated = frame.copy()
        all_detected_objects = []
        alert_types = []
        confidences = []
        
        color_map = {
            'shoplifting': (0, 0, 255),      # Red
            'balaclava': (255, 0, 0),        # Blue
            'weapon': (0, 255, 255),         # Yellow
            'custom': (255, 0, 255)          # Magenta
        }
        
        # Run all detection models
        for model_type, model_info in self.detection_models.items():
            try:
                results = model_info['model'](frame, conf=model_info['confidence'], verbose=False)
                color = color_map.get(model_type, (0, 255, 0))
                
                annotated, found, detected_objects = self.draw_boxes(
                    annotated,
                    results,
                    model_info['name'].upper(),
                    color,
                    model_info['confidence']
                )
                
                if found:
                    alert_types.append(model_type)
                    all_detected_objects.extend(detected_objects)
                    confidences.extend([obj['confidence'] for obj in detected_objects])
            except Exception as e:
                print(f"⚠️ Error running {model_type} model on alert {alert.id}: {e}")
                continue
        
        # Update alert with new results
        if alert_types:
            if len(alert_types) > 1:
                alert.alert_type = 'multiple'
            else:
                alert.alert_type = alert_types[0]
            
            alert.detected_objects = all_detected_objects
            avg_confidence = sum(confidences) / len(confidences) if confidences else alert.confidence_score
            alert.confidence_score = avg_confidence
            
            # Save updated annotated frame
            try:
                success, buffer = cv2.imencode('.jpg', annotated)
                if success:
                    old_image = alert.frame_image
                    alert.frame_image.save(
                        f"alerts/reprocessed_alert_{alert.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                        ContentFile(buffer.tobytes()),
                        save=False
                    )
                    if old_image:
                        try:
                            old_image.delete()
                        except Exception:
                            pass
            except Exception as e:
                print(f"⚠️ Failed to save updated frame for alert {alert.id}: {e}")
            
            alert.status = 'investigating'
            note = f"Reprocessed (attempt {alert.reprocess_attempts + 1}): detected in {len(alert_types)} models."
            alert.resolution_notes = (alert.resolution_notes or '') + '\n' + note
        else:
            # No detections found in reprocessing
            alert.status = 'false_positive'
            note = f"Reprocessed (attempt {alert.reprocess_attempts + 1}): no detections found."
            alert.resolution_notes = (alert.resolution_notes or '') + '\n' + note
        
        alert.save()
        
        # Mark as reprocessed in queue
        AlertPriorityQueue.mark_reprocessed(alert.id)
        
        if alert_types:
            print(f"✅ Alert {alert.id} reprocessed: {', '.join(alert_types)}")
        else:
            print(f"❌ Alert {alert.id} reprocessed: no detections")
        
        return alert


# Helper function to start processing for a camera
def start_camera_processing(camera_id, max_frames=None):
    """
    Start video processing for a specific camera
    
    Args:
        camera_id: ID of the camera to process
        max_frames: Maximum frames to process (None for continuous)
    """
    processor = VideoProcessor(camera_id)
    processor.run(max_frames=max_frames)
