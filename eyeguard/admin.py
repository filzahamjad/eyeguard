from django.contrib import admin
from .models import (
    Subscription, Business, DetectionModel, Camera,
    CameraDetectionModel, Alert, AlertNotification, ProcessingLog
)


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


from django.urls import path

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'business', 'location', 'camera_type', 'status', 'stream_type',
        'is_active', 'last_active'
    ]
    list_filter = ['status', 'is_active', 'stream_type', 'business', 'camera_type']
    search_fields = ['name', 'location', 'business__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    inlines = [CameraDetectionModelInline]
    change_list_template = "admin/eyeguard/camera/change_list.html"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('setup-hikvision/', self.admin_site.admin_view(self.hikvision_setup_view), name='eyeguard_cameras_setup_hikvision'),
        ]
        return custom_urls + urls

    def hikvision_setup_view(self, request):
        from django.shortcuts import render
        return render(request, "admin/eyeguard/camera_setup.html")
    
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
