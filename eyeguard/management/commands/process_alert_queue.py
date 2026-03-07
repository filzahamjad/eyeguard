"""
Management command to process the alert reprocessing queue.

This command continuously monitors and processes alerts queued for reprocessing
in priority order. Can be run as a background daemon or scheduled task.

Usage:
    python manage.py process_alert_queue              # Process one batch, exit
    python manage.py process_alert_queue --daemon     # Run continuously
    python manage.py process_alert_queue --interval=5 # Check queue every 5 seconds
"""

import time
import sys
from django.core.management.base import BaseCommand
from eyeguard.alert_queue import AlertPriorityQueue
from eyeguard.video_processor import VideoProcessor


class Command(BaseCommand):
    help = 'Process alerts queued for reprocessing in priority order'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run continuously as a daemon process',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Seconds to wait between queue checks (default: 10)',
        )
        parser.add_argument(
            '--max-batch',
            type=int,
            default=1,
            help='Maximum alerts to process per check (default: 1)',
        )
    
    def handle(self, *args, **options):
        daemon_mode = options.get('daemon', False)
        interval = options.get('interval', 10)
        max_batch = options.get('max_batch', 1)
        
        if daemon_mode:
            self.stdout.write(
                self.style.SUCCESS('📡 Starting alert queue processor in daemon mode')
            )
            self.stdout.write(f'⏱️  Checking queue every {interval} seconds')
            self.process_queue_daemon(interval=interval, max_batch=max_batch)
        else:
            self.stdout.write(
                self.style.SUCCESS('🔄 Processing alert queue (single batch)')
            )
            processed = self.process_queue_batch(max_batch=max_batch)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Processed {processed} alerts')
            )
    
    def process_queue_batch(self, max_batch=1):
        """Process up to max_batch alerts from the queue."""
        processed = 0
        
        for _ in range(max_batch):
            next_alert = AlertPriorityQueue.get_next_alert()
            
            if not next_alert:
                break
            
            try:
                self.stdout.write(
                    f'🔄 Processing alert {next_alert.id} (priority: {next_alert.reprocess_priority})'
                )
                
                # Create processor for the camera
                processor = VideoProcessor(next_alert.camera_id)
                processor.load_models()
                
                # Reprocess the alert
                reprocessed = processor.reprocess_alert_from_queue(next_alert.id)
                
                if reprocessed:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Alert {next_alert.id} reprocessed')
                    )
                    processed += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Alert {next_alert.id} could not be reprocessed')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing alert {next_alert.id}: {e}')
                )
                # Dequeue on error after 3 attempts
                if next_alert.reprocess_attempts >= 3:
                    AlertPriorityQueue.dequeue(next_alert.id)
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Alert {next_alert.id} dequeued after max attempts')
                    )
        
        remaining = AlertPriorityQueue.get_queue_count()
        self.stdout.write(f'📊 Queue status: {remaining} alerts remaining')
        
        return processed
    
    def process_queue_daemon(self, interval=10, max_batch=1):
        """Continuously process the queue in daemon mode."""
        try:
            while True:
                queue_count = AlertPriorityQueue.get_queue_count()
                
                if queue_count > 0:
                    self.stdout.write(f'📬 Queue has {queue_count} alerts to process')
                    processed = self.process_queue_batch(max_batch=max_batch)
                    
                    if processed > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Processed {processed} alert(s)')
                        )
                else:
                    self.stdout.write(f'✨ Queue is empty, waiting...')
                
                self.stdout.write(f'⏳ Checking again in {interval} seconds\n')
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n\n⏹️  Shutting down queue processor')
            )
            sys.exit(0)
