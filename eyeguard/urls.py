from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionViewSet,
    BusinessViewSet,
    DetectionModelViewSet,
    CameraViewSet,
    AlertViewSet,
    ProcessingLogViewSet,
    live_detect,
    LiveDetectionPageView,
    email_token_auth,
)
from rest_framework.authtoken import views as drf_authtoken_views

router = DefaultRouter()
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'businesses', BusinessViewSet, basename='business')
router.register(r'detection-models', DetectionModelViewSet, basename='detection-model')
router.register(r'cameras', CameraViewSet, basename='camera')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'processing-logs', ProcessingLogViewSet, basename='processing-log')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('camera-setup/', TemplateView.as_view(template_name='camera_setup.html'), name='camera_setup'),
    path('live-detection/', LiveDetectionPageView.as_view(), name='live-detection'),
    path('api/live-detect/', live_detect),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-token-auth/', drf_authtoken_views.obtain_auth_token),
    path('api-email-token-auth/', email_token_auth),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API Endpoints:
# 
# SUBSCRIPTIONS:
# GET    /api/subscriptions/              - List all active subscription plans
# GET    /api/subscriptions/{id}/         - Get subscription details
# GET    /api/subscriptions/{id}/features/ - Get subscription features
#
# BUSINESSES:
# GET    /api/businesses/                 - List businesses (filtered by user)
# POST   /api/businesses/                 - Create new business with admin user
# GET    /api/businesses/{id}/            - Get business details
# PUT    /api/businesses/{id}/            - Update business
# PATCH  /api/businesses/{id}/            - Partial update business
# DELETE /api/businesses/{id}/            - Delete business
# POST   /api/businesses/{id}/validate_subscription/ - Validate subscription status
# GET    /api/businesses/{id}/dashboard/  - Get business dashboard stats
#
# DETECTION MODELS:
# GET    /api/detection-models/           - List all active detection models
# POST   /api/detection-models/           - Create new detection model
# GET    /api/detection-models/{id}/      - Get model details
# PUT    /api/detection-models/{id}/      - Update model
# PATCH  /api/detection-models/{id}/      - Partial update model
# DELETE /api/detection-models/{id}/      - Delete model
#
# CAMERAS:
# GET    /api/cameras/                    - List cameras (filtered by business)
# POST   /api/cameras/                    - Create new camera
# GET    /api/cameras/{id}/               - Get camera details
# PUT    /api/cameras/{id}/               - Update camera
# PATCH  /api/cameras/{id}/               - Partial update camera
# DELETE /api/cameras/{id}/               - Delete camera
# POST   /api/cameras/{id}/assign_model/  - Assign detection model to camera
# DELETE /api/cameras/{id}/remove_model/  - Remove detection model from camera
# GET    /api/cameras/{id}/alerts/        - Get camera alerts (with filters)
# POST   /api/cameras/{id}/update_status/ - Update camera status
#
# ALERTS:
# GET    /api/alerts/                     - List all alerts (filtered by business)
# POST   /api/alerts/                     - Create new alert
# GET    /api/alerts/{id}/                - Get alert details
# PUT    /api/alerts/{id}/                - Update alert
# PATCH  /api/alerts/{id}/                - Partial update alert
# DELETE /api/alerts/{id}/                - Delete alert
# GET    /api/alerts/recent/              - Get alerts from last 24 hours
# GET    /api/alerts/unacknowledged/      - Get unacknowledged alerts
# POST   /api/alerts/{id}/acknowledge/    - Acknowledge an alert
# POST   /api/alerts/{id}/resolve/        - Resolve an alert
# POST   /api/alerts/{id}/mark_false_positive/ - Mark as false positive
# GET    /api/alerts/statistics/          - Get alert statistics
#
# PROCESSING LOGS:
# GET    /api/processing-logs/            - List processing logs
# POST   /api/processing-logs/            - Create processing log
# GET    /api/processing-logs/{id}/       - Get log details
