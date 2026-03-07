# WebSocket Setup for Real-Time Alerts

## Overview

Real-time alert streaming via WebSocket using `django-channels`. Alerts are broadcast to connected clients as soon as they're created, without polling.

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
# Or manually:
pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0
```

### 2. Start Redis (Required for Channel Layer)

```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 redis:latest

# Or using Homebrew on macOS
brew install redis
redis-server
```

### 3. Run Server with Daphne (ASGI)

Instead of `python manage.py runserver`, use Daphne for WebSocket support:

```bash
daphne -b 0.0.0.0 -p 8000 eyeguard.asgi:application
```

Or use a production ASGI server:

```bash
# Uvicorn
uvicorn eyeguard.asgi:application --host 0.0.0.0 --port 8000

# Hypercorn
hypercorn eyeguard.asgi:application --bind 0.0.0.0:8000
```

## WebSocket Endpoints

### All Alerts (Superuser Only)

```
ws://localhost:8000/ws/alerts/all/
```

### Business Alerts

```
ws://localhost:8000/ws/alerts/business/{business_id}/
```

### Camera Alerts

```
ws://localhost:8000/ws/alerts/camera/{camera_id}/
```

## Authentication

WebSocket connections require a valid Django user token in the URL or headers:

```javascript
const token = "YOUR_AUTH_TOKEN";
const ws = new WebSocket(
  `ws://localhost:8000/ws/alerts/camera/1/?token=${token}`,
);
```

Or via headers (Daphne supports this):

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/alerts/camera/1/");
ws.onopen = () => {
  // Send token after connection
  ws.send(JSON.stringify({ type: "authenticate", token }));
};
```

## Client Examples

### JavaScript/Browser

```javascript
// Connect to camera alerts
const ws = new WebSocket(
  "ws://localhost:8000/ws/alerts/camera/1/?token=YOUR_TOKEN",
);

ws.onopen = (event) => {
  console.log("Connected to alert stream");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "alert_created") {
    console.log("New alert:", data.alert);
    // Update UI with new alert
    displayAlert(data.alert);
  } else if (data.type === "alert_updated") {
    console.log("Alert updated:", data.alert);
    // Update alert in UI
    updateAlert(data.alert);
  } else if (data.type === "connection_established") {
    console.log(data.message);
  }
};

ws.onerror = (event) => {
  console.error("WebSocket error:", event);
};

ws.onclose = (event) => {
  console.log("Disconnected from alert stream");
  // Reconnect after delay
  setTimeout(() => location.reload(), 5000);
};

// Keep connection alive with ping
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  }
}, 30000);
```

### Python Client

```python
import asyncio
import json
import websockets
from aiohttp import ClientSession

async def listen_to_alerts(token, camera_id=1):
    """Listen to real-time alerts via WebSocket."""
    uri = f'ws://localhost:8000/ws/alerts/camera/{camera_id}/?token={token}'

    async with websockets.connect(uri) as websocket:
        print(f"Connected to alert stream for camera {camera_id}")

        async for message in websocket:
            data = json.loads(message)

            if data['type'] == 'alert_created':
                print(f"🚨 New alert: {data['alert']['alert_type']}")
                print(f"   Severity: {data['alert']['severity']}")
                print(f"   Confidence: {data['alert']['confidence_score']}")

            elif data['type'] == 'alert_updated':
                print(f"📝 Alert {data['alert']['id']} updated: {data['alert']['status']}")

            elif data['type'] == 'connection_established':
                print(f"✅ {data['message']}")

# Run
asyncio.run(listen_to_alerts('YOUR_TOKEN'))
```

### Node.js with Socket.IO (Client Library)

```javascript
const io = require("socket.io-client");

const socket = io("http://localhost:8000", {
  path: "/socket.io/",
  auth: { token: "YOUR_TOKEN" },
});

socket.on("alert_created", (alert) => {
  console.log("New alert:", alert);
});

socket.on("alert_updated", (alert) => {
  console.log("Alert updated:", alert);
});

socket.on("disconnect", () => {
  console.log("Disconnected, reconnecting...");
});
```

## Message Format

### Connection Established

```json
{
  "type": "connection_established",
  "message": "Connected to alerts (alerts_camera_1)",
  "timestamp": "2026-02-13T10:30:00.123456Z"
}
```

### Alert Created

```json
{
  "type": "alert_created",
  "alert": {
    "id": 123,
    "camera": 1,
    "alert_type": "weapon",
    "severity": "critical",
    "status": "new",
    "detected_objects": [
      {
        "label": "Weapon Detector",
        "confidence": 0.95,
        "bbox": [100, 150, 200, 250]
      }
    ],
    "confidence_score": 0.95,
    "frame_timestamp": "2026-02-13T10:30:00.123456Z",
    "created_at": "2026-02-13T10:30:00.123456Z"
  },
  "timestamp": "2026-02-13T10:30:00.123456Z"
}
```

### Alert Updated

```json
{
  "type": "alert_updated",
  "alert": {
    "id": 123,
    "status": "investigating",
    "resolution_notes": "Auto-confirmation: 2/5 frames matched...",
    "reprocess_attempts": 1,
    "last_reprocessed_at": "2026-02-13T10:30:05.123456Z"
  },
  "timestamp": "2026-02-13T10:30:05.123456Z"
}
```

### Ping/Pong (Keep-Alive)

Client sends:

```json
{ "type": "ping" }
```

Server responds:

```json
{ "type": "pong", "timestamp": "..." }
```

## Access Control

| Scope           | URL                         | Allowed Users                 |
| --------------- | --------------------------- | ----------------------------- |
| All Alerts      | `/ws/alerts/all/`           | Superusers only               |
| Business Alerts | `/ws/alerts/business/{id}/` | Business admin + staff        |
| Camera Alerts   | `/ws/alerts/camera/{id}/`   | Camera owner's business staff |

## Configuration

### In-Memory Channel Layer (Development)

For single-process development without Redis:

```python
# settings.py
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

**Note:** This only works with a single worker process. For production, use Redis.

### Redis Channel Layer (Production)

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

## Troubleshooting

### WebSocket Connection Refused

- Ensure Daphne (or similar ASGI server) is running, not `runserver`
- Check that Redis is running (if using RedisChannelLayer)
- Verify the URL and token are correct

### "Groups" Error

- Make sure `CHANNEL_LAYERS` is configured in settings.py
- Redis must be running if using RedisChannelLayer

### Alerts Not Broadcasting

- Check that alert creation is happening (look for "ALERT CREATED" in logs)
- Verify WebSocket client is connected (should see "Connected to alert stream")
- Check Django logs for "Broadcasted alert_created"

### Connection Drops Frequently

- Add keep-alive ping/pong mechanism (see JavaScript example)
- Increase Daphne timeout: `daphne -b 0.0.0.0 -p 8000 --timeout 120 ...`

## Production Deployment

### Using Gunicorn + Daphne

```bash
# ASGI worker for WebSockets
daphne -b 0.0.0.0 -p 8001 eyeguard.asgi:application

# WSGI workers for HTTP (optional, REST API)
gunicorn eyeguard.wsgi:application -b 0.0.0.0:8000 -w 4

# Reverse proxy (Nginx)
upstream daphne {
    server 127.0.0.1:8001;
}
upstream gunicorn {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.eyeguard.local;

    # WebSocket
    location /ws/ {
        proxy_pass http://daphne;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # HTTP API
    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
    }
}
```

### Docker Compose Example

```yaml
version: "3.8"

services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: eyeguard
      POSTGRES_USER: eyeguard
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"

  eyeguard:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 eyeguard.asgi:application
    ports:
      - "8000:8000"
    environment:
      DEBUG: "False"
      DJANGO_SETTINGS_MODULE: eyeguard.settings
      DATABASE_URL: postgresql://eyeguard:secure_password@db:5432/eyeguard
    depends_on:
      - db
      - redis
```

## Files Modified/Created

- `eyeguard/consumers.py` — WebSocket consumer for alerts
- `eyeguard/routing.py` — WebSocket routing configuration
- `eyeguard/asgi.py` — Updated for Channels
- `eyeguard/settings.py` — Added Channels configuration
- `eyeguard/video_processor.py` — Alert broadcasting on creation
- `requirements.txt` — Added channels, channels-redis, daphne
