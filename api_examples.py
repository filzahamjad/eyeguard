"""
API Usage Examples for CCTV Surveillance System

This file contains example code snippets for interacting with the surveillance API
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

# Authentication token (obtain after login)
TOKEN = "your_auth_token_here"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Token {TOKEN}"
}


# ============================================
# 1. BUSINESS MANAGEMENT
# ============================================

def create_business():
    """Create a new business with admin user"""
    url = f"{BASE_URL}/businesses/"
    data = {
        "name": "Tech Retail Store",
        "email": "contact@techretail.com",
        "phone": "+1234567890",
        "address": "456 Tech Avenue, Silicon Valley, CA 94025",
        "subscription": 2,  # Assuming subscription ID 2 exists
        "subscription_start_date": "2024-02-01T00:00:00Z",
        "subscription_end_date": "2025-01-31T23:59:59Z",
        "admin_username": "techretail_admin",
        "admin_password": "SecurePass123!",
        "admin_email": "admin@techretail.com",
        "admin_first_name": "John",
        "admin_last_name": "Doe"
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def validate_business_subscription(business_id):
    """Check if business subscription is valid"""
    url = f"{BASE_URL}/businesses/{business_id}/validate_subscription/"
    
    response = requests.post(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def get_business_dashboard(business_id, days=7):
    """Get business dashboard with statistics"""
    url = f"{BASE_URL}/businesses/{business_id}/dashboard/"
    params = {"days": days}
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


# ============================================
# 2. CAMERA MANAGEMENT
# ============================================

def create_camera(business_id):
    """Create a new camera for a business"""
    url = f"{BASE_URL}/cameras/"
    data = {
        "business": business_id,
        "name": "Store Entrance Camera 1",
        "location": "Main Entrance - Ground Floor",
        "stream_url": "rtsp://admin:password@192.168.1.100:554/stream1",
        "stream_type": "rtsp",
        "target_fps": 10,
        "motion_confidence": 0.6,
        "persist_frames": 5,
        "status": "active",
        "detection_models_config": [
            {
                "model_id": 1,  # Shoplifting model
                "confidence_threshold": 0.65,
                "is_enabled": True
            },
            {
                "model_id": 2,  # Weapon model
                "confidence_threshold": 0.7,
                "is_enabled": True
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def assign_detection_model(camera_id, model_id, confidence=0.6):
    """Assign a detection model to a camera"""
    url = f"{BASE_URL}/cameras/{camera_id}/assign_model/"
    data = {
        "model_id": model_id,
        "confidence_threshold": confidence,
        "is_enabled": True
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def update_camera_status(camera_id, status):
    """Update camera status (active, inactive, maintenance, error)"""
    url = f"{BASE_URL}/cameras/{camera_id}/update_status/"
    data = {"status": status}
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def get_camera_alerts(camera_id, days=7, status=None, severity=None):
    """Get alerts for a specific camera"""
    url = f"{BASE_URL}/cameras/{camera_id}/alerts/"
    params = {"days": days}
    
    if status:
        params["status"] = status
    if severity:
        params["severity"] = severity
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


# ============================================
# 3. ALERT MANAGEMENT
# ============================================

def list_alerts(camera_id=None, status=None, severity=None):
    """List alerts with filters"""
    url = f"{BASE_URL}/alerts/"
    params = {}
    
    if camera_id:
        params["camera"] = camera_id
    if status:
        params["status"] = status
    if severity:
        params["severity"] = severity
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def get_recent_alerts():
    """Get alerts from last 24 hours"""
    url = f"{BASE_URL}/alerts/recent/"
    
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def get_unacknowledged_alerts():
    """Get all unacknowledged alerts"""
    url = f"{BASE_URL}/alerts/unacknowledged/"
    
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    url = f"{BASE_URL}/alerts/{alert_id}/acknowledge/"
    
    response = requests.post(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def resolve_alert(alert_id, resolution_notes):
    """Resolve an alert with notes"""
    url = f"{BASE_URL}/alerts/{alert_id}/resolve/"
    data = {"resolution_notes": resolution_notes}
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def mark_false_positive(alert_id, notes):
    """Mark alert as false positive"""
    url = f"{BASE_URL}/alerts/{alert_id}/mark_false_positive/"
    data = {"notes": notes}
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def get_alert_statistics(days=7):
    """Get alert statistics for a time period"""
    url = f"{BASE_URL}/alerts/statistics/"
    params = {"days": days}
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


# ============================================
# 4. EXAMPLE WORKFLOW
# ============================================

def example_workflow():
    """
    Complete example workflow:
    1. Create business
    2. Create camera
    3. Check alerts
    4. Handle alerts
    """
    
    print("=" * 60)
    print("STEP 1: Create Business")
    print("=" * 60)
    business = create_business()
    business_id = business.get('id')
    
    print("\n" + "=" * 60)
    print("STEP 2: Validate Subscription")
    print("=" * 60)
    validate_business_subscription(business_id)
    
    print("\n" + "=" * 60)
    print("STEP 3: Create Camera")
    print("=" * 60)
    camera = create_camera(business_id)
    camera_id = camera.get('id')
    
    print("\n" + "=" * 60)
    print("STEP 4: Get Recent Alerts")
    print("=" * 60)
    alerts = get_recent_alerts()
    
    print("\n" + "=" * 60)
    print("STEP 5: Handle First Alert (if any)")
    print("=" * 60)
    if alerts and len(alerts) > 0:
        alert_id = alerts[0]['id']
        
        # Acknowledge the alert
        print("\nAcknowledging alert...")
        acknowledge_alert(alert_id)
        
        # Resolve the alert
        print("\nResolving alert...")
        resolve_alert(alert_id, "Reviewed - No action needed")
    
    print("\n" + "=" * 60)
    print("STEP 6: Get Business Dashboard")
    print("=" * 60)
    get_business_dashboard(business_id, days=30)
    
    print("\n" + "=" * 60)
    print("STEP 7: Get Alert Statistics")
    print("=" * 60)
    get_alert_statistics(days=30)


# ============================================
# 5. BULK OPERATIONS
# ============================================

def acknowledge_all_new_alerts():
    """Acknowledge all new alerts"""
    alerts = get_unacknowledged_alerts()
    
    for alert in alerts:
        alert_id = alert['id']
        print(f"\nAcknowledging alert {alert_id}...")
        acknowledge_alert(alert_id)


def get_critical_alerts_summary():
    """Get summary of all critical alerts"""
    critical_alerts = list_alerts(severity='critical', status='new')
    
    print(f"\n{'=' * 60}")
    print(f"CRITICAL ALERTS SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total Critical Alerts: {len(critical_alerts)}")
    
    for alert in critical_alerts:
        print(f"\nAlert ID: {alert['id']}")
        print(f"Camera: {alert['camera_name']}")
        print(f"Location: {alert['camera_location']}")
        print(f"Type: {alert['alert_type_display']}")
        print(f"Confidence: {alert['confidence_score']:.2%}")
        print(f"Time: {alert['created_at']}")


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("CCTV Surveillance System - API Examples")
    print("=" * 60)
    
    # Uncomment the function you want to test:
    
    # example_workflow()
    # get_recent_alerts()
    # get_alert_statistics(days=7)
    # get_critical_alerts_summary()
    
    print("\nUpdate the TOKEN variable and uncomment the functions to test!")
