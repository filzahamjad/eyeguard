"""
WebSocket routing configuration for django-channels.
Defines URL patterns for WebSocket connections.
"""

from django.urls import re_path
from eyeguard.consumers import AlertConsumer, LiveDetectionConsumer

websocket_urlpatterns = [
    # Superuser-only: all alerts
    re_path(r'ws/alerts/all/$', AlertConsumer.as_asgi()),
    
    # Business alerts
    re_path(r'ws/alerts/business/(?P<scope_id>\d+)/$', AlertConsumer.as_asgi()),
    
    # Camera alerts
    re_path(r'ws/alerts/camera/(?P<scope_id>\d+)/$', AlertConsumer.as_asgi()),

    # Live detection: optional camera_id in URL
    re_path(r'ws/live-detection/$', LiveDetectionConsumer.as_asgi()),
    re_path(r'ws/live-detection/(?P<camera_id>\d+)/$', LiveDetectionConsumer.as_asgi()),
]
