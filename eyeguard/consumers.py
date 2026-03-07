"""
WebSocket consumers for real-time alert streaming and live detection.

Handles client connections and broadcasts alerts when they're created.
LiveDetectionConsumer: browser sends frames, backend runs YOLO and returns detections.
Uses django-channels for async WebSocket support.
"""

import asyncio
import json
import logging
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from eyeguard.models import Alert, Camera, Business
from eyeguard.serializers import AlertSerializer
from eyeguard.detection_helper import (
    load_detection_models_for_live,
    run_detection_on_frame,
    decode_image_from_bytes,
    decode_image_from_base64,
)

logger = logging.getLogger(__name__)

# Throttle: min interval between processing frames (seconds)
LIVE_DETECTION_THROTTLE_INTERVAL = 0.25  # ~4 FPS max per connection


class AlertConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time alert streaming.
    
    Groups:
    - 'alerts_all': All alerts (for admins/superusers)
    - 'alerts_business_{business_id}': Alerts for specific business
    - 'alerts_camera_{camera_id}': Alerts for specific camera
    
    Examples:
    - Connect to all alerts: ws://localhost/ws/alerts/all/
    - Connect to business alerts: ws://localhost/ws/alerts/business/1/
    - Connect to camera alerts: ws://localhost/ws/alerts/camera/1/
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')
        self.scope_type = self.scope.get('url_route', {}).get('kwargs', {}).get('scope_type')
        self.scope_id = self.scope.get('url_route', {}).get('kwargs', {}).get('scope_id')
        
        # Validate user is authenticated
        if not self.user or not self.user.is_authenticated:
            await self.close()
            logger.warning("Unauthenticated WebSocket connection attempt")
            return
        
        # Determine which groups to subscribe to
        self.groups_to_join = []
        
        if self.scope_type == 'all':
            # Only superusers can subscribe to all alerts
            if self.user.is_superuser:
                self.groups_to_join.append('alerts_all')
            else:
                logger.warning(f"User {self.user.username} attempted to subscribe to all alerts")
                await self.close()
                return
        
        elif self.scope_type == 'business':
            # Users can subscribe to their own business alerts
            business_id = self.scope_id
            if await self._can_access_business(business_id):
                self.groups_to_join.append(f'alerts_business_{business_id}')
            else:
                logger.warning(f"User {self.user.username} attempted unauthorized access to business {business_id}")
                await self.close()
                return
        
        elif self.scope_type == 'camera':
            # Users can subscribe to their own camera alerts
            camera_id = self.scope_id
            if await self._can_access_camera(camera_id):
                self.groups_to_join.append(f'alerts_camera_{camera_id}')
            else:
                logger.warning(f"User {self.user.username} attempted unauthorized access to camera {camera_id}")
                await self.close()
                return
        
        else:
            logger.warning(f"Invalid scope_type: {self.scope_type}")
            await self.close()
            return
        
        # Join groups and accept connection
        for group in self.groups_to_join:
            await self.channel_layer.group_add(group, self.channel_name)
        
        await self.accept()
        logger.info(f"User {self.user.username} connected to alert groups: {self.groups_to_join}")
        
        # Send confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to alerts ({", ".join(self.groups_to_join)})',
            'timestamp': self._timestamp()
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        for group in self.groups_to_join:
            await self.channel_layer.group_discard(group, self.channel_name)
        logger.info(f"User {self.user.username} disconnected (code: {close_code})")
    
    async def receive(self, text_data):
        """Handle incoming messages (ping/pong for keep-alive)."""
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': self._timestamp()
                }))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {self.user.username}")
    
    async def alert_created(self, event):
        """
        Receive alert_created event from channel layer.
        Called when a new alert is broadcast to the group.
        """
        alert_data = event.get('alert_data')
        
        await self.send(text_data=json.dumps({
            'type': 'alert_created',
            'alert': alert_data,
            'timestamp': self._timestamp()
        }))
    
    async def alert_updated(self, event):
        """
        Receive alert_updated event from channel layer.
        Called when an alert is updated (status change, reprocessing, etc).
        """
        alert_data = event.get('alert_data')
        
        await self.send(text_data=json.dumps({
            'type': 'alert_updated',
            'alert': alert_data,
            'timestamp': self._timestamp()
        }))
    
    @database_sync_to_async
    def _can_access_business(self, business_id):
        """Check if user can access a business."""
        if self.user.is_superuser:
            return True
        try:
            Business.objects.get(id=business_id, admin_user=self.user)
            return True
        except Business.DoesNotExist:
            return False
    
    @database_sync_to_async
    def _can_access_camera(self, camera_id):
        """Check if user can access a camera."""
        if self.user.is_superuser:
            return True
        try:
            Camera.objects.get(id=camera_id, business__admin_user=self.user)
            return True
        except Camera.DoesNotExist:
            return False
    
    @staticmethod
    def _timestamp():
        """Get ISO format timestamp."""
        from django.utils import timezone
        return timezone.now().isoformat()


class LiveDetectionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for browser-based live detection.
    Client sends frames (binary or base64 in JSON); server runs detection models and returns
    detections and optional annotated image.

    Routes:
    - ws/live-detection/          -> send first message with { camera_id: N } or { model_ids: [1,2] }, then send frames
    - ws/live-detection/<id>/    -> models loaded for camera <id> on connect; send frames only
    """

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            logger.warning("Unauthenticated live-detection WebSocket attempt")
            return

        self.camera_id = self.scope.get('url_route', {}).get('kwargs', {}).get('camera_id')
        self.model_infos = None
        self.last_process_time = 0
        self._executor = getattr(self.channel_layer, '_thread_pool', None)  # optional

        if self.camera_id is not None:
            try:
                camera_id_int = int(self.camera_id)
            except (TypeError, ValueError):
                await self.close()
                return
            if not await self._can_access_camera(camera_id_int):
                logger.warning(f"User {self.user.username} unauthorized for camera {camera_id_int}")
                await self.close()
                return
            # Load models in thread to avoid blocking
            self.model_infos = await asyncio.to_thread(
                load_detection_models_for_live, camera_id=camera_id_int, model_ids=None
            )
            if not self.model_infos:
                logger.warning(f"No detection models loaded for camera {camera_id_int}")

        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Live detection ready. Send frames (binary or JSON with image_b64).',
            'camera_id': self.camera_id,
            'models_loaded': self.model_infos is not None and len(self.model_infos) > 0,
            'timestamp': timezone.now().isoformat(),
        }))

    async def disconnect(self, close_code):
        self.model_infos = None
        logger.info(f"Live detection disconnected: {self.user.username} (code={close_code})")

    async def receive(self, text_data=None, bytes_data=None):
        now = time.monotonic()
        # Config message (only when no camera_id in URL and models not yet loaded)
        if text_data and not bytes_data and self.camera_id is None and self.model_infos is None:
            try:
                data = json.loads(text_data)
                camera_id = data.get('camera_id')
                model_ids = data.get('model_ids')
                if camera_id is not None:
                    cid = int(camera_id)
                    if not await self._can_access_camera(cid):
                        await self.send(text_data=json.dumps({
                            'type': 'error', 'message': 'Unauthorized for this camera',
                            'timestamp': timezone.now().isoformat(),
                        }))
                        return
                    self.model_infos = await asyncio.to_thread(
                        load_detection_models_for_live, camera_id=cid, model_ids=None
                    )
                elif model_ids is not None:
                    self.model_infos = await asyncio.to_thread(
                        load_detection_models_for_live, camera_id=None, model_ids=model_ids
                    )
                else:
                    # Load all active models
                    self.model_infos = await asyncio.to_thread(
                        load_detection_models_for_live, camera_id=None, model_ids=None
                    )
                await self.send(text_data=json.dumps({
                    'type': 'ready',
                    'models_loaded': len(self.model_infos) if self.model_infos else 0,
                    'timestamp': timezone.now().isoformat(),
                }))
            except Exception as e:
                logger.exception(e)
                await self.send(text_data=json.dumps({
                    'type': 'error', 'message': str(e),
                    'timestamp': timezone.now().isoformat(),
                }))
            return

        # Frame: need models loaded
        if not self.model_infos:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Send camera_id or model_ids first to load models.',
                'timestamp': timezone.now().isoformat(),
            }))
            return

        # Throttle
        if now - self.last_process_time < LIVE_DETECTION_THROTTLE_INTERVAL:
            return
        self.last_process_time = now

        # Decode image
        frame = None
        if bytes_data:
            frame = decode_image_from_bytes(bytes_data)
        elif text_data:
            try:
                data = json.loads(text_data)
                b64 = data.get('image_b64') or data.get('image')
                if b64:
                    frame = decode_image_from_base64(b64)
            except (json.JSONDecodeError, TypeError):
                pass
        if frame is None:
            await self.send(text_data=json.dumps({
                'type': 'error', 'message': 'Invalid or missing image data',
                'timestamp': timezone.now().isoformat(),
            }))
            return

        # Run detection in thread
        try:
            result = await asyncio.to_thread(
                run_detection_on_frame,
                frame,
                self.model_infos,
                return_annotated=True,
            )
        except Exception as e:
            logger.exception(e)
            await self.send(text_data=json.dumps({
                'type': 'error', 'message': str(e),
                'timestamp': timezone.now().isoformat(),
            }))
            return

        await self.send(text_data=json.dumps({
            'type': 'detection',
            'detections': result['detections'],
            'annotated_image_b64': result.get('annotated_image_b64'),
            'timestamp': timezone.now().isoformat(),
        }))

    @database_sync_to_async
    def _can_access_camera(self, camera_id):
        if self.user.is_superuser:
            return True
        try:
            Camera.objects.get(id=camera_id, business__admin_user=self.user)
            return True
        except Camera.DoesNotExist:
            return False


# Helper function to broadcast alerts
async def broadcast_alert(alert, event_type='alert_created'):
    """
    Broadcast an alert to connected WebSocket clients.
    
    Args:
        alert: Alert instance
        event_type: 'alert_created' or 'alert_updated'
    """
    from channels.layers import get_channel_layer
    
    try:
        # Serialize alert data
        serializer = AlertSerializer(alert)
        alert_data = serializer.data
        
        channel_layer = get_channel_layer()
        
        # Broadcast to all alerts group (superusers)
        await channel_layer.group_send(
            'alerts_all',
            {
                'type': event_type,
                'alert_data': alert_data
            }
        )
        
        # Broadcast to business group
        await channel_layer.group_send(
            f'alerts_business_{alert.camera.business_id}',
            {
                'type': event_type,
                'alert_data': alert_data
            }
        )
        
        # Broadcast to camera group
        await channel_layer.group_send(
            f'alerts_camera_{alert.camera_id}',
            {
                'type': event_type,
                'alert_data': alert_data
            }
        )
        
        logger.info(f"Broadcasted {event_type} for alert {alert.id}")
    except Exception as e:
        logger.error(f"Failed to broadcast alert {alert.id}: {e}")
