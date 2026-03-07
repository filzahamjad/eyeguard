"""
Priority queue system for alert reprocessing.

Alerts can be queued for reprocessing with different priority levels.
The queue processes alerts in priority order (highest first) within the same priority level.
"""

from django.utils import timezone
from .models import Alert
from asgiref.sync import async_to_sync


class AlertPriorityQueue:
    """Manages a priority queue of alerts for reprocessing."""
    
    @staticmethod
    def enqueue(alert_id, priority=5, max_attempts=3):
        """
        Add an alert to the reprocessing queue.
        
        Args:
            alert_id: ID of the Alert to queue
            priority: Priority level 1-10 (10=highest, 5=default)
            max_attempts: Maximum reprocessing attempts allowed (stop if exceeded)
        
        Returns:
            Alert instance or None if alert not found or already max attempts reached
        """
        try:
            alert = Alert.objects.get(id=alert_id)
        except Alert.DoesNotExist:
            return None
        
        # Check if already at max attempts
        if alert.reprocess_attempts >= max_attempts:
            print(f"⚠️ Alert {alert.id} already reprocessed {alert.reprocess_attempts} times (max: {max_attempts})")
            return alert
        
        # Queue the alert
        alert.reprocess_priority = max(1, min(10, priority))  # Clamp to 1-10
        alert.is_queued_for_reprocess = True
        alert.queued_for_reprocess_at = timezone.now()
        alert.save()
        
        print(f"✅ Alert {alert.id} queued for reprocessing (priority: {alert.reprocess_priority})")
        return alert
    
    @staticmethod
    def get_next_alert():
        """
        Get the next alert to reprocess from the queue.
        
        Returns alerts in order of:
        1. Highest priority (10 down to 1)
        2. Oldest queued time (FIFO within same priority)
        
        Returns:
            Alert instance or None if queue is empty
        """
        alert = Alert.objects.filter(
            is_queued_for_reprocess=True
        ).order_by('-reprocess_priority', 'queued_for_reprocess_at').first()
        
        return alert
    
    @staticmethod
    def get_queue_summary():
        """Get summary of queued alerts by priority."""
        queued = Alert.objects.filter(is_queued_for_reprocess=True)
        
        summary = {}
        for alert in queued:
            priority = alert.reprocess_priority
            if priority not in summary:
                summary[priority] = []
            summary[priority].append({
                'id': alert.id,
                'alert_type': alert.alert_type,
                'camera': alert.camera.name,
                'queued_at': alert.queued_for_reprocess_at,
                'attempts': alert.reprocess_attempts,
            })
        
        return summary
    
    @staticmethod
    def dequeue(alert_id):
        """Remove an alert from the reprocessing queue."""
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.is_queued_for_reprocess = False
            alert.save()
            print(f"✅ Alert {alert.id} removed from reprocessing queue")
            return alert
        except Alert.DoesNotExist:
            return None
    
    @staticmethod
    def mark_reprocessed(alert_id):
        """Mark an alert as reprocessed (increment attempts, update timestamp) and broadcast update."""
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.reprocess_attempts += 1
            alert.last_reprocessed_at = timezone.now()
            alert.is_queued_for_reprocess = False
            alert.save()
            print(f"✅ Alert {alert.id} reprocessed (attempt {alert.reprocess_attempts})")
            
            # Broadcast update via WebSocket
            try:
                from eyeguard.consumers import broadcast_alert
                async_to_sync(broadcast_alert)(alert, event_type='alert_updated')
            except Exception as e:
                print(f"⚠️ Failed to broadcast alert update: {e}")
            
            return alert
        except Alert.DoesNotExist:
            return None
    
    @staticmethod
    def get_queue_count():
        """Get the number of alerts currently in the queue."""
        return Alert.objects.filter(is_queued_for_reprocess=True).count()
