from django.core.management.base import BaseCommand
from surveillance.video_processor import start_camera_processing
from surveillance.models import Camera


class Command(BaseCommand):
    help = 'Start video processing for a specific camera'

    def add_arguments(self, parser):
        parser.add_argument(
            'camera_id',
            type=int,
            help='ID of the camera to process'
        )
        parser.add_argument(
            '--max-frames',
            type=int,
            default=None,
            help='Maximum number of frames to process (default: continuous)'
        )

    def handle(self, *args, **options):
        camera_id = options['camera_id']
        max_frames = options['max_frames']
        
        try:
            camera = Camera.objects.get(id=camera_id)
            self.stdout.write(
                self.style.SUCCESS(f'Starting processing for camera: {camera.name}')
            )
            
            # Start processing
            start_camera_processing(camera_id, max_frames)
            
        except Camera.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Camera with ID {camera_id} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
