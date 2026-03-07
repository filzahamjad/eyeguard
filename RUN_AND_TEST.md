# How to Run and Test EyeGuard (including Live Webcam)

## 1. Prerequisites

- **Python 3.9+**
- **PostgreSQL** (database)
- **Redis** (for WebSockets; optional for dev — you can use in-memory channel layer)
- **YOLO models**: place `.pt` files in `media/models/` (see step 5)

## 2. One-time setup

### 2.1 Virtual environment and dependencies

From the project root (where `manage.py` is):

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate      # macOS/Linux

pip install -r requirements.txt
```

### 2.2 Database

Create a PostgreSQL database named `eyeguard` (or set env vars):

```sql
CREATE DATABASE eyeguard;
```

Optional: set env vars if different from defaults:

- `POSTGRES_DB` (default: `eyeguard`)
- `POSTGRES_USER` (default: `postgres`)
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST` (default: `localhost`)
- `POSTGRES_PORT` (default: `5432`)

Run migrations:

```bash
python manage.py migrate
```

### 2.3 Create a superuser (for login and admin)

```bash
python manage.py createsuperuser
```

Enter username, email, and password. You’ll use this to log in to the live detection page and admin.

### 2.4 Detection models on disk

- Ensure **motion** model exists: `media/models/yolo11n.pt`  
  (download from Ultralytics if needed.)
- Your **custom models** (e.g. from zip files): unzip so you have `.pt` files, e.g.:
  - `media/models/skimask.pt`
  - `media/models/best-custom.pt`

The app does **not** load `.zip` files; only `.pt` files.

### 2.5 Register models in Django (so live detection can use them)

Either use **Django Admin** or the **API**:

**Option A – Django Admin**

1. Start the server (see step 3), open `http://127.0.0.1:8000/admin/`, log in as superuser.
2. Go to **Detection models** → **Add**.
3. For each model, set:
   - **Name** (e.g. `Skimask`, `Best Custom`)
   - **Model type** (e.g. `Balaclava/Mask Detection`, `Custom Model`)
   - **Model path**: filename only, e.g. `skimask.pt`, `best-custom.pt` (must be under `media/models/`).
   - **Confidence threshold** (e.g. `0.6`).
   - **Is active**: checked.
4. Save.

**Option B – API**

```bash
# Get a token first (replace username/password)
curl -X POST http://127.0.0.1:8000/api-token-auth/ -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"yourpassword\"}"

# Create detection model (use the token in Authorization)
curl -X POST http://127.0.0.1:8000/api/detection-models/ -H "Content-Type: application/json" -H "Authorization: Token YOUR_TOKEN" -d "{\"name\":\"Skimask\",\"model_type\":\"balaclava\",\"model_path\":\"skimask.pt\",\"confidence_threshold\":0.6}"
```

### 2.6 WebSockets (Redis vs in-memory)

- **With Redis**: start Redis on `127.0.0.1:6379`. Leave `CHANNEL_LAYERS` in `settings.py` as-is (Redis).
- **Without Redis** (single-process dev): in `eyeguard/settings.py`, comment out the Redis `CHANNEL_LAYERS` and uncomment the in-memory one:

```python
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         ...
#     },
# }
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

Then WebSockets (including live detection) will work without Redis.

---

## 3. Run the server

From the project root:

```bash
python manage.py runserver 0.0.0.0:8000
```

With `daphne` first in `INSTALLED_APPS`, `runserver` uses the ASGI app, so WebSockets work.

Alternatively, run Daphne directly:

```bash
daphne -b 0.0.0.0 -p 8000 eyeguard.asgi:application
```

**When using Daphne:** Static files (admin CSS/JS) are served by WhiteNoise. Run this once (and after adding apps that ship static files):

```bash
python manage.py collectstatic --noinput
```

Server base URL: **http://127.0.0.1:8000/** (or your host/port).

---

## 4. Test the live webcam feature (browser)

### 4.1 Open the live detection page

1. In a browser, go to: **http://127.0.0.1:8000/live-detection/**
2. If not logged in, you’ll be redirected to **http://127.0.0.1:8000/admin/login/**.
3. Log in with your superuser (or any user that can access the app).
4. After login you should land back on **http://127.0.0.1:8000/live-detection/**.

### 4.2 Use the page

1. **Camera ID**: leave empty to use “all active” detection models; or enter a **camera ID** if you created a camera and assigned models to it.
2. **Interval (ms)**: e.g. `300` (send a frame every 300 ms). Higher = fewer FPS, less load.
3. Click **Start camera** and allow browser camera access.
4. Status should show “WebSocket connected” and then “Models loaded” (or “Sending frames” when using a camera ID).
5. You should see:
   - Live video.
   - Green boxes and labels when something is detected (and optionally the annotated image).
   - FPS / frames sent and a short “Detections” summary.

If **no models are loaded**:

- Ensure at least one **Detection model** is created in admin (or via API) and **Is active** is set.
- Ensure the corresponding `.pt` file exists under `media/models/` and **Model path** matches (e.g. `skimask.pt`).

---

## 5. Test the REST live-detect API

Single-image detection over HTTP:

### 5.1 Get a token

```bash
curl -X POST http://127.0.0.1:8000/api-token-auth/ -H "Content-Type: application/json" -d "{\"username\":\"your_username\",\"password\":\"your_password\"}"
```

Use the returned `"token"` value in the next steps.

### 5.2 Send an image (file upload)

```bash
curl -X POST http://127.0.0.1:8000/api/live-detect/ ^
  -H "Authorization: Token YOUR_TOKEN" ^
  -F "image=@path/to/your/image.jpg"
```

Windows CMD: use `^` for line continuation. In PowerShell use backtick `` ` ``; on macOS/Linux use `\`.

Optional body fields (form or JSON when using base64):

- `camera_id`: use that camera’s models.
- `model_ids`: list of detection model IDs, e.g. `[1,2]`.
- `return_annotated`: `true` (default) to get `annotated_image_b64` in the response.

Response example:

```json
{
  "detections": [
    { "label": "BALACLAVA", "confidence": 0.87, "bbox": [100, 50, 200, 150], "type": "balaclava" }
  ],
  "annotated_image_b64": "base64_encoded_jpeg..."
}
```

### 5.3 Send an image as base64 (JSON)

Encode your image to base64, then:

```bash
curl -X POST http://127.0.0.1:8000/api/live-detect/ -H "Authorization: Token YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"image_b64\":\"YOUR_BASE64_STRING\",\"return_annotated\":true}"
```

---

## 6. Test server-side webcam (process_camera)

This uses a **physical webcam** on the machine running Django (no browser):

1. Create a **Camera** in admin (or API) with:
   - **Stream type**: `webcam`
   - **Stream URL**: `0` (first webcam) or `1`, `2`, … for other devices.
   - Assign at least one **detection model** to the camera (via the camera’s “Detection models” / assign_model API).
2. Run:

```bash
python manage.py process_camera <camera_id>
```

Example: `python manage.py process_camera 1`

The process will:

- Open the webcam.
- Run motion detection and your assigned models.
- Create **alerts** when something is detected and broadcast them over WebSockets.

To test with a **video file** instead:

- Create a camera with **Stream type** `file` and **Stream URL** = full path to the video file.
- Run the same command: `python manage.py process_camera <camera_id>`.

---

## 7. Quick checklist

| Step | What to do |
|------|------------|
| 1 | `pip install -r requirements.txt`, `python manage.py migrate`, `createsuperuser` |
| 2 | Put `yolo11n.pt` and your `.pt` models in `media/models/` |
| 3 | In Admin (or API), create at least one **Detection model** (name, type, model_path, active) |
| 4 | Start Redis (or switch to in-memory channel layer for dev) |
| 5 | `python manage.py runserver 0.0.0.0:8000` |
| 6 | Open **http://127.0.0.1:8000/live-detection/** → log in → Start camera |
| 7 | Optional: create a Camera (webcam or file), assign models, run `process_camera <id>` |

---

## 8. Troubleshooting

- **“No detection models available”**  
  Create and activate at least one **Detection model** in admin with correct **model_path** and ensure the `.pt` file exists in `media/models/`.

- **WebSocket closes or “Disconnected”**  
  Ensure Redis is running (or in-memory channel layer is enabled). Use the same host as the page (e.g. `127.0.0.1`) so cookies are sent.

- **Redirect loop or can’t open /live-detection/**  
  Log in at **/admin/login/** first; then open **/live-detection/**. `LOGIN_REDIRECT_URL` is set so you land on the live page after login.

- **Camera permission denied in browser**  
  Use HTTPS or `localhost`/`127.0.0.1`; some browsers block camera on plain HTTP except on localhost.

- **reprocess_frames or live-detect errors about `os`/`cv2`**  
  You should have `import os` and `import cv2` in `views.py`; if not, add them at the top of the file.
