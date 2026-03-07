# Alert Priority Queue System

## Overview

The alert priority queue system allows you to queue alerts for reprocessing with different priority levels. This is useful for:

- Re-running detection models on alerts with different thresholds or updated models
- Confirming false positives by re-analyzing the original frame
- Prioritizing critical alerts for faster reprocessing
- Handling alert spikes by processing in order of importance

## Features

- **Priority-based queue**: Alerts are processed in order of priority (1-10, where 10 is critical)
- **FIFO within priority**: Within the same priority level, alerts are processed in FIFO order
- **Attempt tracking**: Each alert tracks reprocessing attempts and can be limited to N maximum attempts
- **Background processing**: Dedicated management command to process the queue as a background task
- **API endpoints**: REST API to enqueue, check status, and process alerts

## Model Fields

The `Alert` model includes:

- `reprocess_priority` (int, 1-10): Priority level for reprocessing (default: 5)
- `is_queued_for_reprocess` (bool): Whether the alert is in the processing queue
- `reprocess_attempts` (int): Number of times this alert has been reprocessed
- `last_reprocessed_at` (DateTime): Timestamp of last reprocessing
- `queued_for_reprocess_at` (DateTime): When the alert was queued

## Usage

### Via Python/Management Command

Process alerts one batch at a time:

```bash
python3 manage.py process_alert_queue
```

Process continuously as a daemon:

```bash
python3 manage.py process_alert_queue --daemon
```

Check queue every 5 seconds, process up to 2 alerts per check:

```bash
python3 manage.py process_alert_queue --daemon --interval=5 --max-batch=2
```

### Via REST API

**Queue an alert for reprocessing:**

```bash
POST /api/alerts/{alert_id}/queue_for_reprocess/
{
  "priority": 8,
  "max_attempts": 3
}
```

**Get queue status:**

```bash
GET /api/alerts/reprocessing_queue/
```

Response:

```json
{
  "queue_count": 5,
  "alerts_by_priority": {
    "10": [
      {
        "id": 123,
        "alert_type": "weapon",
        "camera": "Camera 1",
        "queued_at": "2026-02-13T10:30:00Z",
        "attempts": 0
      }
    ],
    "5": [...]
  }
}
```

**Process the next alert from queue:**

```bash
POST /api/alerts/process_queue/
```

Response:

```json
{
  "alert": { ... },
  "message": "Alert 123 reprocessed successfully",
  "queue_remaining": 4
}
```

**Remove an alert from queue:**

```bash
POST /api/alerts/{alert_id}/remove_from_queue/
```

## How It Works

1. **Queueing**: Call `AlertPriorityQueue.enqueue(alert_id, priority=8)` or use the API endpoint
2. **Priority ordering**: The queue manager sorts by priority (high to low), then by queue time (FIFO)
3. **Processing**:
   - Load detection models for the alert's camera
   - Reload the original alert frame image
   - Run all enabled detection models on that frame
   - Update the alert with new detection results
   - Save a new annotated frame
   - Increment reprocess attempt counter
4. **Status updates**:
   - If detections found → `status='investigating'`, `resolution_notes` appended
   - If no detections → `status='false_positive'`, `resolution_notes` appended
   - Alert is removed from queue (`is_queued_for_reprocess=False`)

## Integration with Background Threading

When an alert is created during real-time video processing, the confirmation step runs in a background thread (non-blocking). Separately, the alert priority queue can be processed as a continuous daemon task via the management command or API.

This design ensures:

- Real-time video processing isn't blocked
- Reprocessing is decoupled and can scale horizontally
- Operators can control queue processing timing

## Example Workflow

1. Real-time camera processes frames and creates alerts
2. Each alert runs auto-confirmation in a background thread (checks last 10 frames)
3. Alert status updated to `investigating` (confirmed) or `false_positive` (not confirmed)
4. Operator reviews alert and decides to reprocess it with different models:
   ```
   POST /api/alerts/123/queue_for_reprocess/ { "priority": 10 }
   ```
5. Background daemon picks up the alert and reprocesses it
6. New detection results stored; alert status and notes updated

## Default Behavior

- **Auto-confirmation**: Every new alert automatically re-checks the last 10 frames with the detection model(s) that triggered it. Defaults to 2/10 frames matching = confirmed.
- **Manual reprocessing**: Operator can queue any alert for reprocessing at any time with custom priority.
- **Attempt limit**: Default max of 3 reprocessing attempts per alert (configurable per enqueue call).

## Configuration

Adjust thresholds in code:

- **Alert confirmation threshold**: Edit `confirm_alert(alert, alert_type, required_hits=2)` in `video_processor.py`
- **Default priority**: Set `reprocess_priority` default in `Alert` model
- **Max attempts**: Pass `max_attempts` when calling `enqueue()`

## Files

- `eyeguard/alert_queue.py` - Priority queue manager
- `eyeguard/video_processor.py` - `reprocess_alert_from_queue()` method
- `eyeguard/models.py` - Alert model fields
- `eyeguard/views.py` - API endpoints
- `eyeguard/management/commands/process_alert_queue.py` - Management command
