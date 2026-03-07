# Project Structure

```
surveillance_project/
│
├── surveillance/                      # Main Django app
│   ├── __init__.py
│   ├── models.py                     # Database models (Business, Camera, Alert, etc.)
│   ├── serializers.py                # DRF serializers for API
│   ├── views.py                      # API ViewSets
│   ├── urls.py                       # URL routing
│   ├── admin.py                      # Django admin configuration
│   ├── permissions.py                # Custom permissions
│   ├── video_processor.py            # Video processing service
│   │
│   ├── management/
│   │   └── commands/
│   │       └── process_camera.py     # Django command to process camera
│   │
│   └── migrations/
│       └── (auto-generated)
│
├── media/                            # Media files storage
│   ├── alerts/                       # Alert images (organized by date)
│   │   └── YYYY/MM/DD/
│   │       └── alert_*.jpg
│   └── models/                       # YOLO model files
│       ├── yolo11n.pt
│       ├── shoplifting_wights.pt
│       ├── skimask.pt
│       └── best-custom.pt
│
├── config/                           # Project configuration
│   ├── __init__.py
│   ├── settings.py                   # Django settings
│   ├── urls.py                       # Main URL configuration
│   └── wsgi.py                       # WSGI configuration
│
├── requirements.txt                  # Python dependencies
├── .env.template                     # Environment variables template
├── README.md                         # Project documentation
├── api_examples.py                   # API usage examples
└── manage.py                         # Django management script
```

## Directory Descriptions

### `/surveillance/`

Main Django application containing all business logic, models, and API endpoints.

### `/media/alerts/`

Stores captured alert images organized by date (YYYY/MM/DD). Each alert image contains:

- Annotated frame with bounding boxes
- Detection labels and confidence scores
- Timestamp

### `/media/models/`

Contains YOLO model weight files:

- `yolo11n.pt` - Motion detection (YOLO11 nano)
- `shoplifting_wights.pt` - Shoplifting detection
- `skimask.pt` - Balaclava/mask detection
- `best-custom.pt` - Weapon detection

### `/config/`

Django project configuration files.

## Key Files

| File                 | Purpose                                                       |
| -------------------- | ------------------------------------------------------------- |
| `models.py`          | Database schema (Subscription, Business, Camera, Alert, etc.) |
| `serializers.py`     | API data serialization/deserialization                        |
| `views.py`           | API endpoints and business logic                              |
| `video_processor.py` | Video stream processing and detection                         |
| `permissions.py`     | API access control                                            |
| `admin.py`           | Django admin interface configuration                          |
| `urls.py`            | API routing configuration                                     |

## Data Flow

```
┌──────────────┐
│ CCTV Stream  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│  video_processor.py          │
│  ┌────────────────────────┐  │
│  │ 1. Motion Detection    │  │
│  │    (YOLO11n)          │  │
│  └────────┬───────────────┘  │
│           │                  │
│           ▼                  │
│  ┌────────────────────────┐  │
│  │ 2. If motion persists: │  │
│  │    - Shoplifting       │  │
│  │    - Weapon            │  │
│  │    - Balaclava         │  │
│  └────────┬───────────────┘  │
│           │                  │
│           ▼                  │
│  ┌────────────────────────┐  │
│  │ 3. Annotate Frame     │  │
│  └────────┬───────────────┘  │
└───────────┼──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  models.py - Alert.create()  │
│  - Save to database          │
│  - Save annotated image      │
│  - Record metadata           │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  API (views.py)              │
│  - GET alerts                │
│  - Acknowledge               │
│  - Resolve                   │
└──────────────────────────────┘
```

## Database Schema

```
┌─────────────────┐
│  Subscription   │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────┴────────┐
│    Business     │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────┴────────┐       N ┌──────────────────┐
│     Camera      │◄────────┤ DetectionModel   │
└────────┬────────┘         └──────────────────┘
         │ 1              (through CameraDetectionModel)
         │
         │ N
┌────────┴────────┐
│     Alert       │
└─────────────────┘
```

## API Architecture

```
Client (Frontend/Mobile)
         │
         ▼
┌─────────────────────┐
│   REST API          │
│   (urls.py)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   ViewSets          │
│   (views.py)        │
│   - BusinessViewSet │
│   - CameraViewSet   │
│   - AlertViewSet    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Serializers       │
│ (serializers.py)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Models            │
│   (models.py)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Database          │
│   (PostgreSQL)      │
└─────────────────────┘
```
