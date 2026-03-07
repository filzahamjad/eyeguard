# CCTV Surveillance System - Django Backend

A comprehensive Django-based surveillance system with AI-powered detection for shoplifting, weapons, and suspicious behavior.

## Features

- **Business Management**: Multi-tenant system with subscription-based access
- **Camera Management**: Support for RTSP streams, HTTP streams, video files, and webcams
- **AI Detection Models**:
  - Motion detection
  - Shoplifting detection
  - Weapon detection
  - Balaclava/mask detection
  - Custom model support
- **Alert System**: Real-time alerts with image capture and metadata
- **REST API**: Complete API for integration with frontend applications
- **Dashboard**: Business analytics and monitoring

## System Architecture

```
┌─────────────────┐
│  CCTV Streams   │
│  (RTSP/HTTP)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Video Processor │
│  (YOLO Models)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Alert System   │
│  (Save Images)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Django API    │
│  (REST/Admin)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Database     │
│ (PostgreSQL)    │
└─────────────────┘
```

## Installation

### 1. Prerequisites

- Python 3.9 or higher
- PostgreSQL (recommended) or MySQL
- CUDA-capable GPU (optional, for faster processing)

### 2. Clone Repository

```bash
git clone <your-repo-url>
cd surveillance_project
```

### 3. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Database Setup

Create a PostgreSQL database:

```sql
CREATE DATABASE surveillance_db;
CREATE USER surveillance_user WITH PASSWORD 'your_password';
ALTER ROLE surveillance_user SET client_encoding TO 'utf8';
ALTER ROLE surveillance_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE surveillance_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE surveillance_db TO surveillance_user;
```

### 6. Configure Django Settings

Update your `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'surveillance_db',
        'USER': 'surveillance_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 7. Run Migrations

```bash
python manage.py makemigrations surveillance
python manage.py migrate
```

### 8. Create Superuser

```bash
python manage.py createsuperuser
```

### 9. Setup YOLO Models

Create a `media/models/` directory and place your YOLO model files:

```bash
mkdir -p media/models
# Copy your model files:
# - yolo11n.pt (motion detection)
# - shoplifting_wights.pt
# - skimask.pt (balaclava detection)
# - best-custom.pt (weapon detection)
```

### 10. Run Development Server

```bash
python manage.py runserver
```

## API Endpoints

### Authentication

First, obtain a token:

```bash
curl -X POST http://localhost:8000/api-auth/login/ \
  -d "username=admin&password=your_password"
```

### Business Management

#### Create Business

```bash
POST /api/businesses/
{
    "name": "Retail Store ABC",
    "email": "admin@retailabc.com",
    "phone": "+1234567890",
    "address": "123 Main St, City, State",
    "subscription": 1,
    "subscription_start_date": "2024-01-01T00:00:00Z",
    "subscription_end_date": "2024-12-31T23:59:59Z",
    "admin_username": "retailabc_admin",
    "admin_password": "secure_password",
    "admin_email": "admin@retailabc.com"
}
```

#### Validate Subscription

```bash
POST /api/businesses/{id}/validate_subscription/
```

#### Get Business Dashboard

```bash
GET /api/businesses/{id}/dashboard/?days=7
```

### Camera Management

#### Create Camera

```bash
POST /api/cameras/
{
    "business": 1,
    "name": "Front Entrance Camera",
    "location": "Main Entrance - Floor 1",
    "stream_url": "rtsp://192.168.1.100:554/stream",
    "stream_type": "rtsp",
    "target_fps": 10,
    "motion_confidence": 0.6,
    "persist_frames": 5,
    "detection_models_config": [
        {
            "model_id": 1,
            "confidence_threshold": 0.6,
            "is_enabled": true
        },
        {
            "model_id": 2,
            "confidence_threshold": 0.7,
            "is_enabled": true
        }
    ]
}
```

#### Assign Detection Model

```bash
POST /api/cameras/{id}/assign_model/
{
    "model_id": 1,
    "confidence_threshold": 0.6,
    "is_enabled": true
}
```

#### Get Camera Alerts

```bash
GET /api/cameras/{id}/alerts/?days=7&status=new&severity=high
```

### Alert Management

#### List Alerts

```bash
GET /api/alerts/?camera=1&status=new&severity=critical
```

#### Get Recent Alerts (last 24h)

```bash
GET /api/alerts/recent/
```

#### Acknowledge Alert

```bash
POST /api/alerts/{id}/acknowledge/
```

#### Resolve Alert

```bash
POST /api/alerts/{id}/resolve/
{
    "resolution_notes": "False alarm, maintenance staff"
}
```

#### Mark as False Positive

```bash
POST /api/alerts/{id}/mark_false_positive/
{
    "notes": "Shadow triggered detection"
}
```

#### Get Alert Statistics

```bash
GET /api/alerts/statistics/?days=30
```

## Video Processing

### Process Camera Stream

Use the Django management command:

```bash
# Continuous processing
python manage.py process_camera <camera_id>

# Process specific number of frames
python manage.py process_camera <camera_id> --max-frames 1000
```

### Programmatic Processing

```python
from surveillance.video_processor import start_camera_processing

# Start processing
start_camera_processing(camera_id=1, max_frames=None)
```

## Database Models

### Core Models

1. **Subscription**: Subscription plans (Basic, Standard, Premium, Enterprise)
2. **Business**: Organizations using the system
3. **DetectionModel**: AI models for detection
4. **Camera**: Camera configurations
5. **Alert**: Generated alerts with images
6. **ProcessingLog**: Processing activity logs

### Relationships

```
Business (1) ─── (N) Camera
Business (N) ─── (1) Subscription
Camera (N) ─── (N) DetectionModel [through CameraDetectionModel]
Camera (1) ─── (N) Alert
Camera (1) ─── (N) ProcessingLog
```

## Alert Image Storage

Alert images are automatically saved in:

```
media/alerts/YYYY/MM/DD/alert_YYYYMMDD_HHMMSS_index.jpg
```

The database stores:

- File path (in `frame_image` field)
- Detected objects with bounding boxes (JSON)
- Confidence scores
- Timestamp

## Example Usage Flow

### 1. Setup Initial Data

```python
# Create subscription plans
from surveillance.models import Subscription

Subscription.objects.create(
    name='basic',
    max_cameras=5,
    price=99.00,
    features={'storage_days': 7, 'email_alerts': True}
)

# Create detection models
from surveillance.models import DetectionModel

DetectionModel.objects.create(
    name='Shoplifting Detector',
    model_type='shoplifting',
    model_path='shoplifting_wights.pt',
    confidence_threshold=0.6
)
```

### 2. Create Business via API

```bash
curl -X POST http://localhost:8000/api/businesses/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Store",
    "email": "contact@mystore.com",
    "subscription": 1,
    "subscription_start_date": "2024-01-01T00:00:00Z",
    "subscription_end_date": "2024-12-31T23:59:59Z",
    "admin_username": "store_admin",
    "admin_password": "password123",
    "admin_email": "admin@mystore.com"
  }'
```

### 3. Add Camera

```bash
curl -X POST http://localhost:8000/api/cameras/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "business": 1,
    "name": "Entrance Camera",
    "location": "Main Entrance",
    "stream_url": "evaluation.mp4",
    "stream_type": "file",
    "detection_models_config": [
      {"model_id": 1, "confidence_threshold": 0.6}
    ]
  }'
```

### 4. Start Processing

```bash
python manage.py process_camera 1
```

### 5. Monitor Alerts

```bash
# Get all new alerts
curl http://localhost:8000/api/alerts/?status=new \
  -H "Authorization: Token YOUR_TOKEN"

# Get business dashboard
curl http://localhost:8000/api/businesses/1/dashboard/ \
  -H "Authorization: Token YOUR_TOKEN"
```

## Production Deployment

### Using Gunicorn

```bash
gunicorn myproject.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Using Celery for Async Processing

Update settings:

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

Create Celery tasks for video processing:

```python
# tasks.py
from celery import shared_task
from surveillance.video_processor import start_camera_processing

@shared_task
def process_camera_async(camera_id):
    start_camera_processing(camera_id)
```

## Security Considerations

1. **Authentication**: Use token-based authentication for API
2. **HTTPS**: Always use HTTPS in production
3. **Database**: Use strong passwords and restrict access
4. **File Upload**: Validate and sanitize all file uploads
5. **CORS**: Configure CORS properly for your frontend domain
6. **Secrets**: Use environment variables for sensitive data

## Troubleshooting

### Camera Stream Won't Open

- Verify stream URL is correct
- Check network connectivity
- Ensure camera supports the protocol (RTSP/HTTP)
- Test with VLC media player first

### Models Not Loading

- Check model file paths in database
- Ensure model files exist in `media/models/`
- Verify file permissions

### Low Performance

- Reduce `target_fps` in camera settings
- Use GPU acceleration (CUDA)
- Optimize model confidence thresholds
- Process fewer cameras simultaneously

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub or contact support.
