"""
ASGI config for eyeguard project with WebSocket support via django-channels.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyeguard.settings')

# Initialize Django ASGI application early to ensure AppRegistry
from django.core.asgi import get_asgi_application

django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from eyeguard.routing import websocket_urlpatterns

django_asgi_app = get_asgi_application()

# Channels ASGI application with protocol routing
application = ProtocolTypeRouter({
    # HTTP and WebSocket requests
    'http': django_asgi_app,
    
    # WebSocket requests with authentication
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
