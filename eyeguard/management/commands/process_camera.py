from django.core.management.base import BaseCommand, CommandError

from eyeguard.video_processor import start_camera_processing


class Command(BaseCommand):
    help = 'Process an existing camera by id. Usage: process_camera <camera_id> [--max-frames N]'

    def add_arguments(self, parser):
        parser.add_argument('camera_id', type=int, help='ID of the camera to process')
        parser.add_argument('--max-frames', type=int, default=None, help='Maximum frames to process')

    def handle(self, *args, **options):
        camera_id = options.get('camera_id')
        max_frames = options.get('max_frames')

        if not camera_id:
            raise CommandError('camera_id is required')

        self.stdout.write(self.style.NOTICE(f'Starting processing for camera id={camera_id} (max_frames={max_frames})'))
        try:
            start_camera_processing(camera_id, max_frames=max_frames)
        except Exception as e:
            raise CommandError(f'Processing failed: {e}')
