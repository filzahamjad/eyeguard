# Quick Start Guide

Get your surveillance system up and running in 15 minutes!

## Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] PostgreSQL installed and running
- [ ] Git installed
- [ ] YOLO model files available

## Step-by-Step Setup

### 1. Database Setup (5 minutes)

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Run these commands in PostgreSQL:
CREATE DATABASE surveillance_db;
CREATE USER surveillance_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE surveillance_db TO surveillance_user;
\q
```

### 2. Project Setup (5 minutes)

```bash
# Create project directory
mkdir surveillance_system
cd surveillance_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env

# Edit .env file with your database credentials
nano .env  # or use your preferred editor
```

### 3. Django Setup (3 minutes)

```bash
# Run migrations
python manage.py makemigrations surveillance
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Follow prompts to set username and password

# Create media directories
mkdir -p media/models media/alerts
```

### 4. Add Model Files (2 minutes)

```bash
# Copy your YOLO model files to media/models/
cp /path/to/yolo11n.pt media/models/
cp /path/to/shoplifting_wights.pt media/models/
cp /path/to/skimask.pt media/models/
cp /path/to/best-custom.pt media/models/
```

### 5. Start the Server

```bash
# Run development server
python manage.py runserver
```

Visit: http://localhost:8000/admin

## Initial Data Setup

### Option A: Using Django Admin (Recommended for beginners)

1. Go to http://localhost:8000/admin
2. Login with superuser credentials

**Create Subscription Plans:**

- Click "Subscriptions" → "Add Subscription"
- Create plans: Basic (5 cameras), Standard (10 cameras), Premium (25 cameras)

**Create Detection Models:**

- Click "Detection Models" → "Add Detection Model"
- Add all your models (shoplifting, weapon, balaclava)

### Option B: Using Django Shell

```bash
python manage.py shell
```

```python
from eyeguard.models import Subscription, DetectionModel

# Create subscription plans
Subscription.objects.create(
    name='basic',
    max_cameras=5,
    price=99.00,
    features={'storage_days': 7, 'email_alerts': True}
)

Subscription.objects.create(
    name='standard',
    max_cameras=10,
    price=199.00,
    features={'storage_days': 30, 'email_alerts': True, 'sms_alerts': True}
)

# Create detection models
DetectionModel.objects.create(
    name='Shoplifting Detector',
    model_type='shoplifting',
    model_path='shoplifting_wights.pt',
    confidence_threshold=0.6
)

DetectionModel.objects.create(
    name='Weapon Detector',
    model_type='weapon',
    model_path='best-custom.pt',
    confidence_threshold=0.7
)

DetectionModel.objects.create(
    name='Balaclava Detector',
    model_type='balaclava',
    model_path='skimask.pt',
    confidence_threshold=0.6
)

exit()
```

## Test the System

### 1. Create a Test Business via API

```bash
curl -X POST http://localhost:8000/api/businesses/ \
  -H "Content-Type: application/json" \
  -u admin:your_admin_password \
  -d '{
    "name": "Test Store",
    "email": "test@store.com",
    "subscription": 1,
    "subscription_start_date": "2024-02-01T00:00:00Z",
    "subscription_end_date": "2025-02-01T00:00:00Z",
    "admin_username": "teststore_admin",
    "admin_password": "TestPass123!",
    "admin_email": "admin@teststore.com"
  }'
```

### 2. Create a Test Camera

```bash
curl -X POST http://localhost:8000/api/cameras/ \
  -H "Content-Type: application/json" \
  -u admin:your_admin_password \
  -d '{
    "business": 1,
    "name": "Test Camera",
    "location": "Main Entrance",
    "stream_url": "evaluation.mp4",
    "stream_type": "file",
    "target_fps": 10,
    "detection_models_config": [
      {"model_id": 1, "confidence_threshold": 0.6}
    ]
  }'
```

### 3. Start Processing

```bash
# Process the video file
python manage.py process_camera 1 --max-frames 500
```

### 4. View Alerts

Go to: http://localhost:8000/admin/surveillance/alert/

Or via API:

```bash
curl http://localhost:8000/api/alerts/recent/ \
  -u admin:your_admin_password
```

## Common Issues & Solutions

### Issue: "Could not open video stream"

**Solution:**

- Verify the stream URL is correct
- For file: Use full path to video file
- For RTSP: Check network connectivity and credentials

### Issue: "Model file not found"

**Solution:**

- Check model files exist in `media/models/`
- Verify paths in DetectionModel database entries
- Ensure file permissions are correct

### Issue: "Database connection error"

**Solution:**

- Verify PostgreSQL is running: `sudo service postgresql status`
- Check credentials in `.env` file
- Test connection: `psql -U surveillance_user -d surveillance_db`

### Issue: "No alerts being generated"

**Solution:**

- Reduce confidence thresholds (try 0.3-0.4 for testing)
- Check video has motion (people/objects)
- Verify `persist_frames` isn't too high (use 2-3 for testing)

## Next Steps

1. **Configure Real Cameras:**
   - Replace test camera with actual RTSP streams
   - Adjust confidence thresholds based on environment

2. **Setup Notifications:**
   - Configure email settings in `.env`
   - Implement webhook integrations

3. **Production Deployment:**
   - Use Gunicorn/uWSGI for WSGI
   - Setup Nginx as reverse proxy
   - Configure HTTPS with Let's Encrypt
   - Use PostgreSQL in production mode
   - Setup Celery for async processing

4. **Build Frontend:**
   - Use React/Vue/Angular to consume the API
   - Display live camera feeds
   - Show real-time alerts
   - Create dashboards and analytics

## API Documentation

Once running, access API documentation at:

- DRF Browsable API: http://localhost:8000/api/
- Admin Interface: http://localhost:8000/admin/

## Getting Help

- Check `README.md` for detailed documentation
- Review `api_examples.py` for API usage examples
- See `PROJECT_STRUCTURE.md` for architecture details

## Success Checklist

- [ ] Server running at http://localhost:8000
- [ ] Admin accessible at http://localhost:8000/admin
- [ ] Subscriptions created
- [ ] Detection models added
- [ ] Test business created
- [ ] Test camera created
- [ ] Video processing working
- [ ] Alerts being generated
- [ ] Alert images saved in media/alerts/

Congratulations! Your surveillance system is ready! 🎉
