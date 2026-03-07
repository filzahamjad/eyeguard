# WebSocket Real-Time Alerts - Quick Reference

## Setup (5 Minutes)

```bash
# 1. Install dependencies
pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0

# 2. Start Redis (Terminal 1)
redis-server

# 3. Start Django ASGI server (Terminal 2)
daphne -b 0.0.0.0 -p 8000 eyeguard.asgi:application

# 4. Start video processing (Terminal 3)
python3 manage.py process_camera 1 --max-frames 500

# 5. Open alert_stream.html in browser, enter token, click Connect!
```

## Get Your Token

```bash
python3 manage.py shell
>>> from rest_framework.authtoken.models import Token
>>> from django.contrib.auth.models import User
>>> user = User.objects.first()
>>> token, _ = Token.objects.get_or_create(user=user)
>>> print(token.key)
abcdef1234567890...
```

## WebSocket Endpoints

```
ws://localhost:8000/ws/alerts/all/?token=YOUR_TOKEN
ws://localhost:8000/ws/alerts/business/1/?token=YOUR_TOKEN
ws://localhost:8000/ws/alerts/camera/1/?token=YOUR_TOKEN
```

## Browser JavaScript

```javascript
const token = "YOUR_TOKEN";
const ws = new WebSocket(
  `ws://localhost:8000/ws/alerts/camera/1/?token=${token}`,
);

ws.onopen = () => console.log("Connected!");
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log(data.type, data.alert || data.message);
};
ws.onerror = (e) => console.error("Error:", e);
ws.onclose = () => console.log("Disconnected");

// Keep alive
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  }
}, 30000);
```

## Python Client

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

## Alert Messages

### Alert Created

```json
{
  "type": "alert_created",
  "alert": {
    "id": 123,
    "alert_type": "weapon",
    "severity": "critical",
    "confidence_score": 0.95,
    "detected_objects": [...],
    "created_at": "..."
  }
}
```

### Alert Updated

```json
{
  "type": "alert_updated",
  "alert": {
    "id": 123,
    "status": "investigating",
    "reprocess_attempts": 1,
    "resolution_notes": "..."
  }
}
```

## Troubleshooting

| Issue                   | Fix                                          |
| ----------------------- | -------------------------------------------- |
| `Connection refused`    | Use `daphne`, not `runserver`                |
| `Groups error`          | Ensure Redis is running: `redis-cli ping`    |
| `Authentication failed` | Include token in URL: `?token=YOUR_TOKEN`    |
| `Disconnects after 60s` | Add keep-alive ping (see JavaScript example) |

## Architecture

```
Alert Created → Broadcast via async_to_sync
                    ↓
            Redis Channel Layer
                    ↓
        Groups: alerts_all, alerts_business_X, alerts_camera_Y
                    ↓
        WebSocket Consumers (Connected Clients)
                    ↓
        Real-time UI Update
```

## Files

- `eyeguard/consumers.py` - WebSocket consumer
- `eyeguard/routing.py` - URL routing
- `eyeguard/asgi.py` - ASGI config (updated)
- `eyeguard/settings.py` - Channels config (updated)
- `alert_stream.html` - Test interface
- `requirements.txt` - Dependencies (updated)

## Permissions

| Scope      | Can Access     | URL                         |
| ---------- | -------------- | --------------------------- |
| All Alerts | Superusers     | `/ws/alerts/all/`           |
| Business   | Business staff | `/ws/alerts/business/{id}/` |
| Camera     | Camera owner   | `/ws/alerts/camera/{id}/`   |

## Features

✅ Real-time broadcasting (no polling)
✅ Group-based access control
✅ Token authentication
✅ alert_created and alert_updated events
✅ Keep-alive ping/pong
✅ Redis backend (production-ready)
✅ Beautiful HTML test interface
