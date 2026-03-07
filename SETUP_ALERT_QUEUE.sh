#!/bin/bash
# Quick-start guide for Alert Priority Queue system

set -e

echo "📋 Alert Priority Queue Setup Guide"
echo "===================================="
echo ""

echo "1️⃣  Running Django migrations (adds queue fields to Alert model)..."
python3 manage.py makemigrations eyeguard
python3 manage.py migrate
echo "✅ Migrations complete"
echo ""

echo "2️⃣  Starting a demo..."
echo "Run this in one terminal to process video and generate alerts:"
echo "   python3 manage.py process_camera 1 --max-frames 200"
echo ""

echo "3️⃣  In another terminal, monitor the queue:"
echo "   # Check queue status (Django shell)"
echo "   python3 manage.py shell -c \"from eyeguard.alert_queue import AlertPriorityQueue; print(AlertPriorityQueue.get_queue_summary())\""
echo ""

echo "4️⃣  Queue an alert for reprocessing:"
echo "   # Via shell"
echo "   python3 manage.py shell -c \"from eyeguard.alert_queue import AlertPriorityQueue; AlertPriorityQueue.enqueue(1, priority=8)\""
echo ""

echo "5️⃣  Process the queue:"
echo "   # Single batch:"
echo "   python3 manage.py process_alert_queue"
echo ""
echo "   # Daemon mode (continuous):"
echo "   python3 manage.py process_alert_queue --daemon --interval=5"
echo ""

echo "6️⃣  Via REST API (if server running on port 8000):"
echo ""
echo "   # Get your token first"
echo "   TOKEN=\$(python3 manage.py shell -c \"from django.contrib.auth.models import User; from rest_framework.authtoken.models import Token; u=User.objects.first(); t,_=Token.objects.get_or_create(user=u); print(t.key)\")"
echo ""
echo "   # Queue alert 1 for reprocessing (priority 8, max 3 attempts)"
echo "   curl -X POST http://localhost:8000/api/alerts/1/queue_for_reprocess/ \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H \"Authorization: Token \$TOKEN\" \\"
echo "     -d '{\"priority\": 8, \"max_attempts\": 3}'"
echo ""
echo "   # Check queue status"
echo "   curl http://localhost:8000/api/alerts/reprocessing_queue/ \\"
echo "     -H \"Authorization: Token \$TOKEN\""
echo ""
echo "   # Process next alert from queue"
echo "   curl -X POST http://localhost:8000/api/alerts/process_queue/ \\"
echo "     -H \"Authorization: Token \$TOKEN\""
echo ""

echo "📚 Full documentation: See ALERT_PRIORITY_QUEUE.md"
echo ""
