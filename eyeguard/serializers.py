from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Subscription, Business, DetectionModel, Camera, 
    CameraDetectionModel, Alert, AlertNotification, ProcessingLog
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_display = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'name', 'plan_display', 'max_cameras', 
            'price', 'features', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BusinessSerializer(serializers.ModelSerializer):
    subscription_details = SubscriptionSerializer(source='subscription', read_only=True)
    admin_user_details = UserSerializer(source='admin_user', read_only=True)
    is_valid_subscription = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    active_cameras_count = serializers.SerializerMethodField()
    can_add_camera = serializers.SerializerMethodField()
    
    class Meta:
        model = Business
        fields = [
            'id', 'name', 'email', 'phone', 'address',
            'subscription', 'subscription_details',
            'subscription_start_date', 'subscription_end_date',
            'is_subscription_active', 'is_valid_subscription',
            'days_until_expiry', 'active_cameras_count', 'can_add_camera',
            'admin_user', 'admin_user_details',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_active_cameras_count(self, obj):
        return obj.cameras.filter(is_active=True).count()
    
    def get_can_add_camera(self, obj):
        return obj.can_add_camera()


class BusinessCreateSerializer(serializers.ModelSerializer):
    admin_username = serializers.CharField(write_only=True)
    admin_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    admin_email = serializers.EmailField(write_only=True)
    admin_first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Business
        fields = [
            'name', 'email', 'phone', 'address',
            'subscription', 'subscription_start_date', 'subscription_end_date',
            'admin_username', 'admin_password', 'admin_email',
            'admin_first_name', 'admin_last_name'
        ]
    
    def validate(self, data):
        # Check if subscription is valid
        subscription = data.get('subscription')
        if not subscription or not subscription.is_active:
            raise serializers.ValidationError("Selected subscription plan is not active")
        
        # Validate subscription dates
        if data['subscription_end_date'] <= data['subscription_start_date']:
            raise serializers.ValidationError("Subscription end date must be after start date")
        
        return data
    
    def create(self, validated_data):
        # Extract admin user data
        admin_username = validated_data.pop('admin_username')
        admin_password = validated_data.pop('admin_password')
        admin_email = validated_data.pop('admin_email')
        admin_first_name = validated_data.pop('admin_first_name', '')
        admin_last_name = validated_data.pop('admin_last_name', '')
        
        # Create admin user
        admin_user = User.objects.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            first_name=admin_first_name,
            last_name=admin_last_name
        )
        
        # Create business
        validated_data['admin_user'] = admin_user
        business = Business.objects.create(**validated_data)
        
        return business


class DetectionModelSerializer(serializers.ModelSerializer):
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    
    class Meta:
        model = DetectionModel
        fields = [
            'id', 'name', 'model_type', 'model_type_display',
            'model_path', 'confidence_threshold', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CameraDetectionModelSerializer(serializers.ModelSerializer):
    detection_model_details = DetectionModelSerializer(source='detection_model', read_only=True)
    effective_confidence = serializers.SerializerMethodField()
    
    class Meta:
        model = CameraDetectionModel
        fields = [
            'id', 'detection_model', 'detection_model_details',
            'confidence_threshold', 'effective_confidence',
            'is_enabled', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_effective_confidence(self, obj):
        return obj.get_confidence_threshold()


class CameraSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    camera_type_display = serializers.CharField(source='get_camera_type_display', read_only=True)
    stream_type_display = serializers.CharField(source='get_stream_type_display', read_only=True)
    assigned_models = CameraDetectionModelSerializer(
        source='cameradetectionmodel_set', 
        many=True, 
        read_only=True
    )
    recent_alerts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Camera
        fields = [
            'id', 'business', 'business_name', 'name', 'location',
            'camera_type', 'camera_type_display',
            'stream_url', 'stream_type', 'stream_type_display',
            'username', 'password',
            'target_fps', 'motion_confidence', 'persist_frames',
            'assigned_models', 'status', 'status_display',
            'is_active', 'last_active', 'recent_alerts_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_recent_alerts_count(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        last_24h = timezone.now() - timedelta(hours=24)
        return obj.alerts.filter(created_at__gte=last_24h).count()
    
    def validate(self, data):
        # Check if business can add more cameras (only for creation)
        if not self.instance:  # Creating new camera
            business = data.get('business')
            if business and not business.can_add_camera():
                raise serializers.ValidationError(
                    f"Camera limit reached. Your subscription allows maximum "
                    f"{business.subscription.max_cameras} cameras."
                )
        
        return data


class CameraCreateSerializer(serializers.ModelSerializer):
    detection_models_config = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Camera
        fields = [
            'business', 'name', 'location', 'stream_url', 'stream_type',
            'target_fps', 'motion_confidence', 'persist_frames',
            'detection_models_config', 'status'
        ]
    
    def create(self, validated_data):
        detection_models_config = validated_data.pop('detection_models_config', [])
        camera = Camera.objects.create(**validated_data)
        
        # Add detection models
        for model_config in detection_models_config:
            model_id = model_config.get('model_id')
            confidence = model_config.get('confidence_threshold')
            is_enabled = model_config.get('is_enabled', True)
            
            if model_id:
                CameraDetectionModel.objects.create(
                    camera=camera,
                    detection_model_id=model_id,
                    confidence_threshold=confidence,
                    is_enabled=is_enabled
                )
        
        return camera


class AlertSerializer(serializers.ModelSerializer):
    camera_name = serializers.CharField(source='camera.name', read_only=True)
    camera_location = serializers.CharField(source='camera.location', read_only=True)
    business_name = serializers.CharField(source='camera.business.name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    acknowledged_by_details = UserSerializer(source='acknowledged_by', read_only=True)
    is_recent = serializers.BooleanField(read_only=True)
    frame_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'camera', 'camera_name', 'camera_location', 'business_name',
            'alert_type', 'alert_type_display', 'severity', 'severity_display',
            'status', 'status_display', 'detected_objects', 'confidence_score',
            'frame_image', 'frame_image_url', 'frame_timestamp', 'is_recent',
            'acknowledged_by', 'acknowledged_by_details', 'acknowledged_at',
            'resolution_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'frame_image_url']
    
    def get_frame_image_url(self, obj):
        if obj.frame_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.frame_image.url)
            return obj.frame_image.url
        return None


class AlertCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'camera', 'alert_type', 'severity', 'detected_objects',
            'confidence_score', 'frame_image', 'frame_timestamp'
        ]
    
    def validate_camera(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Cannot create alert for inactive camera")
        return value


class AlertUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ['status', 'acknowledged_by', 'acknowledged_at', 'resolution_notes']
    
    def validate(self, data):
        if data.get('status') == 'acknowledged' and not data.get('acknowledged_by'):
            raise serializers.ValidationError(
                "acknowledged_by is required when status is 'acknowledged'"
            )
        return data


class AlertNotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    alert_details = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertNotification
        fields = [
            'id', 'alert', 'alert_details', 'notification_type',
            'notification_type_display', 'recipient', 'sent_at',
            'is_successful', 'error_message'
        ]
        read_only_fields = ['id', 'sent_at']
    
    def get_alert_details(self, obj):
        return {
            'id': obj.alert.id,
            'type': obj.alert.alert_type,
            'camera': obj.alert.camera.name,
            'timestamp': obj.alert.created_at
        }


class ProcessingLogSerializer(serializers.ModelSerializer):
    camera_name = serializers.CharField(source='camera.name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProcessingLog
        fields = [
            'id', 'camera', 'camera_name', 'started_at', 'ended_at',
            'duration_seconds', 'frames_processed', 'alerts_generated',
            'errors', 'status', 'status_display'
        ]
        read_only_fields = ['id']
    
    def get_duration_seconds(self, obj):
        if obj.ended_at:
            return (obj.ended_at - obj.started_at).total_seconds()
        return None
