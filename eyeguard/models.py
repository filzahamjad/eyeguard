from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Subscription(models.Model):
    """Subscription plans for businesses"""
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    max_cameras = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_name_display()} - {self.max_cameras} cameras"
    
    class Meta:
        db_table = 'subscriptions'


class Business(models.Model):
    """Business/Organization using the surveillance system"""
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Subscription details
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT)
    subscription_start_date = models.DateTimeField()
    subscription_end_date = models.DateTimeField()
    is_subscription_active = models.BooleanField(default=True)
    
    # Admin user for this business
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='businesses')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    @property
    def is_valid_subscription(self):
        """Check if subscription is valid and active"""
        if not self.is_subscription_active or not self.is_active:
            return False
        if not self.subscription_end_date:
            return False
        try:
            return self.subscription_end_date > timezone.now()
        except TypeError:
            return False
    
    @property
    def days_until_expiry(self):
        """Days remaining in subscription"""
        if not self.subscription_end_date:
            return 0
        try:
            delta = self.subscription_end_date - timezone.now()
            return max(0, delta.days)
        except TypeError:
            return 0
    
    def can_add_camera(self):
        """Check if business can add more cameras"""
        current_cameras = self.cameras.filter(is_active=True).count()
        return current_cameras < self.subscription.max_cameras
    
    class Meta:
        db_table = 'businesses'
        verbose_name_plural = 'Businesses'


class DetectionModel(models.Model):
    """AI Models available for detection"""
    MODEL_TYPES = [
        ('shoplifting', 'Shoplifting Detection'),
        ('weapon', 'Weapon Detection'),
        ('balaclava', 'Balaclava/Mask Detection'),
        ('motion', 'Motion Detection'),
        ('custom', 'Custom Model'),
    ]
    
    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    model_path = models.CharField(max_length=500, help_text="Path to model weights file")
    confidence_threshold = models.FloatField(default=0.6)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_model_type_display()})"
    
    class Meta:
        db_table = 'detection_models'


class Camera(models.Model):
    """Camera details for each business location"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('error', 'Error'),
    ]
    
    CAMERA_TYPES = [
        ('generic', 'Generic IP Camera'),
        ('hikvision', 'Hikvision'),
        ('dahua', 'Dahua'),
        ('uniview', 'Uniview'),
        ('other', 'Other'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='cameras')
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, help_text="Physical location of camera")
    
    # Camera type
    camera_type = models.CharField(max_length=20, default='generic', choices=CAMERA_TYPES)
    
    # Stream details
    stream_url = models.CharField(max_length=500, help_text="RTSP/HTTP stream URL or video file path")
    stream_type = models.CharField(max_length=20, default='rtsp', choices=[
        ('rtsp', 'RTSP Stream'),
        ('http', 'HTTP Stream'),
        ('file', 'Video File'),
        ('webcam', 'Webcam'),
    ])
    
    # Camera credentials (for IP cameras like Hikvision)
    username = models.CharField(max_length=255, blank=True, null=True, help_text="Camera username for authentication")
    password = models.CharField(max_length=255, blank=True, null=True, help_text="Camera password for authentication")
    channel = models.IntegerField(default=1, help_text="Camera channel number (for multi-channel DVRs, e.g., 1-32)")
    
    # Processing configuration
    target_fps = models.IntegerField(default=10, help_text="Processing FPS (frames per second)")
    motion_confidence = models.FloatField(default=0.6, help_text="Motion detection confidence threshold")
    persist_frames = models.IntegerField(default=5, help_text="Frames to persist before triggering alert")
    
    # Models assigned to this camera
    detection_models = models.ManyToManyField(
        DetectionModel, 
        through='CameraDetectionModel',
        related_name='cameras'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    last_active = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.business.name} - {self.name}"
    
    class Meta:
        db_table = 'cameras'
        unique_together = ['business', 'name']


class CameraDetectionModel(models.Model):
    """Junction table for Camera and DetectionModel with custom settings"""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    detection_model = models.ForeignKey(DetectionModel, on_delete=models.CASCADE)
    confidence_threshold = models.FloatField(
        null=True, 
        blank=True,
        help_text="Override default model confidence threshold for this camera"
    )
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_confidence_threshold(self):
        """Get confidence threshold (camera-specific or model default)"""
        return self.confidence_threshold if self.confidence_threshold else self.detection_model.confidence_threshold
    
    class Meta:
        db_table = 'camera_detection_models'
        unique_together = ['camera', 'detection_model']


class Alert(models.Model):
    """Alert generated by detection models"""
    ALERT_TYPES = [
        ('shoplifting', 'Shoplifting Detected'),
        ('weapon', 'Weapon Detected'),
        ('balaclava', 'Balaclava/Mask Detected'),
        ('motion', 'Motion Detected'),
        ('multiple', 'Multiple Threats'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('acknowledged', 'Acknowledged'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]
    
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Detection details
    detected_objects = models.JSONField(
        default=list,
        help_text="List of detected objects with confidence scores"
    )
    confidence_score = models.FloatField(help_text="Average confidence score")
    
    # Image/Frame details
    frame_image = models.ImageField(
        upload_to='',
        help_text="Annotated frame with detected objects"
    )
    frame_timestamp = models.DateTimeField(help_text="When the frame was captured")
    
    # Alert handling
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Reprocessing queue (priority-based)
    # priority: 1-10 where 10 is highest (critical); default 5 (medium)
    reprocess_priority = models.IntegerField(default=5, help_text="1-10 priority for reprocessing (10=critical)")
    # Whether this alert is queued for reprocessing
    is_queued_for_reprocess = models.BooleanField(default=False)
    # Number of times this alert has been reprocessed
    reprocess_attempts = models.IntegerField(default=0)
    # Last time this alert was reprocessed
    last_reprocessed_at = models.DateTimeField(null=True, blank=True)
    # Timestamp when queued for reprocessing
    queued_for_reprocess_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.camera.name} - {self.get_alert_type_display()} - {self.created_at}"
    
    @property
    def is_recent(self):
        """Check if alert was created in last 24 hours"""
        if not self.created_at:
            return False
        try:
            return (timezone.now() - self.created_at) < timedelta(hours=24)
        except TypeError:
            return False
    
    class Meta:
        db_table = 'alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['camera', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]


class AlertNotification(models.Model):
    """Notification log for alerts sent to users"""
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('webhook', 'Webhook'),
    ]
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    recipient = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient} - {self.sent_at}"
    
    class Meta:
        db_table = 'alert_notifications'


class ProcessingLog(models.Model):
    """Log of processing activity for cameras"""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='processing_logs')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    frames_processed = models.IntegerField(default=0)
    alerts_generated = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, default='running', choices=[
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ])
    
    def __str__(self):
        return f"{self.camera.name} - {self.started_at}"
    
    class Meta:
        db_table = 'processing_logs'
        ordering = ['-started_at']
