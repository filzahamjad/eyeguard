# Hikvision Camera Integration - Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────┐          ┌──────────────────────┐          │
│  │  camera_setup.html   │ ◄─────► │  alert_stream.html   │          │
│  │                      │          │                      │          │
│  │ • Setup form         │          │ • Live alerts        │          │
│  │ • Camera list        │          │ • Alert history      │          │
│  │ • Test connection    │          │ • WebSocket stream   │          │
│  └──────────────────────┘          └──────────────────────┘          │
│           │                                   │                       │
│           │ HTTP/API                         │ WebSocket              │
└───────────┼───────────────────────────────────┼───────────────────────┘
            │                                   │
            ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DJANGO BACKEND API                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   views.py                                   │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ CameraViewSet.setup_hikvision()  [POST]               │  │   │
│  │  │                                                        │  │   │
│  │  │ • Validates input credentials                        │  │   │
│  │  │ • Checks business permissions                        │  │   │
│  │  │ • Builds RTSP URL from IP/credentials                │  │   │
│  │  │ • Tests connection if requested                      │  │   │
│  │  │ • Creates Camera record                              │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                                │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ CameraViewSet.list/create/update/delete               │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                                │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ AlertViewSet, BusinessViewSet, other ViewSets         │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   serializers.py                             │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ CameraSerializer                                       │  │   │
│  │  │                                                        │  │   │
│  │  │ • Serializes Camera objects to JSON                   │  │   │
│  │  │ • Includes: id, name, location, IP, username,        │  │   │
│  │  │            password, camera_type, status, etc.       │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   models.py                                  │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ Camera Model (Updated)                                 │  │   │
│  │  │                                                        │  │   │
│  │  │ Fields:                                                │  │   │
│  │  │  • id (PrimaryKey)                                    │  │   │
│  │  │  • business (ForeignKey)                              │  │   │
│  │  │  • name (CharField)                                   │  │   │
│  │  │  • location (CharField)                               │  │   │
│  │  │  • camera_type ⭐ (CharField: hikvision, etc.)      │  │   │
│  │  │  • stream_url (CharField: IP or RTSP URL)           │  │   │
│  │  │  • stream_type (CharField: rtsp, http, etc.)         │  │   │
│  │  │  • username ⭐ (CharField: optional)                 │  │   │
│  │  │  • password ⭐ (CharField: optional)                 │  │   │
│  │  │  • target_fps, motion_confidence, etc.               │  │   │
│  │  │  • status, is_active, timestamps                     │  │   │
│  │  │                                                        │  │   │
│  │  │ ⭐ = New fields added for Hikvision support          │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATABASE                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   cameras table                              │   │
│  │                                                              │   │
│  │  id  │ business_id │ name │ location │ camera_type ⭐    │   │
│  │  ────┼─────────────┼──────┼──────────┼────────────────    │   │
│  │  42  │      1      │Main  │Front Door│  hikvision         │   │
│  │                                                              │   │
│  │  stream_url        │ username ⭐ │ password ⭐ │ status  │   │
│  │  ──────────────────┼─────────────┼──────────────┼─────── │   │
│  │  192.168.1.100     │   admin     │  pass123    │ active  │   │
│  │                                                              │   │
│  │  is_active │ target_fps │ motion_confidence │ timestamps  │   │
│  │  ──────────┼────────────┼───────────────────┼─────────── │   │
│  │    true    │     10     │       0.6         │ created_at │   │
│  │                                                              │   │
│  │ ⭐ = New fields added                                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│ User enters credentials in camera_setup.html                          │
│  - Camera Name: "Main Entrance"                                       │
│  - IP Address: "192.168.1.100"                                        │
│  - Username: "admin"                                                  │
│  - Password: "password123"                                            │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ JavaScript sends POST to /api/cameras/setup_hikvision/                │
│ with Authorization header and credential data                         │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Django CameraViewSet.setup_hikvision() [views.py]                     │
│                                                                       │
│ 1. Parse request data (IP, username, password, etc.)                 │
│ 2. Validate business permissions                                     │
│ 3. Check camera limit for subscription                               │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Call build_hikvision_rtsp_url() [video_processor.py]                  │
│                                                                       │
│ Input:  - ip_address: "192.168.1.100"                               │
│         - username: "admin"                                          │
│         - password: "password123"                                    │
│         - channel: 1                                                 │
│                                                                       │
│ Processing:                                                           │
│  • URL-encode username and password for special chars                │
│  • Build URL: rtsp://admin:password123@192.168.1.100:554/...         │
│                                                                       │
│ Output: "rtsp://admin:password123@192.168.1.100:554/...              │
│          Streaming/Channels/1"                                       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    Optional: Test Connection ──┐
                                │               │
                                │               ▼
                                │         ┌──────────────────────┐
                                │         │ cv2.VideoCapture()   │
                                │         │ cap.read()           │
                                │         │ Test frame decode    │
                                │         └──────────────────────┘
                                │               │
                                ▼               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Create Camera record in database [models.py]                          │
│                                                                       │
│ camera = Camera.objects.create(                                      │
│     business=business,                                               │
│     name="Main Entrance",                                            │
│     location="Front Door",                                           │
│     camera_type="hikvision",                    ⭐ New              │
│     stream_url="192.168.1.100",                 ⭐ Modified         │
│     stream_type="rtsp",                                              │
│     username="admin",                           ⭐ New              │
│     password="password123",                     ⭐ New              │
│     status="active",                                                 │
│     is_active=True                                                   │
│ )                                                                     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Serialize Camera object using CameraSerializer [serializers.py]       │
│                                                                       │
│ Returns JSON:                                                         │
│ {                                                                     │
│   "id": 42,                                                           │
│   "name": "Main Entrance",                                           │
│   "location": "Front Door",                                          │
│   "camera_type": "hikvision",          ⭐ New                       │
│   "camera_type_display": "Hikvision",  ⭐ New                       │
│   "stream_url": "192.168.1.100",       ⭐ Modified                  │
│   "username": "admin",                 ⭐ New                       │
│   "password": "password123",           ⭐ New                       │
│   "business": 1,                                                      │
│   "status": "active",                                                 │
│   "is_active": true,                                                  │
│   "created_at": "2025-02-28T...",                                    │
│   "updated_at": "2025-02-28T..."                                     │
│ }                                                                     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Return Response with Camera ID to frontend                            │
│ Status: 201 Created                                                   │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ camera_setup.html receives response                                   │
│  • Shows success message                                              │
│  • Clears form                                                        │
│  • Updates cameras list                                               │
│  • Navigates to "My Cameras" tab                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Video Stream Access Flow

```
Later when video processing occurs:

┌──────────────────────────────────┐
│ VideoProcessor.initialize()      │
│ (when streaming starts)          │
└────────────────┬─────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ VideoProcessor.initialize_video_capture()                    │
│ (video_processor.py)                                         │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ Check if camera_type == 'hikvision'                          │
│ and username/password are available                          │
└────────────────┬─────────────────────────────────────────────┘
                 │ YES
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ Call build_hikvision_rtsp_url()                              │
│ Generate full RTSP URL with embedded credentials             │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ cv2.VideoCapture(rtsp_url)                                   │
│ Connect to Hikvision camera                                  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ Read frames, perform motion detection                        │
│ Run YOLO detection models                                    │
│ Generate alerts on detections                                │
└──────────────────────────────────────────────────────────────┘
```

## Component Interaction Diagram

```
                ┌─────────────────────┐
                │   Hikvision Camera  │
                │  192.168.1.100:554  │
                └──────────┬──────────┘
                           │ RTSP Stream
                           │
                ┌──────────▼──────────┐
                │  cv2.VideoCapture   │
                │ (OpenCV)            │
                └──────────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │   Motion   │  │   YOLO     │  │   Custom   │
    │ Detection  │  │ Detection  │  │   Models   │
    │   Model    │  │   Models   │  │            │
    └────────────┘  └────────────┘  └────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                   ┌─────────────────┐
                   │ Alert Priority  │
                   │ Queue           │
                   └────────┬────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
        ┌────────┐     ┌────────┐     ┌────────┐
        │Database│     │ WebSocket │  │ Email  │
        │ Alert  │     │ Broadcast  │  │Notify  │
        │Records │     │            │  │        │
        └────────┘     └────────┘     └────────┘
```

## Key Design Decisions

### 1. Store IP Address in `stream_url`

- **Why**: Maintains backward compatibility
- **How**: For Hikvision, we store just the IP (192.168.1.100)
- **Benefit**: Users see their camera IP in the admin, not the full RTSP URL

### 2. Separate Username/Password Fields

- **Why**: Allow future encryption at rest
- **How**: Added dedicated fields: `username`, `password`
- **Benefit**: Can apply encryption without changing URLs

### 3. URL Building at Runtime

- **Why**: Credentials are never exposed in URLs or logs
- **How**: Build RTSP URL only when opening video capture
- **Benefit**: Reduces security surface area

### 4. Optional Connection Testing

- **Why**: Verify camera is accessible before creating record
- **How**: Test frame read on setup
- **Benefit**: User gets immediate feedback on connectivity issues

### 5. Extensible Camera Types

- **Why**: Easy to add Dahua, Uniview, other brands
- **How**: camera_type choices can be extended
- **Benefit**: Same framework for all IP cameras

## Security Architecture

```
User Input
    │
    ▼
URL Encoding (special char handling)
    │
    ▼
HTTP/HTTPS Transport (Django)
    │
    ▼
Database Storage
    │
    ├─ Recommendations:
    │  • Add field encryption (django-encrypted-model-fields)
    │  • Use HTTPS in production
    │  • Implement credential rotation
    │  • Add audit logging for credential access
    │  • Use environment variables for sensitive settings
    │
    ▼
RTSP Generation (on-demand)
    │
    ▼
Camera Connection (SSL/TLS optional)
    │
    ▼
Video Stream Processing
```

---

## File Dependencies

```
camera_setup.html
    │
    ├─ Calls: POST /api/cameras/setup_hikvision/
    ├─ Calls: GET /api/cameras/
    ├─ Calls: DELETE /api/cameras/{id}/
    │
    └─ Requires: api_token (stored in localStorage)

views.py (setup_hikvision endpoint)
    │
    ├─ Imports: build_hikvision_rtsp_url from video_processor
    ├─ Uses: Business, Camera models
    ├─ Uses: CameraSerializer
    ├─ Uses: cv2 for connection testing
    │
    └─ Validates: business permissions, camera limits

video_processor.py
    │
    ├─ Contains: build_hikvision_rtsp_url() function
    ├─ Uses: urllib.parse.quote for URL encoding
    ├─ Uses: cv2.VideoCapture for testing
    │
    └─ Called by: initialize_video_capture() method

models.py
    │
    ├─ Camera model with fields:
    │  • camera_type (hikvision, dahua, etc.)
    │  • username, password
    │  • stream_url, stream_type
    │
    └─ Related Tables: Business, DetectionModel, CameraDetectionModel

serializers.py
    │
    ├─ CameraSerializer includes:
    │  • camera_type, camera_type_display
    │  • username, password
    │  • All standard camera fields
    │
    └─ Used by: views for JSON responses

migrations/0003_*.py
    │
    ├─ Adds: camera_type, username, password columns
    │
    └─ Applied: python manage.py migrate eyeguard
```

---

## Testing Checklist

- [ ] Database migration applied successfully
- [ ] Django system checks pass
- [ ] Can access camera_setup.html
- [ ] Can authenticate with API token
- [ ] Can select business from dropdown
- [ ] Can fill all required fields
- [ ] Connection test successfully verifies Hikvision camera
- [ ] Camera record created in database
- [ ] Camera appears in "My Cameras" list
- [ ] Can delete camera
- [ ] Video processor can read stream from Hikvision camera
- [ ] Alerts trigger on motion/detection
- [ ] Special characters in password are URL-encoded correctly
- [ ] Multi-channel support works (channel 1, 2, etc.)
