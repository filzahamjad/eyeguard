from django.contrib import admin
from django.urls import path, reverse
from django.http import StreamingHttpResponse, HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import messages
import threading
import cv2

from .models import (
    Subscription, Business, DetectionModel, Camera,
    CameraDetectionModel, Alert, AlertNotification, ProcessingLog
)

# In-process registry shared with views.py — import the same dict object.
from .views import _active_processors


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_cameras', 'price', 'is_active', 'created_at']
    list_filter = ['is_active', 'name']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'subscription', 'is_subscription_active',
        'subscription_end_date', 'days_until_expiry', 'is_active'
    ]
    list_filter = ['is_active', 'is_subscription_active', 'subscription']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at', 'updated_at', 'is_valid_subscription', 'days_until_expiry']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'phone', 'address', 'admin_user')
        }),
        ('Subscription', {
            'fields': (
                'subscription', 'subscription_start_date', 'subscription_end_date',
                'is_subscription_active', 'is_valid_subscription', 'days_until_expiry'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(DetectionModel)
class DetectionModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'confidence_threshold', 'is_active', 'created_at']
    list_filter = ['is_active', 'model_type']
    search_fields = ['name', 'description']
    ordering = ['model_type', 'name']


class CameraDetectionModelInline(admin.TabularInline):
    model = CameraDetectionModel
    extra = 1
    fields = ['detection_model', 'confidence_threshold', 'is_enabled']


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'business', 'location', 'camera_type', 'status', 'stream_type',
        'is_active', 'last_active', 'processing_controls',
    ]
    list_filter = ['status', 'is_active', 'stream_type', 'business', 'camera_type']
    search_fields = ['name', 'location', 'business__name']
    readonly_fields = ['created_at', 'updated_at', 'processing_controls', 'live_stream_preview']
    ordering = ['-created_at']
    inlines = [CameraDetectionModelInline]
    change_list_template = "admin/eyeguard/camera/change_list.html"
    change_form_template = "admin/eyeguard/camera/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('setup-hikvision/', self.admin_site.admin_view(self.hikvision_setup_view), name='eyeguard_cameras_setup_hikvision'),
            path('<int:camera_id>/start-processing/', self.admin_site.admin_view(self.start_processing_view), name='eyeguard_camera_start_processing'),
            path('<int:camera_id>/stop-processing/', self.admin_site.admin_view(self.stop_processing_view), name='eyeguard_camera_stop_processing'),
            path('<int:camera_id>/stream/', self.admin_site.admin_view(self.stream_view), name='eyeguard_camera_stream'),
        ]
        return custom_urls + urls

    def hikvision_setup_view(self, request):
        from django.shortcuts import render
        return render(request, "admin/eyeguard/camera_setup.html")

    def start_processing_view(self, request, camera_id):
        """Start process_camera in a background thread for this camera."""
        from .video_processor import VideoProcessor
        entry = _active_processors.get(camera_id)
        if entry and entry['thread'].is_alive():
            messages.warning(request, f"Camera {camera_id} is already processing.")
        else:
            processor = VideoProcessor(camera_id)

            def _run():
                try:
                    processor.run()
                except Exception as exc:
                    print(f"[camera {camera_id}] processing error: {exc}")
                finally:
                    _active_processors.pop(camera_id, None)

            t = threading.Thread(target=_run, daemon=True, name=f'cam-proc-{camera_id}')
            _active_processors[camera_id] = {'thread': t, 'processor': processor}
            t.start()
            messages.success(request, f"Started processing for camera {camera_id}.")

        return HttpResponseRedirect(
            reverse('admin:eyeguard_camera_change', args=[camera_id])
        )

    def stop_processing_view(self, request, camera_id):
        """Stop a running process_camera thread."""
        entry = _active_processors.get(camera_id)
        if entry and entry['thread'].is_alive():
            entry['processor'].stop_event.set()
            messages.success(request, f"Stop requested for camera {camera_id}.")
        else:
            messages.warning(request, f"Camera {camera_id} is not currently processing.")

        return HttpResponseRedirect(
            reverse('admin:eyeguard_camera_change', args=[camera_id])
        )

    def stream_view(self, request, camera_id):
        """MJPEG stream endpoint for embedding in the admin change form."""
        try:
            camera = Camera.objects.get(pk=camera_id)
        except Camera.DoesNotExist:
            from django.http import Http404
            raise Http404

        from .video_processor import build_hikvision_rtsp_url

        stream_url = camera.stream_url
        if camera.camera_type == 'hikvision' and camera.username and camera.password:
            try:
                stream_url = build_hikvision_rtsp_url(
                    ip_address=camera.stream_url,
                    username=camera.username,
                    password=camera.password,
                    channel=camera.channel,
                )
            except Exception:
                pass

        def _frames():
            if camera.stream_type == 'webcam':
                idx = int(stream_url) if str(stream_url).isdigit() else 0
                cap = cv2.VideoCapture(idx)
            else:
                cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                return
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if not ok:
                        continue
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n'
                        + buf.tobytes()
                        + b'\r\n'
                    )
            finally:
                cap.release()

        return StreamingHttpResponse(
            _frames(),
            content_type='multipart/x-mixed-replace; boundary=frame',
        )

    # ── Display helpers ────────────────────────────────────────────────

    def _is_running(self, camera_id):
        entry = _active_processors.get(camera_id)
        return bool(entry and entry['thread'].is_alive())

    def processing_controls(self, obj):
        """Shown in both the list view and the change form."""
        running = self._is_running(obj.pk)
        start_url = reverse('admin:eyeguard_camera_start_processing', args=[obj.pk])
        stop_url  = reverse('admin:eyeguard_camera_stop_processing',  args=[obj.pk])
        stream_url = reverse('admin:eyeguard_camera_stream', args=[obj.pk])

        if running:
            badge = '<span style="color:green;font-weight:bold">● Running</span>'
            btn   = f'<a href="{stop_url}" class="button" style="background:#ba2121;color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none;margin-right:6px">■ Stop</a>'
        else:
            badge = '<span style="color:#888">● Stopped</span>'
            btn   = f'<a href="{start_url}" class="button" style="background:#417690;color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none;margin-right:6px">▶ Start</a>'

        stream_btn = (
            f'<a href="{stream_url}" target="_blank" '
            f'style="background:#0a7;color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none">'
            f'📷 Stream</a>'
        )
        return format_html('{} {} {}', format_html(badge), format_html(btn), format_html(stream_btn))

    processing_controls.short_description = 'Processing'
    processing_controls.allow_tags = True

    def live_stream_preview(self, obj):
        """Embedded live stream in the change form (iframe around MJPEG)."""
        stream_url = reverse('admin:eyeguard_camera_stream', args=[obj.pk])
        return format_html(
            '<img src="{}" style="max-width:640px;max-height:480px;border:1px solid #ccc;" '
            'onerror="this.style.display=\'none\'" />',
            stream_url,
        )

    live_stream_preview.short_description = 'Live Preview'

    fieldsets = (
        ('Basic Information', {
            'fields': ('business', 'name', 'location', 'camera_type')
        }),
        ('Stream Configuration', {
            'fields': ('stream_url', 'stream_type', 'target_fps', 'username', 'password', 'channel')
        }),
        ('Detection Configuration', {
            'fields': ('motion_confidence', 'persist_frames')
        }),
        ('Processing Controls', {
            'fields': ('processing_controls', 'live_stream_preview'),
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'last_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        'camera', 'alert_type', 'severity', 'status',
        'confidence_score', 'frame_timestamp', 'created_at'
    ]
    list_filter = ['alert_type', 'severity', 'status', 'created_at']
    search_fields = ['camera__name', 'camera__business__name']
    readonly_fields = ['created_at', 'updated_at', 'is_recent']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('camera', 'alert_type', 'severity', 'status')
        }),
        ('Detection Details', {
            'fields': ('detected_objects', 'confidence_score', 'frame_image', 'frame_timestamp')
        }),
        ('Resolution', {
            'fields': ('acknowledged_by', 'acknowledged_at', 'resolution_notes')
        }),
        ('Metadata', {
            'fields': ('is_recent', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('camera', 'camera__business', 'acknowledged_by')


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'alert', 'notification_type', 'recipient',
        'is_successful', 'sent_at'
    ]
    list_filter = ['notification_type', 'is_successful', 'sent_at']
    search_fields = ['recipient', 'alert__camera__name']
    readonly_fields = ['sent_at']
    ordering = ['-sent_at']


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = [
        'camera', 'started_at', 'ended_at', 'status',
        'frames_processed', 'alerts_generated'
    ]
    list_filter = ['status', 'started_at']
    search_fields = ['camera__name', 'camera__business__name']
    ordering = ['-started_at']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('camera', 'camera__business')
