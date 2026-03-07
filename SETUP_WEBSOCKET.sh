#!/bin/bash
# WebSocket Setup Quick Start

set -e

echo "🚀 WebSocket Alert Streaming Setup"
echo "===================================="
echo ""

echo "1️⃣  Installing WebSocket dependencies..."
pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0
echo "✅ Dependencies installed"
echo ""

echo "2️⃣  Checking Redis..."
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis not found. Install it:"
    echo "   macOS: brew install redis"
    echo "   Ubuntu: sudo apt-get install redis-server"
    echo "   Docker: docker run -d -p 6379:6379 redis:latest"
else
    echo "✅ Redis found at: $(which redis-server)"
fi
echo ""

echo "3️⃣  Starting services..."
echo ""
echo "Terminal 1 - Start Redis:"
echo "   redis-server"
echo ""
echo "Terminal 2 - Start Django with Daphne:"
echo "   daphne -b 0.0.0.0 -p 8000 eyeguard.asgi:application"
echo ""
echo "Terminal 3 - Start video processing:"
echo "   python3 manage.py process_camera 1 --max-frames 500"
echo ""

echo "4️⃣  Test WebSocket connection in browser console:"
cat << 'EOF'
   // Get your token first:
   // curl -X POST http://localhost:8000/api/token-auth/ \
   //   -H "Content-Type: application/json" \
   //   -d '{"username": "your_user", "password": "your_pass"}'

   const token = 'YOUR_TOKEN_HERE';
   const ws = new WebSocket(`ws://localhost:8000/ws/alerts/camera/1/?token=${token}`);

   ws.onopen = () => console.log('✅ Connected!');
   ws.onmessage = (e) => console.log('📡 Alert:', JSON.parse(e.data));
   ws.onerror = (e) => console.error('❌ Error:', e);
   ws.onclose = () => console.log('🔌 Disconnected');
EOF

echo ""
echo "5️⃣  See real-time alerts!"
echo ""
echo "📚 Full documentation: WEBSOCKET_SETUP.md"
echo ""
