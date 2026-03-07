#!/bin/bash
# EyeGuard Hikvision Camera Setup Quick Start

# 1. Start your Django development server
cd /Users/filzahamjad/Desktop/sites/eyeguard
python manage.py runserver

# 2. Once running, access the camera setup interface:
# Open in browser: file:///Users/filzahamjad/Desktop/sites/eyeguard/camera_setup.html

# 3. You'll need:
#    - Your EyeGuard API token (get from admin panel)
#    - Hikvision camera IP address (e.g., 192.168.1.100)
#    - Camera admin username (default: admin)
#    - Camera admin password
#    - Your business/organization ID

# 4. Example API call to add a camera:
curl -X POST http://localhost:8000/api/cameras/setup_hikvision/ \
  -H "Authorization: Token YOUR_ADMIN_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Entrance",
    "location": "Front Door",
    "ip_address": "192.168.1.100",
    "username": "admin",
    "password": "your_camera_password",
    "channel": 1,
    "business_id": 1,
    "test_connection": true
  }'

# 5. To list all cameras:
curl -X GET http://localhost:8000/api/cameras/ \
  -H "Authorization: Token YOUR_ADMIN_TOKEN_HERE"

# 6. To delete a camera:
curl -X DELETE http://localhost:8000/api/cameras/CAMERA_ID/ \
  -H "Authorization: Token YOUR_ADMIN_TOKEN_HERE"

# 7. Check camera logs:
tail -f /var/log/eyeguard.log

# 8. Database migration status:
python manage.py migrate eyeguard

echo "✅ Hikvision camera setup is ready!"
echo "📖 See HIKVISION_SETUP.md for detailed documentation"
