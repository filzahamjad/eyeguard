# WebSocket Real-Time Alert Streaming

## Implementation Complete ✅

Real-time alert broadcasting via WebSocket has been integrated into EyeGuard. Alerts are now pushed to connected clients immediately when created, without polling.

## What's New

### Files Created

- `eyeguard/consumers.py` — WebSocket consumer for alert streaming
- `eyeguard/routing.py` — WebSocket routing configuration
- `alert_stream.html` — Beautiful test/demo interface
- `WEBSOCKET_SETUP.md` — Complete setup guide
- `SETUP_WEBSOCKET.sh` — Quick-start script

### Files Modified

- `eyeguard/asgi.py` — Added Channels protocol router
- `eyeguard/settings.py` — Added Channels configuration
- `eyeguard/video_processor.py` — Alert broadcasting on creation
- `requirements.txt` — Added channels, channels-redis, daphne

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Services (in separate terminals)

**Terminal 1: Redis**

```bash
redis-server
# Or: docker run -d -p 6379:6379 redis:latest
```

**Terminal 2: Django with Daphne (ASGI)**

```bash
daphne -b 0.0.0.0 -p 8000 eyeguard.asgi:application
```

**Terminal 3: Start Video Processing**

```bash
python3 manage.py process_camera 1 --max-frames 500
```

### 3. Test Alerts in Browser

1. Open `alert_stream.html` in a browser
2. Get your API token:
   ```bash
   python3 manage.py shell
   >>> from rest_framework.authtoken.models import Token
   >>> from django.contrib.auth.models import User
   >>> user = User.objects.first()
   >>> token, _ = Token.objects.get_or_create(user=user)
   >>> print(token.key)
   ```
3. Paste token into the HTML form and click "Connect"
4. Watch alerts appear in real-time as video processing detects objects!

## WebSocket Endpoints

| Endpoint                                       | Description     | Access         |
| ---------------------------------------------- | --------------- | -------------- |
| `ws://localhost:8000/ws/alerts/all/`           | All alerts      | Superuser only |
| `ws://localhost:8000/ws/alerts/business/{id}/` | Business alerts | Business staff |
| `ws://localhost:8000/ws/alerts/camera/{id}/`   | Camera alerts   | Camera owner   |

## Architecture

```
Video Processing (Main Thread)
    ↓
Alert Created
    ├→ Save to DB
    ├→ Create Confirmation Thread
    └→ Broadcast via async_to_sync(broadcast_alert)
                    ↓
        Channel Layer (Redis)
                    ↓
        Group: alerts_all, alerts_business_X, alerts_camera_Y
                    ↓
        Connected WebSocket Clients
                    ↓
        Real-time UI Update (Browser/App)
```

## Message Format

### Alert Created

```json
{
  "type": "alert_created",
  "alert": {
    "id": 123,
    "alert_type": "weapon",
    "severity": "critical",
    "status": "new",
    "confidence_score": 0.95,
    "detected_objects": [...],
    "created_at": "2026-02-13T..."
  },
  "timestamp": "..."
}
```

### Alert Updated (Reprocessing, Status Change)

```json
{
  "type": "alert_updated",
  "alert": {
    "id": 123,
    "status": "investigating",
    "resolution_notes": "...",
    "reprocess_attempts": 1
  },
  "timestamp": "..."
}
```

## Client Examples

### Browser (JavaScript)

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/ws/alerts/camera/1/?token=YOUR_TOKEN",
);
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log("Alert:", data.alert);
};
```

### Python

```python
import asyncio
import websockets
import json

async def listen():
    uri = 'ws://localhost:8000/ws/alerts/camera/1/?token=YOUR_TOKEN'
    async with websockets.connect(uri) as ws:
        async for msg in ws:
            print(json.loads(msg))

asyncio.run(listen())
```

## Configuration

### Development (In-Memory, Single Process)

```python
# settings.py
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

### Production (Redis, Multi-Process)

```python
# settings.py
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

## Features

- ✅ Real-time alert broadcasting
- ✅ Group-based access control (all, business, camera)
- ✅ User authentication via token
- ✅ Alert lifecycle events (created, updated)
- ✅ Keep-alive ping/pong
- ✅ Beautiful HTML demo interface
- ✅ Production-ready with Redis backend

## Performance Notes

- Alerts are broadcast asynchronously using `async_to_sync()` (non-blocking)
- Main video processing loop continues unaffected
- Redis channel layer handles thousands of concurrent connections
- Each user only receives alerts they have access to (permission checks in consumer)

## Troubleshooting

| Issue                        | Solution                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| `Connection refused`         | Ensure Daphne is running (not `runserver`)                                         |
| `Groups error`               | Check Redis is running: `redis-cli ping`                                           |
| `No alerts received`         | Verify WebSocket connected in browser console                                      |
| `Token authentication fails` | Get fresh token and include in URL: `?token=...`                                   |
| `Connection drops after 60s` | Add keep-alive: `setInterval(() => ws.send(JSON.stringify({type:'ping'})), 30000)` |

## Next Steps (Optional Enhancements)

- [ ] Add typing indicator when processing (optional feature)
- [ ] Implement alert filters on client side (by type, severity)
- [ ] Add alert history/pagination via REST API
- [ ] Implement alert acknowledgment via WebSocket
- [ ] Deploy with docker-compose for production
- [ ] Add Nginx reverse proxy config for SSL/TLS

See `WEBSOCKET_SETUP.md` for full documentation and examples.
