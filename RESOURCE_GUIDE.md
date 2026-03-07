# 📖 EyeGuard Hikvision Integration - Complete Resource Guide

## Quick Navigation

### 🎯 **I want to...**

#### Add a Camera to EyeGuard

→ Open: [camera_setup.html](camera_setup.html) or use the admin link (Cameras → "Hikvision Setup")
→ Read: [HIKVISION_SETUP.md](HIKVISION_SETUP.md)

#### Understand How the System Works

→ Read: [ARCHITECTURE_HIKVISION.md](ARCHITECTURE_HIKVISION.md)

#### Learn Technical Implementation Details

→ Read: [IMPLEMENTATION_SUMMARY_HIKVISION.md](IMPLEMENTATION_SUMMARY_HIKVISION.md)

#### Use the API Programmatically

→ Read: [QUICK_START_HIKVISION.sh](QUICK_START_HIKVISION.sh)
→ Section: API Examples

#### Get Started Quickly

→ Read: [README_HIKVISION_COMPLETE.md](README_HIKVISION_COMPLETE.md)

#### Troubleshoot Issues

→ Read: [HIKVISION_SETUP.md](HIKVISION_SETUP.md)
→ Section: Troubleshooting

#### Check Database Schema

→ View: [eyeguard/models.py](eyeguard/models.py)
→ Class: Camera Model

#### View API Implementation

→ View: [eyeguard/views.py](eyeguard/views.py)
→ Method: CameraViewSet.setup_hikvision()

#### Understand Video Processing

→ View: [eyeguard/video_processor.py](eyeguard/video_processor.py)
→ Function: build_hikvision_rtsp_url()

---

## 📚 Documentation Files

### Primary Documentation

| File                                                                       | Purpose                           | Best For                 |
| -------------------------------------------------------------------------- | --------------------------------- | ------------------------ |
| [README_HIKVISION_COMPLETE.md](README_HIKVISION_COMPLETE.md)               | Complete overview and quick start | First-time users         |
| [HIKVISION_SETUP.md](HIKVISION_SETUP.md)                                   | Step-by-step setup guide          | Setting up cameras       |
| [ARCHITECTURE_HIKVISION.md](ARCHITECTURE_HIKVISION.md)                     | System architecture and diagrams  | Understanding the system |
| [IMPLEMENTATION_SUMMARY_HIKVISION.md](IMPLEMENTATION_SUMMARY_HIKVISION.md) | Technical implementation details  | Developers               |
| [QUICK_START_HIKVISION.sh](QUICK_START_HIKVISION.sh)                       | API examples and quick commands   | API usage                |

### Code Files

| File                                                       | Component                      | Changes                               |
| ---------------------------------------------------------- | ------------------------------ | ------------------------------------- |
| [camera_setup.html](camera_setup.html)                     | **NEW** - Camera management UI | Complete new interface                |
| [eyeguard/models.py](eyeguard/models.py)                   | Database models                | Added camera_type, username, password |
| [eyeguard/serializers.py](eyeguard/serializers.py)         | API serializers                | Updated CameraSerializer              |
| [eyeguard/video_processor.py](eyeguard/video_processor.py) | Video processing               | Added build_hikvision_rtsp_url()      |
| [eyeguard/views.py](eyeguard/views.py)                     | API endpoints                  | Added setup_hikvision endpoint        |

### Database

| File                                                   | Purpose                           |
| ------------------------------------------------------ | --------------------------------- |
| [eyeguard/migrations/0003\_\*.py](eyeguard/migrations) | **NEW** - Database schema updates |

---

## 🚀 Getting Started

### 1. **First Time Setup** (5 minutes)

```
1. Read: README_HIKVISION_COMPLETE.md (Quick Start section)
4. Open: camera_setup.html (or via admin) (or via Django admin → Cameras → "Hikvision Setup")
3. Get: API token from admin panel
4. Add: Your first camera
```

### 2. **Detailed Setup** (15 minutes)

```
1. Read: HIKVISION_SETUP.md (Step-by-step)
2. Find: Your camera IP address
3. Open: camera_setup.html (or via admin)
4. Configure: Camera details
5. Test: Connection before saving
```

### 3. **Programmatic Access** (10 minutes)

```
1. Read: QUICK_START_HIKVISION.sh
2. Copy: API examples
3. Use: curl or Python requests
4. Integrate: Into your system
```

### 4. **Deep Dive** (30 minutes)

```
1. Read: ARCHITECTURE_HIKVISION.md
2. View: System diagrams
3. Study: Data flow
4. Review: Code implementation
```

---

## 🎯 Common Tasks

### Task: Add a New Camera

**Time: 3 minutes**

```bash
# Step 1: Open the interface (or use the admin link via Cameras → "Hikvision Setup")
open file:///Users/filzahamjad/Desktop/sites/eyeguard/camera_setup.html

# Step 2: Enter credentials (in the form)
# - Camera Name: Your camera name
# - IP Address: Your camera IP
# - Username: admin (or your username)
# - Password: Your password
# - Business: Select your organization

# Step 3: Click "Add Camera"
# Done! ✅
```

### Task: Find Your Camera IP Address

**Time: 2-5 minutes**

```bash
# Method 1: Ping common default
ping 192.168.1.64

# Method 2: Network scan
arp-scan -l | grep -i hikvision

# Method 3: Router admin
# Open: http://192.168.1.1 (or your router IP)
# Look for HIKVISION device in connected devices

# Method 4: Direct connection test
nc -zv 192.168.1.100 554  # Replace with suspected IP
```

### Task: Test Camera Connection

**Time: 1 minute**

```bash
# Using curl
curl -X POST http://localhost:8000/api/cameras/setup_hikvision/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test",
    "location": "Test",
    "ip_address": "192.168.1.100",
    "username": "admin",
    "password": "password",
    "business_id": 1,
    "test_connection": true
  }'

# Or use the web form with "Test connection" checkbox
```

### Task: View All Cameras

**Time: 1 minute**

```bash
# Method 1: Web interface
# Open: camera_setup.html
# Click: "My Cameras" tab

# Method 2: API
curl -X GET http://localhost:8000/api/cameras/ \
  -H "Authorization: Token YOUR_TOKEN" | python -m json.tool
```

### Task: Delete a Camera

**Time: 1 minute**

```bash
# Method 1: Web interface
# Open: camera_setup.html → My Cameras
# Click: Delete button

# Method 2: API
curl -X DELETE http://localhost:8000/api/cameras/CAMERA_ID/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### Task: Check Database Schema

**Time: 2 minutes**

```bash
# View Camera model:
# File: eyeguard/models.py
# Search for: "class Camera(models.Model):"

# View database directly:
python manage.py dbshell
SELECT * FROM cameras;
```

---

## 📊 System Overview

### What Each Component Does

```
camera_setup.html
    ↓
    User provides: IP, username, password
    ↓
    API endpoint: setup_hikvision
    ↓
    views.py: Validates and creates record
    ↓
    video_processor.py: Builds RTSP URL
    ↓
    Database: Stores camera with credentials
    ↓
    Later: When streaming starts
    ↓
    video_processor.py: Retrieves credentials
    ↓
    build_hikvision_rtsp_url(): Generates URL
    ↓
    cv2.VideoCapture(): Opens stream
    ↓
    Processing: Motion/detection
```

### Key Files and Their Roles

| File               | Role               | Key Method/Class                  |
| ------------------ | ------------------ | --------------------------------- |
| camera_setup.html  | User Interface     | JavaScript form handlers          |
| views.py           | API Layer          | `CameraViewSet.setup_hikvision()` |
| video_processor.py | Video Processing   | `build_hikvision_rtsp_url()`      |
| models.py          | Data Model         | `Camera` class with new fields    |
| serializers.py     | Data Serialization | `CameraSerializer`                |

---

## 🔍 Code Locations

### Add a Camera (Code)

**File:** [eyeguard/views.py](eyeguard/views.py)  
**Method:** `CameraViewSet.setup_hikvision()`  
**Lines:** ~565-670

**What it does:**

1. Validates input (IP, credentials, business)
2. Checks permissions and limits
3. Builds RTSP URL
4. Tests connection (optional)
5. Creates camera record

### Build RTSP URL (Code)

**File:** [eyeguard/video_processor.py](eyeguard/video_processor.py)  
**Function:** `build_hikvision_rtsp_url()`  
**Lines:** ~52-76

**What it does:**

1. Takes: IP, username, password, channel
2. URL-encodes credentials
3. Returns: Full RTSP URL

### Extract Stream (Code)

**File:** [eyeguard/video_processor.py](eyeguard/video_processor.py)  
**Method:** `VideoProcessor.initialize_video_capture()`  
**Lines:** ~163-195

**What it does:**

1. Checks camera type
2. Builds RTSP URL if Hikvision
3. Opens cv2.VideoCapture
4. Starts reading frames

### Database Schema (Code)

**File:** [eyeguard/models.py](eyeguard/models.py)  
**Class:** `Camera`  
**Lines:** ~118-170

**New Fields:**

- `camera_type` - Camera manufacturer/type
- `username` - Camera admin username
- `password` - Camera admin password

---

## ✅ Verification Checklist

Check these to verify everything is working:

- [ ] Can open camera_setup.html
- [ ] Can enter API token
- [ ] Can see business dropdown (populated from API)
- [ ] Can fill camera form with all details
- [ ] Can test connection successfully
- [ ] Camera appears in database
- [ ] Camera shows in "My Cameras" tab
- [ ] Can start video streaming
- [ ] Alerts trigger on motion/detection
- [ ] Django system checks pass
- [ ] No error logs in console

---

## 🐛 Debugging Help

### Check Django System

```bash
cd /Users/filzahamjad/Desktop/sites/eyeguard
python manage.py check
```

### View Database

```bash
python manage.py dbshell
SELECT * FROM cameras;
.exit
```

### Test API Endpoint

```bash
curl -X POST http://localhost:8000/api/cameras/setup_hikvision/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", ...}'
```

### Check Logs

```bash
tail -f /var/log/eyeguard.log
```

### Verify Camera Credentials

```bash
# Try connecting directly
stream_url="rtsp://admin:password@192.168.1.100:554/Streaming/Channels/1"
python3 -c "import cv2; cap = cv2.VideoCapture('$stream_url'); print('Connected!' if cap.isOpened() else 'Failed')"
```

---

## 📱 Browser Requirements

- **Recommended:** Chrome, Firefox, Safari (latest versions)
- **Requirements:** JavaScript enabled, Cookies enabled
- **API Token Storage:** Local browser storage

---

## 🔐 Security Notes

⚠️ **Important Security Considerations:**

1. **Credentials**: Stored in database - ensure database is secured
2. **HTTPS**: Use HTTPS in production (currently HTTP for development)
3. **API Token**: Keep your token secret - don't share it
4. **Default Passwords**: Always change camera default passwords
5. **Network**: Consider network segmentation for camera traffic
6. **Encryption**: Future enhancement - database-level encryption

---

## 📞 Need Help?

### For Setup Questions

→ Read: [HIKVISION_SETUP.md](HIKVISION_SETUP.md)

### For API Usage

→ Read: [QUICK_START_HIKVISION.sh](QUICK_START_HIKVISION.sh)

### For Architecture Questions

→ Read: [ARCHITECTURE_HIKVISION.md](ARCHITECTURE_HIKVISION.md)

### For Code Questions

→ See: Specific file listed in "[Code Locations](#-code-locations)"

---

**Last Updated:** February 28, 2025  
**Status:** ✅ Complete and Ready to Use
