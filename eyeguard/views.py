from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.contrib.auth import get_user_model, authenticate
from rest_framework.authtoken.models import Token
from django.db.models import Q, Count, Avg
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.core.files.storage import default_storage
import io
import os
import cv2
import numpy as np
import concurrent.futures
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import (
    Subscription, Business, DetectionModel, Camera,
    CameraDetectionModel, Alert, AlertNotification, ProcessingLog
)
from .serializers import (
    SubscriptionSerializer, BusinessSerializer, BusinessCreateSerializer,
    DetectionModelSerializer, CameraSerializer, CameraCreateSerializer,
    CameraDetectionModelSerializer, AlertSerializer, AlertCreateSerializer,
    AlertUpdateSerializer, AlertNotificationSerializer, ProcessingLogSerializer
)
from .permissions import IsBusinessAdmin, IsBusinessMember
from .alert_queue import AlertPriorityQueue
from .video_processor import VideoProcessor
from .detection_helper import (
    load_detection_models_for_live,
    run_detection_on_frame,
    decode_image_from_bytes,
    decode_image_from_base64,
)


User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def email_token_auth(request):
  """
  Obtain DRF auth token using email + password instead of username.

  POST body:
    - email
    - password
  """
  email = request.data.get("email")
  password = request.data.get("password")

  if not email or not password:
    return Response(
      {"detail": "Email and password are required."},
      status=status.HTTP_400_BAD_REQUEST,
    )

  try:
    user = User.objects.get(email=email)
  except User.DoesNotExist:
    return Response(
      {"detail": "Invalid email or password."},
      status=status.HTTP_400_BAD_REQUEST,
    )

  user = authenticate(request=request, username=user.username, password=password)
  if not user:
    return Response(
      {"detail": "Invalid email or password."},
      status=status.HTTP_400_BAD_REQUEST,
    )

  token, _ = Token.objects.get_or_create(user=user)
  return Response({"token": token.key})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def live_detect(request):
    """
    Run detection on a single image (file upload or base64 in JSON).
    POST body: image (file), or JSON with image_b64; optional camera_id or model_ids.
    Returns: { detections: [...], annotated_image_b64?: "..." }
    """
    camera_id = request.data.get('camera_id')
    model_ids = request.data.get('model_ids')
    return_annotated = request.data.get('return_annotated', True)

    # Resolve image
    frame = None
    if 'image' in request.FILES:
        data = request.FILES['image'].read()
        frame = decode_image_from_bytes(data)
    elif request.content_type and 'json' in request.content_type:
        b64 = request.data.get('image_b64') or request.data.get('image')
        if b64:
            frame = decode_image_from_base64(b64)
    if frame is None:
        return Response(
            {'error': 'Provide image (file upload) or JSON with image_b64'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Camera access check
    if camera_id is not None:
        user = request.user
        if not user.is_superuser:
            if not Camera.objects.filter(id=camera_id, business__admin_user=user).exists():
                return Response({'error': 'Unauthorized for this camera'}, status=status.HTTP_403_FORBIDDEN)

    # Load models
    model_infos = load_detection_models_for_live(camera_id=camera_id, model_ids=model_ids)
    if not model_infos:
        return Response(
            {'error': 'No detection models available. Set camera_id or model_ids, and ensure models are configured.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = run_detection_on_frame(frame, model_infos, return_annotated=return_annotated)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'detections': result['detections'],
        'annotated_image_b64': result.get('annotated_image_b64') if return_annotated else None,
    })


@method_decorator(login_required, name='dispatch')
class LiveDetectionPageView(TemplateView):
    """Serves the live webcam detection page (requires login)."""
    template_name = 'eyeguard/live_detection.html'


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing available subscription plans
    """
    queryset = Subscription.objects.filter(is_active=True)
    serializer_class = SubscriptionSerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['get'])
    def features(self, request, pk=None):
        """Get detailed features of a subscription plan"""
        subscription = self.get_object()
        return Response({
            'id': subscription.id,
            'name': subscription.get_name_display(),
            'features': subscription.features,
            'max_cameras': subscription.max_cameras,
            'price': subscription.price
        })


class BusinessViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing businesses
    """
    queryset = Business.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_subscription_active', 'subscription']
    search_fields = ['name', 'email']
    ordering_fields = ['created_at', 'name', 'subscription_end_date']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BusinessCreateSerializer
        return BusinessSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Business.objects.all()
        # Users can only see businesses they admin
        return Business.objects.filter(admin_user=user)
    
    @action(detail=True, methods=['post'])
    def validate_subscription(self, request, pk=None):
        """Manually validate/check business subscription status"""
        business = self.get_object()
        
        is_valid = business.is_valid_subscription
        
        return Response({
            'business_id': business.id,
            'business_name': business.name,
            'is_valid': is_valid,
            'is_active': business.is_subscription_active,
            'subscription_end_date': business.subscription_end_date,
            'days_until_expiry': business.days_until_expiry,
            'can_add_camera': business.can_add_camera(),
            'current_cameras': business.cameras.filter(is_active=True).count(),
            'max_cameras': business.subscription.max_cameras
        })
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """Get business dashboard statistics"""
        business = self.get_object()
        
        # Get time range from query params (default: last 7 days)
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        cameras = business.cameras.filter(is_active=True)
        alerts = Alert.objects.filter(camera__business=business)
        recent_alerts = alerts.filter(created_at__gte=start_date)
        
        stats = {
            'business_info': {
                'name': business.name,
                'subscription': business.subscription.get_name_display(),
                'is_valid_subscription': business.is_valid_subscription,
                'days_until_expiry': business.days_until_expiry
            },
            'cameras': {
                'total': cameras.count(),
                'active': cameras.filter(status='active').count(),
                'inactive': cameras.filter(status='inactive').count(),
                'error': cameras.filter(status='error').count(),
                'max_allowed': business.subscription.max_cameras
            },
            'alerts': {
                'total_period': recent_alerts.count(),
                'new': recent_alerts.filter(status='new').count(),
                'acknowledged': recent_alerts.filter(status='acknowledged').count(),
                'resolved': recent_alerts.filter(status='resolved').count(),
                'by_severity': {
                    'critical': recent_alerts.filter(severity='critical').count(),
                    'high': recent_alerts.filter(severity='high').count(),
                    'medium': recent_alerts.filter(severity='medium').count(),
                    'low': recent_alerts.filter(severity='low').count()
                },
                'by_type': dict(recent_alerts.values('alert_type').annotate(count=Count('id')).values_list('alert_type', 'count'))
            }
        }
        
        return Response(stats)


class DetectionModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing detection models
    """
    queryset = DetectionModel.objects.filter(is_active=True)
    serializer_class = DetectionModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['model_type', 'is_active']
    search_fields = ['name', 'description']


class CameraViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cameras
    """
    queryset = Camera.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['business', 'status', 'is_active', 'stream_type']
    search_fields = ['name', 'location']
    ordering_fields = ['created_at', 'name', 'last_active']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Use a dedicated serializer for CREATE input, but always return the
        full CameraSerializer in responses so the frontend receives the
        camera id and all read-only fields.
        """
        if self.action == 'create':
            return CameraCreateSerializer
        return CameraSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Camera.objects.all()
        # Users can only see cameras from their businesses
        return Camera.objects.filter(business__admin_user=user)
    
    def perform_create(self, serializer):
        """
        Called by the default create() implementation to persist a new camera.
        """
        camera = serializer.save()
        camera.last_active = timezone.now()
        camera.save()

    def create(self, request, *args, **kwargs):
        """
        Override create so that:
        - CameraCreateSerializer is used for validation/input
        - The response body is serialized with CameraSerializer, which includes `id`.
        """
        create_serializer = CameraCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        camera = create_serializer.save()
        camera.last_active = timezone.now()
        camera.save()

        output_serializer = CameraSerializer(camera, context={'request': request})
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'])
    def assign_model(self, request, pk=None):
        """Assign a detection model to this camera"""
        camera = self.get_object()
        model_id = request.data.get('model_id')
        confidence_threshold = request.data.get('confidence_threshold')
        is_enabled = request.data.get('is_enabled', True)
        
        try:
            detection_model = DetectionModel.objects.get(id=model_id, is_active=True)
        except DetectionModel.DoesNotExist:
            return Response(
                {'error': 'Detection model not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already assigned
        assignment, created = CameraDetectionModel.objects.get_or_create(
            camera=camera,
            detection_model=detection_model,
            defaults={
                'confidence_threshold': confidence_threshold,
                'is_enabled': is_enabled
            }
        )
        
        if not created:
            # Update existing assignment
            if confidence_threshold is not None:
                assignment.confidence_threshold = confidence_threshold
            assignment.is_enabled = is_enabled
            assignment.save()
        
        serializer = CameraDetectionModelSerializer(assignment)
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_model(self, request, pk=None):
        """Remove a detection model from this camera"""
        camera = self.get_object()
        model_id = request.data.get('model_id')
        
        try:
            assignment = CameraDetectionModel.objects.get(
                camera=camera,
                detection_model_id=model_id
            )
            assignment.delete()
            return Response({'message': 'Model removed successfully'}, status=status.HTTP_204_NO_CONTENT)
        except CameraDetectionModel.DoesNotExist:
            return Response(
                {'error': 'Model assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        """Get all alerts for this camera"""
        camera = self.get_object()
        
        # Filter by date range
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        alerts = camera.alerts.filter(created_at__gte=start_date)
        
        # Additional filters
        alert_status = request.query_params.get('status')
        if alert_status:
            alerts = alerts.filter(status=alert_status)
        
        severity = request.query_params.get('severity')
        if severity:
            alerts = alerts.filter(severity=severity)
        
        serializer = AlertSerializer(alerts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def past_frames(self, request, pk=None):
        """Return URLs for the latest circular past frames for this camera.

        Files are stored under `pastframes/camera_<id>_prev_<0..9>.jpg`.
        """
        camera = self.get_object()
        frames = []
        for i in range(10):
            rel_path = f'pastframes/camera_{camera.id}_prev_{i}.jpg'
            if default_storage.exists(rel_path):
                try:
                    url = default_storage.url(rel_path)
                except Exception:
                    # Fallback to MEDIA_URL
                    url = request.build_absolute_uri(settings.MEDIA_URL + rel_path)
                frames.append({'index': i, 'path': rel_path, 'url': url})

        return Response({'camera_id': camera.id, 'frames': frames})

    @action(detail=True, methods=['post'])
    def reprocess_frames(self, request, pk=None):
        """Run configured detection models on the 10 circular past frames.

        POST body (optional):
          - models: [detection_model_id, ...] (if omitted, use camera's enabled models)
          - save: boolean (if true, create Alert objects for detections)
        """
        camera = self.get_object()
        model_ids = request.data.get('models')
        save_alerts = bool(request.data.get('save', False))

        # Load model infos
        if model_ids:
            cms = CameraDetectionModel.objects.filter(camera=camera, detection_model_id__in=model_ids, is_enabled=True).select_related('detection_model')
        else:
            cms = CameraDetectionModel.objects.filter(camera=camera, is_enabled=True, detection_model__is_active=True).select_related('detection_model')

        model_infos = []
        # Import YOLO lazily
        try:
            from ultralytics import YOLO
        except Exception as e:
            return Response({'error': f'ultralytics import failed: {e}'}, status=500)

        for cm in cms:
            model = cm.detection_model
            model_path = model.model_path
            if not os.path.isabs(model_path):
                model_path = os.path.join(settings.MEDIA_ROOT, 'models', model_path)
            try:
                y = YOLO(model_path)
                model_infos.append({
                    'id': model.id,
                    'name': model.name,
                    'type': model.model_type,
                    'confidence': cm.get_confidence_threshold(),
                    'yolo': y,
                })
            except Exception as e:
                print(f"⚠️ Failed to load model {model.name}: {e}")

        if not model_infos:
            return Response({'error': 'No models available to run'}, status=400)

        # Collect existing pastframe paths
        frame_paths = []
        for i in range(10):
            rel = f'pastframes/camera_{camera.id}_prev_{i}.jpg'
            if default_storage.exists(rel):
                frame_paths.append(rel)

        if not frame_paths:
            return Response({'error': 'No past frames found for this camera'}, status=404)

        # Worker to process one (frame_path, model_info)
        def process_task(frame_path, model_info):
            try:
                with default_storage.open(frame_path, 'rb') as f:
                    data = f.read()
                arr = np.frombuffer(data, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                results = model_info['yolo'](img, conf=model_info['confidence'], verbose=False)
                detections = []
                if results and results[0].boxes is not None and results[0].boxes.conf is not None:
                    for box in results[0].boxes:
                        conf = float(box.conf[0])
                        if conf < model_info['confidence']:
                            continue
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        detections.append({
                            'model': model_info['name'],
                            'type': model_info['type'],
                            'confidence': conf,
                            'bbox': [x1, y1, x2, y2]
                        })
                return (frame_path, model_info['id'], detections)
            except Exception as e:
                return (frame_path, model_info['id'], {'error': str(e)})

        results = []
        # Run tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as exe:
            futures = []
            for fp in frame_paths:
                for mi in model_infos:
                    futures.append(exe.submit(process_task, fp, mi))
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

        # Aggregate by frame
        summary = {}
        for frame_path, model_id, det in results:
            summary.setdefault(frame_path, []).append({'model_id': model_id, 'detections': det})

        # Optionally save alerts for any detections
        saved_alerts = []
        if save_alerts:
            for frame_path, entries in summary.items():
                # Merge detections across models
                all_dets = []
                confidences = []
                for e in entries:
                    if isinstance(e['detections'], dict) and e['detections'].get('error'):
                        continue
                    for d in e['detections']:
                        all_dets.append(d)
                        confidences.append(d['confidence'])
                if not all_dets:
                    continue
                # Save alert with this frame as image
                try:
                    with default_storage.open(frame_path, 'rb') as f:
                        imgdata = f.read()
                    timestamp = timezone.now()
                    alert = Alert.objects.create(
                        camera=camera,
                        alert_type=all_dets[0]['type'] if all_dets else 'custom',
                        severity='medium',
                        detected_objects=all_dets,
                        confidence_score=(sum(confidences)/len(confidences)) if confidences else 0,
                        frame_timestamp=timestamp,
                        status='new'
                    )
                    fname = f"alert_{timestamp.strftime('%Y%m%d_%H%M%S')}_{alert.id}.jpg"
                    alert.frame_image.save(fname, ContentFile(imgdata), save=True)
                    saved_alerts.append(alert.id)
                except Exception as e:
                    print(f"⚠️ Failed to save alert for {frame_path}: {e}")

        return Response({'frames_processed': len(frame_paths), 'models_used': [m['id'] for m in model_infos], 'summary': summary, 'saved_alerts': saved_alerts})
    
    @action(detail=False, methods=['post'])
    def setup_hikvision(self, request):
        """
        Setup a new Hikvision camera or test connection.
        
        POST body:
        {
            "name": "Camera Name",
            "location": "Camera Location",
            "ip_address": "192.168.1.100",
            "username": "admin",
            "password": "password",
            "channel": 1  (optional, default 1),
            "business_id": business_id
        }
        
        Returns: Camera object with stream_url already configured
        """
        from .video_processor import build_hikvision_rtsp_url
        
        ip_address = request.data.get('ip_address', '').strip()
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        channel = request.data.get('channel', 1)
        camera_name = request.data.get('name', '').strip()
        location = request.data.get('location', '').strip()
        business_id = request.data.get('business_id')
        test_connection = request.data.get('test_connection', False)
        
        # Validation
        if not all([ip_address, username, password, camera_name, business_id]):
            return Response(
                {'error': 'Missing required fields: ip_address, username, password, name, business_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check business access
        try:
            business = Business.objects.get(id=business_id)
            if not self.request.user.is_superuser and business.admin_user != self.request.user:
                return Response(
                    {'error': 'You do not have permission to add cameras to this business'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Business.DoesNotExist:
            return Response(
                {'error': 'Business not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check camera limit
        if not business.can_add_camera():
            return Response(
                {'error': f'Camera limit reached. Maximum {business.subscription.max_cameras} cameras allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build RTSP URL
        try:
            rtsp_url = build_hikvision_rtsp_url(ip_address, username, password, channel)
        except ValueError as e:
            return Response(
                {'error': f'Failed to build Hikvision URL: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Test connection if requested
        if test_connection:
            print(f"Note: Connection testing is skipped for Hikvision cameras to avoid timeouts.")
            print(f"Camera credentials will be validated when streaming begins.")
        
        
        # Create camera
        try:
            camera = Camera.objects.create(
                business=business,
                name=camera_name,
                location=location,
                camera_type='hikvision',
                stream_url=ip_address,
                stream_type='rtsp',
                username=username,
                password=password,
                status='active',
                is_active=True
            )
            
            serializer = CameraSerializer(camera, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Failed to create camera: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update camera status"""
        camera = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Camera.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        camera.status = new_status
        camera.last_active = timezone.now()
        camera.save()
        
        serializer = self.get_serializer(camera)
        return Response(serializer.data)


class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing alerts
    """
    queryset = Alert.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['camera', 'alert_type', 'severity', 'status', 'camera__business']
    search_fields = ['camera__name', 'camera__location']
    ordering_fields = ['created_at', 'severity', 'confidence_score']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AlertCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AlertUpdateSerializer
        return AlertSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Alert.objects.all()
        # Users can only see alerts from their business cameras
        return Alert.objects.filter(camera__business__admin_user=user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent alerts (last 24 hours)"""
        last_24h = timezone.now() - timedelta(hours=24)
        alerts = self.get_queryset().filter(created_at__gte=last_24h)
        
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unacknowledged(self, request):
        """Get all unacknowledged alerts"""
        alerts = self.get_queryset().filter(status='new')
        
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        
        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        alert.status = 'resolved'
        alert.resolution_notes = resolution_notes
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_false_positive(self, request, pk=None):
        """Mark alert as false positive"""
        alert = self.get_object()
        notes = request.data.get('notes', '')
        
        alert.status = 'false_positive'
        alert.resolution_notes = f"False Positive: {notes}"
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get alert statistics"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        alerts = self.get_queryset().filter(created_at__gte=start_date)
        
        stats = {
            'total': alerts.count(),
            'by_status': dict(alerts.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'by_severity': dict(alerts.values('severity').annotate(count=Count('id')).values_list('severity', 'count')),
            'by_type': dict(alerts.values('alert_type').annotate(count=Count('id')).values_list('alert_type', 'count')),
            'average_confidence': alerts.aggregate(avg=Avg('confidence_score'))['avg'],
            'unacknowledged': alerts.filter(status='new').count()
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def queue_for_reprocess(self, request, pk=None):
        """Queue an alert for reprocessing with priority."""
        alert = self.get_object()
        priority = int(request.data.get('priority', 5))  # Default priority 5
        max_attempts = int(request.data.get('max_attempts', 3))
        
        queued_alert = AlertPriorityQueue.enqueue(alert.id, priority=priority, max_attempts=max_attempts)
        
        if queued_alert:
            serializer = self.get_serializer(queued_alert)
            return Response({
                'alert': serializer.data,
                'message': f'Alert queued for reprocessing (priority: {priority})'
            }, status=status.HTTP_202_ACCEPTED)
        
        return Response({'error': 'Alert not found or max attempts exceeded'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def reprocessing_queue(self, request):
        """Get the current reprocessing queue status."""
        summary = AlertPriorityQueue.get_queue_summary()
        queue_count = AlertPriorityQueue.get_queue_count()
        
        return Response({
            'queue_count': queue_count,
            'alerts_by_priority': summary
        })
    
    @action(detail=False, methods=['post'])
    def process_queue(self, request):
        """Process the next alert from the priority queue.
        
        Requires the processor to have models loaded. Typically called
        as part of a background task or separate process.
        """
        next_alert = AlertPriorityQueue.get_next_alert()
        
        if not next_alert:
            return Response({
                'message': 'No alerts in queue'
            }, status=status.HTTP_204_NO_CONTENT)
        
        try:
            # Create a processor instance for the camera
            processor = VideoProcessor(next_alert.camera_id)
            processor.load_models()
            
            # Reprocess the alert
            reprocessed = processor.reprocess_alert_from_queue(next_alert.id)
            
            if reprocessed:
                serializer = self.get_serializer(reprocessed)
                return Response({
                    'alert': serializer.data,
                    'message': f'Alert {next_alert.id} reprocessed successfully',
                    'queue_remaining': AlertPriorityQueue.get_queue_count()
                }, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"❌ Error processing queue: {e}")
            return Response({
                'error': f'Failed to process alert: {str(e)}',
                'queue_remaining': AlertPriorityQueue.get_queue_count()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'error': 'Unknown error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def remove_from_queue(self, request, pk=None):
        """Remove an alert from the reprocessing queue."""
        alert = self.get_object()
        removed = AlertPriorityQueue.dequeue(alert.id)
        
        if removed:
            serializer = self.get_serializer(removed)
            return Response({
                'alert': serializer.data,
                'message': 'Alert removed from queue'
            })
        
        return Response({'error': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)


class ProcessingLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing processing logs
    """
    queryset = ProcessingLog.objects.all()
    serializer_class = ProcessingLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['camera', 'status', 'camera__business']
    ordering_fields = ['started_at', 'frames_processed', 'alerts_generated']
    ordering = ['-started_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ProcessingLog.objects.all()
        return ProcessingLog.objects.filter(camera__business__admin_user=user)
