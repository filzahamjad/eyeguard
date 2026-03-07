# Hikvision Camera Integration Guide

## Overview

EyeGuard now supports Hikvision IP cameras and other RTSP-based cameras. You can easily configure your cameras through the web interface with automatic credential handling and connection testing.

## Features

- **Credential Management**: Securely store camera username/password
- **Auto Configuration**: Automatic RTSP URL building for Hikvision cameras
- **Connection Testing**: Verify camera connectivity before saving
- **Multi-Camera Support**: Manage multiple cameras per organization
- **Business Organization**: Link cameras to specific businesses/locations

## Quick Start

### 1. Access Camera Setup

You can reach the Hikvision setup in two ways:

- **Standalone page:**

  ```
  file:///Users/filzahamjad/Desktop/sites/eyeguard/camera_setup.html
  ```

- **From Django admin:** log in to `/admin/`, go to **Cameras → Hikvision Setup** (button in the camera list).

Both methods expose the same interface and behave identically.

### 2. Authenticate

When you first visit the page, you'll be prompted for your API token:

- Log in to your EyeGuard admin panel
- Navigate to your user settings
- Copy your API authentication token
- Paste it in the prompt on the camera setup page

The token will be saved in your browser's local storage for future sessions.

### 3. Add a Hikvision Camera

#### Step 1: Fill in Camera Details

- **Camera Name**: Give your camera a friendly name (e.g., "Front Door", "Parking Lot")
- **Location**: Physical location of the camera (e.g., "Main Entrance")
- **Camera IP Address**: The IP address of your Hikvision camera (e.g., 192.168.1.100)
- **Username**: Admin username (default is usually "admin")
- **Password**: Admin password

#### Step 2: (Optional) Test Connection

- Check the "Test connection before saving" checkbox
- This will verify the camera is accessible and credentials are correct before creating the camera record

#### Step 3: Submit

Click "Add Camera" to create the camera configuration.

### 4. Managing Cameras

Once added, your cameras appear in the "My Cameras" tab where you can:

- View detailed camera information
- Edit camera settings (coming soon)
- Delete cameras you no longer need

## Default Hikvision Configuration

### Standard RTSP URL Format

```
rtsp://username:password@192.168.1.100:554/Streaming/Channels/1
```

- **Port**: 554 (standard RTSP)
- **Channel**: 1 (main stream)
- **Username/Password**: Your camera admin credentials

### Default Hikvision Credentials

- **Username**: `admin` (or `root`)
- **Password**: Your configured camera password

### Finding Your Camera IP Address

#### Method 1: Using Hikvision iVMS Software

1. Open Hikvision iVMS-4200 or similar management software
2. Your camera IP will be displayed in the device list

#### Method 2: Router Management

1. Log into your network router admin panel
2. Check connected devices list
3. Look for device named "HIKVISION" or similar

#### Method 3: DHCP Server Info

1. Check your DHCP server logs
2. Look for recent device assignments with "HIKVISION" in the hostname

#### Method 4: Default IP Approach

1. Reset camera to factory defaults
2. Connect camera directly to computer via Ethernet
3. Use network scanning tool (e.g., Advanced IP Scanner)
4. Look for device in 192.168.x.x range

## API Reference

### Setup Hikvision Camera Endpoint

**POST** `/api/cameras/setup_hikvision/`

#### Request Body

```json
{
  "name": "Main Entrance",
  "location": "Front Door",
  "ip_address": "192.168.1.100",
  "username": "admin",
  "password": "password123",
  "channel": 1,
  "business_id": 1,
  "test_connection": true
}
```

#### Response (Success)

```json
{
  "id": 42,
  "name": "Main Entrance",
  "location": "Front Door",
  "camera_type": "hikvision",
  "camera_type_display": "Hikvision",
  "stream_url": "192.168.1.100",
  "stream_type": "rtsp",
  "stream_type_display": "RTSP Stream",
  "username": "admin",
  "password": "password123",
  "status": "active",
  "is_active": true,
  "business": 1,
  "target_fps": 10,
  "motion_confidence": 0.6,
  "persist_frames": 5
}
```

#### Response (Error)

```json
{
  "error": "Failed to connect to camera at 192.168.1.100. Check IP, username, and password."
}
```

## Troubleshooting

### Connection Failed

**Problem**: "Failed to connect to camera at IP address"

**Solutions**:

1. Verify IP address is correct and reachable on your network

   ```bash
   ping 192.168.1.100
   ```

2. Verify username/password are correct
   - Test login with Hikvision iVMS software

3. Check camera settings:
   - Ensure RTSP is enabled in camera settings
   - Check firewall rules on network

4. Verify port 554 is accessible:
   ```bash
   nc -zv 192.168.1.100 554
   ```

### Camera Not Streaming After Setup

**Problem**: Camera created but no video feed

**Solutions**:

1. Verify camera is connected and powered on
2. Check LED indicators on camera for network connectivity
3. Restart the camera
4. Verify username/password in your camera admin settings

### Special Characters in Password

**Problem**: Special characters in password cause connection errors

**Solution**: The system automatically URL-encodes special characters, but if issues persist:

1. Change camera password to alphanumeric only
2. Re-add the camera with the new password

## Advanced Configuration

### Multiple Streams

Hikvision cameras support multiple streams. To use secondary stream:

- Change "Channel" to 2 in the setup form
- Different channels may have different resolutions and bitrates

### Network Optimization

#### For High Bandwidth Usage

You can modify camera settings within Hikvision admin panel:

1. Access camera web interface: `http://192.168.1.100:8000`
2. login with admin credentials
3. Adjust bitrate and resolution to reduce bandwidth

#### For Low Light Environments

In camera settings:

- Enable IR LED/Night Vision
- Adjust exposure settings
- Enable noise reduction

## Database Schema

### Camera Model Fields

```python
{
    'id': integer,  # Primary key
    'business': integer,  # ForeignKey to Business
    'name': string,  # Camera name
    'location': string,  # Physical location
    'camera_type': choice,  # 'hikvision', 'dahua', 'generic', etc.
    'stream_url': string,  # IP address or RTSP URL
    'stream_type': choice,  # 'rtsp', 'http', 'file', 'webcam'
    'username': string,  # Optional encrypted credentials
    'password': string,  # Optional encrypted credentials
    'target_fps': integer,  # Processing frames per second
    'motion_confidence': float,  # Motion detection threshold
    'persist_frames': integer,  # Frames before alert trigger
    'status': choice,  # 'active', 'inactive', 'maintenance', 'error'
    'is_active': boolean,
    'last_active': datetime,
    'created_at': datetime,
    'updated_at': datetime
}
```

## Security Notes

⚠️ **Important**:

- Credentials are stored in the database. Ensure your database is properly secured.
- Use strong, unique passwords for camera admin accounts
- Change default camera passwords from factory defaults
- Consider network segmentation for camera traffic
- Enable 2FA on your EyeGuard admin account

## Support

For additional help:

1. Check alert logs in the admin panel
2. Review camera status in "My Cameras" tab
3. Verify camera is online and accessible

## Related Files

- Camera HTML Interface: [camera_setup.html](camera_setup.html)
- Alert Stream View: [alert_stream.html](alert_stream.html)
- API Views: [eyeguard/views.py](eyeguard/views.py)
- Video Processor: [eyeguard/video_processor.py](eyeguard/video_processor.py)
- Models: [eyeguard/models.py](eyeguard/models.py)
