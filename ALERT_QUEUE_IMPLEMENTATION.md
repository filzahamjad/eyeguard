## Alert Priority Queue Implementation Summary

### What Was Added

A complete priority queue system for reprocessing alerts with different priorities. The system includes:

#### 1. **Model Changes** (`eyeguard/models.py`)

Added fields to the `Alert` model:

- `reprocess_priority` (int 1-10) - Priority level, default 5
- `is_queued_for_reprocess` (bool) - Queue membership flag
- `reprocess_attempts` (int) - Count of reprocessing attempts
- `last_reprocessed_at` (DateTime) - Timestamp of last reprocessing
- `queued_for_reprocess_at` (DateTime) - When queued

#### 2. **Priority Queue Manager** (`eyeguard/alert_queue.py`)

New module with `AlertPriorityQueue` class providing:

- `enqueue(alert_id, priority, max_attempts)` - Add alert to queue
- `get_next_alert()` - Fetch highest-priority alert
- `mark_reprocessed(alert_id)` - Update alert after reprocessing
- `dequeue(alert_id)` - Remove from queue
- `get_queue_summary()` - List all queued alerts by priority
- `get_queue_count()` - Count of queued alerts

#### 3. **Video Processor Enhancement** (`eyeguard/video_processor.py`)

Added method `reprocess_alert_from_queue(alert_id)`:

- Loads the alert's frame image
- Runs all enabled detection models on it
- Updates alert with new results
- Updates status to `investigating` (detected) or `false_positive` (not detected)
- Saves annotated frame as `alerts/reprocessed_alert_<id>_<timestamp>.jpg`
- Appends reprocessing notes to `resolution_notes`

#### 4. **REST API Endpoints** (`eyeguard/views.py`)

Added to `AlertViewSet`:

- `POST /api/alerts/{id}/queue_for_reprocess/` - Queue alert
- `GET /api/alerts/reprocessing_queue/` - View queue status
- `POST /api/alerts/process_queue/` - Process next alert
- `POST /api/alerts/{id}/remove_from_queue/` - Dequeue alert

#### 5. **Management Command** (`eyeguard/management/commands/process_alert_queue.py`)

New command to process the queue:

```bash
python3 manage.py process_alert_queue              # Single batch
python3 manage.py process_alert_queue --daemon    # Continuous
python3 manage.py process_alert_queue --interval=5 --max-batch=2
```

#### 6. **Documentation** (`ALERT_PRIORITY_QUEUE.md`)

Complete guide with examples and API reference

### Design Decisions

1. **Non-blocking**: Alert confirmation runs in background thread; queue processing is separate
2. **Priority ordering**: Higher priority (10) processed first; FIFO within same priority
3. **Safety**: DB connections properly managed in threads; ORM objects re-fetched when needed
4. **Attempt limiting**: Configurable max reprocessing attempts per alert
5. **Frame persistence**: Alert frame images stored in `alerts/` folder; reprocessed frames also saved there

### Real-Time Feed Compatibility

- Main video loop: Processes frames, creates alerts, queues confirmation in separate thread
- Confirmation thread: Validates alerts using last 10 in-memory frames (non-blocking)
- Reprocessing queue: Completely separate, can be run on different machine/process if desired
- No blocking of frame processing

### Next Steps

1. **Run migrations** to add Alert model fields:

   ```bash
   python3 manage.py makemigrations eyeguard
   python3 manage.py migrate
   ```

2. **Test the system**:

   ```bash
   # Start camera processing
   python3 manage.py process_camera 1 --max-frames 200

   # In another terminal, check queue status
   python3 manage.py shell -c "from eyeguard.alert_queue import AlertPriorityQueue; print(AlertPriorityQueue.get_queue_summary())"

   # Process one alert from queue
   python3 manage.py process_alert_queue

   # Or run daemon
   python3 manage.py process_alert_queue --daemon --interval=5
   ```

3. **Via API**:

   ```bash
   # Queue alert for reprocessing (priority 8, max 3 attempts)
   curl -X POST http://localhost:8000/api/alerts/1/queue_for_reprocess/ \
     -H "Content-Type: application/json" \
     -H "Authorization: Token YOUR_TOKEN" \
     -d '{"priority": 8, "max_attempts": 3}'

   # Check queue
   curl http://localhost:8000/api/alerts/reprocessing_queue/ \
     -H "Authorization: Token YOUR_TOKEN"

   # Process one alert
   curl -X POST http://localhost:8000/api/alerts/process_queue/ \
     -H "Authorization: Token YOUR_TOKEN"
   ```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Real-time Video Stream                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  VideoProcessor.run() │
         │  (Main thread)        │
         └───────────┬───────────┘
                     │
                     ├─► Creates Alert
                     │
                     ├─► Schedules confirm_alert()
                     │   (Background thread)
                     │
                     └─► Handles next frame
                         (non-blocking)

        ┌─────────────────────────────┐
        │ Alert Confirmation Thread   │
        │ - Checks last 10 frames     │
        │ - Updates status            │
        │ - Non-blocking              │
        └─────────────────────────────┘

┌─────────────────────────────────────┐
│ Alert Priority Queue                │
│ - User/API can queue alerts         │
│ - Separate background task process  │
│ - Management command: process_queue │
│ - REST API endpoints                │
└─────────────────────────────────────┘
```
