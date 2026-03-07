# Hikvision Camera Integration - Implementation Summary

## Overview

Comprehensive Hikvision IP camera integration has been added to EyeGuard, allowing users to easily configure and manage cameras through a web interface with automatic credential handling.

## Changes Made

### 1. Database Model Updates

#### File: `eyeguard/models.py`

**Added to Camera Model**:

- `camera_type` field (choices: generic, hikvision, dahua, uniview, other)
- `username` field for camera authentication
- `password` field for camera authentication

**Migration Created**: `0003_camera_camera_type_camera_password_camera_username.py`

### 2. API Serializer Updates

#### File: `eyeguard/serializers.py`

**Updated CameraSerializer**:

- Added `camera_type` and `camera_type_display` fields
- Added `username` and `password` fields to the serialized output
- Includes all camera authentication details in API responses

### 3. Video Processing

#### File: `eyeguard/video_processor.py`

**Added Features**:

- New `build_hikvision_rtsp_url()` helper function that:
  - Takes IP address, username, password, and channel as inputs
  - Automatically builds proper Hikvision RTSP URLs
  - URL-encodes special characters in credentials
  - Supports multi-channel Hikvision devices

**Updated `initialize_video_capture()` method**:

- Detects Hikvision camera type
- Automatically builds RTSP URL from IP and credentials
- Falls back to stream_url if manual URL provided
- Enhanced error handling with specific Hikvision messages

### 4. API Endpoints

#### File: `eyeguard/views.py`

**New Endpoint**: `POST /api/cameras/setup_hikvision/`

- Allows creation of Hikvision cameras with credential input
- Automatic RTSP URL generation
- Optional connection testing before saving
- Detailed error messages for troubleshooting
- Business/organization validation
- Camera limit checks per subscription

**Features**:

```
Request Body:
{
  "name": "Camera Name",
  "location": "Physical Location",
  "ip_address": "192.168.1.100",
  "username": "admin",
  "password": "password",
  "channel": 1,  // Optional, default 1
  "business_id": 1,
  "test_connection": true  // Optional, default false
}
```

### 5. Frontend Interface

#### File: `camera_setup.html`

New comprehensive camera management interface featuring:

**Setup Tab**:

- Camera name and location input
- Hikvision IP address field
- Username and password input with secure handling
- Channel selection for multi-channel devices
- Business organization selector
- Optional connection testing before saving
- Real-time validation and error messages
- Responsive design for mobile access

**Cameras Tab**:

- List all configured cameras
- Display camera details (IP, type, location)
- Edit functionality (placeholder for future enhancement)
- Delete functionality
- Status indicators

**Features**:

- Local browser storage for API token persistence
- Real-time camera list updates
- Connection status feedback
- Loading indicators
- Success/error message displays
- Business dropdown population from API

### 6. Documentation

#### File: `HIKVISION_SETUP.md`

Comprehensive setup guide including:

- Feature overview
- Step-by-step setup instructions
- API reference
- Troubleshooting guide
- Security recommendations
- Database schema documentation
- Advanced configuration options

## Database Migration

Migration applied successfully:

```
Applying eyeguard.0003_camera_camera_type_camera_password_camera_username... OK
```

New fields added to cameras table:

- camera_type (varchar(20), default='generic')
- password (varchar(255), null=true, blank=true)
- username (varchar(255), null=true, blank=true)

## Available Camera Types

The system now supports multiple camera types:

- **generic**: Generic IP cameras
- **hikvision**: Hikvision cameras (with auto URL generation)
- **dahua**: Dahua cameras (extensible)
- **uniview**: Uniview cameras (extensible)
- **other**: Other camera types

## How It Works

### Camera Stream URL Generation Flow

1. **User Input**: User provides IP address, username, password, channel
2. **URL Building**: `build_hikvision_rtsp_url()` generates:
   ```
   rtsp://username:password@192.168.1.100:554/Streaming/Channels/1
   ```
3. **Credential Encoding**: Special characters URL-encoded for safety
4. **Connection Test**: Optional test frame read to verify connectivity
5. **Database Storage**: IP address stored in `stream_url`, credentials in `username`/`password`
6. **Playback**: Video processor auto-builds RTSP URL on demand using stored credentials

### Security Considerations

- Credentials stored securely in database
- URL encoding for special character handling
- No credentials exposed in logs (only RTSP URL shown)
- Database-level encryption recommended for production

## Testing

The implementation includes:

- Django system checks: ✅ Passed
- API endpoint validation
- Connection testing capability (optional)
- Error handling with user-friendly messages

## Usage Quick Reference

### Add Camera via API

```bash
curl -X POST http://localhost:8000/api/cameras/setup_hikvision/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Entrance",
    "location": "Front Door",
    "ip_address": "192.168.1.100",
    "username": "admin",
    "password": "password123",
    "business_id": 1,
    "test_connection": true
  }'
```

### Access Camera Setup Interface

```
file:///Users/filzahamjad/Desktop/sites/eyeguard/camera_setup.html
```

## Files Modified

1. ✅ `eyeguard/models.py` - Added camera type and credentials fields
2. ✅ `eyeguard/serializers.py` - Updated CameraSerializer
3. ✅ `eyeguard/video_processor.py` - Added Hikvision URL builder and support
4. ✅ `eyeguard/views.py` - Added setup_hikvision endpoint
5. ✅ `eyeguard/migrations/0003_*.py` - Created migration
6. ✅ `camera_setup.html` - Created new camera management interface
7. ✅ `HIKVISION_SETUP.md` - Created comprehensive documentation

## Next Steps

### Optional Enhancements

1. **Edit Endpoint**: Implement camera editing functionality
2. **Encryption**: Add database-level encryption for credentials
3. **Multi-Stream Support**: Auto-detect available streams
4. **Camera Discovery**: Network scanning for automatic camera detection
5. **Admin Interface**: Add camera management to Django admin (included; custom admin view and changelist link)
6. **API Authentication**: Leverage camera API for advanced settings
7. **Health Monitoring**: Periodic connection status checks

### Deployment Considerations

1. Ensure database backups include new credential fields
2. Update any deployment scripts to run migrations
3. Consider adding credential encryption layer
4. Test with actual Hikvision cameras in your environment

## Rollback Plan

If you need to revert:

```bash
python manage.py migrate eyeguard 0002_alert_is_queued_for_reprocess_and_more
```

Then remove the migration file:

```bash
rm eyeguard/migrations/0003_camera_camera_type_camera_password_camera_username.py
```

And undo the model changes in `models.py` and `serializers.py`.

## Configuration Notes

### Default Hikvision Settings

- **RTSP Port**: 554
- **Stream Path**: `/Streaming/Channels/{channel_number}`
- **Default Users**: admin, root
- **Max Channels**: Varies by model (2-8 typical)

### Testing Connection Requirements

- Camera must be powered on
- Camera must be on the same network
- Port 554 must be accessible
- RTSP service must be enabled in camera settings

## Support Resources

- Hikvision Official: https://www.hikvision.com
- RTSP Protocol: RFC 7826
- EyeGuard Documentation: See HIKVISION_SETUP.md
