from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from pathlib import Path

from eyeguard.video_processor import start_camera_processing
from eyeguard.models import Subscription, Business, Camera
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Process a video file for a camera. Can create temporary DB entries for testing.'

    def add_arguments(self, parser):
        parser.add_argument('--camera-id', type=int, help='ID of existing camera to process')
        parser.add_argument('--file', type=str, help='Path to video file to use as camera stream')
        parser.add_argument('--max-frames', type=int, default=None, help='Max frames to process')
        parser.add_argument('--create-temp', action='store_true', help='Create temporary subscription/business/user/camera for testing')

    def handle(self, *args, **options):
        camera_id = options.get('camera_id')
        file_path = options.get('file')
        max_frames = options.get('max_frames')
        create_temp = options.get('create_temp')

        if not camera_id and not file_path and not create_temp:
            raise CommandError('Provide --camera-id or --file with --create-temp, or use --create-temp with --file')

        if create_temp:
            if not file_path:
                raise CommandError('--create-temp requires --file')

            # Create or get a Subscription named 'basic'
            subscription, _ = Subscription.objects.get_or_create(
                name='basic',
                defaults={'max_cameras': 10, 'price': 0.0}
            )

            # Create admin user
            username = f'temp_user_{int(timezone.now().timestamp())}'
            password = 'temp-pass'
            user = User.objects.create_user(username=username, email='', password=password)

            # Create business
            business = Business.objects.create(
                name=f'Temp Business {username}',
                email=f'{username}@example.local',
                subscription=subscription,
                subscription_start_date=timezone.now(),
                subscription_end_date=timezone.now() + timezone.timedelta(days=30),
                is_subscription_active=True,
                admin_user=user,
                is_active=True,
            )

            # Create camera
            cam = Camera.objects.create(
                business=business,
                name=f'Temp Camera {username}',
                location='Test video',
                stream_url=str(Path(file_path).resolve()),
                stream_type='file',
            )

            camera_id = cam.id
            self.stdout.write(self.style.SUCCESS(f'Created temp camera id={camera_id} for file {file_path}'))

        if camera_id:
            self.stdout.write(self.style.NOTICE(f'Starting processing for camera id={camera_id}'))
            try:
                start_camera_processing(camera_id, max_frames=max_frames)
            except Exception as e:
                raise CommandError(f'Processing failed: {e}')
