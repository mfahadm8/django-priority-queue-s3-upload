import os
import boto3
from celery import shared_task, current_task
from file_uploader.celery import app
import time
from boto3.s3.transfer import S3Transfer, TransferConfig
import logging
from django.apps import apps
from django.conf import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
import django
django.setup()

s3_client = boto3.client('s3')
BUCKET_NAME = 'cdk-hnb659fds-assets-182426352951-ap-southeast-1'
MAX_UPLOADS = os.cpu_count() or 2

# Dictionary to hold upload tasks
upload_tasks = {}

class ProgressPercentage:
    def __init__(self, filename, size, guid):
        self._filename = filename
        self._size = size
        self._seen_so_far = 0
        self._guid = guid
        self._last_saved_progress = 0

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        if percentage - self._last_saved_progress >= 3.0:
            FileUpload = apps.get_model('uploads', 'FileUpload')
            file_upload = FileUpload.objects.get(guid=self._guid)
            file_upload.progress = percentage
            file_upload.save(update_fields=['progress'])
            logger.info(f"Updated progress for {self._guid}: {percentage:.2f}%")
            self._last_saved_progress = percentage

def upload_file(file_path, object_name, guid):
    file_size = os.path.getsize(file_path)
    config = TransferConfig(multipart_threshold=1024*25, max_concurrency=10, multipart_chunksize=1024*25, use_threads=True)
    transfer = S3Transfer(s3_client, config)

    global upload_tasks
    upload_task = transfer.upload_file(
        file_path, BUCKET_NAME, object_name,
        callback=ProgressPercentage(file_path, file_size, guid)
    )
    upload_tasks[guid] = upload_task

@app.task(time_limit=10800)
def process_file_upload(file_path, object_name, guid):
    try:
        logger.info("Worker started")
        logger.info(f"Processing file: {object_name}")
        upload_file(file_path, object_name, guid)
        FileUpload = apps.get_model('uploads', 'FileUpload')
        file_upload = FileUpload.objects.get(guid=guid)
        file_upload.status = 'completed'
        file_upload.progress = 100
        file_upload.save(update_fields=['status', 'progress'])
        if file_path.endswith('.json'):
            pass
        elif file_path.endswith('.zip'):
            pass
        return {'status': 'completed'}
    except Exception as e:
        logger.error(f"Error uploading {file_path}: {e}")
        FileUpload = apps.get_model('uploads', 'FileUpload')
        file_upload = FileUpload.objects.get(guid=guid)
        file_upload.status = 'failed'
        file_upload.save(update_fields=['status'])
        return {'status': 'failed', 'error': str(e)}

def process_queue(queue_name):
    while True:
        try:
            logger.info("Processing queue")
            FileUpload = apps.get_model('uploads', 'FileUpload')
            uploading_tasks = FileUpload.objects.filter(status='uploading').count()
            if uploading_tasks < MAX_UPLOADS:
                file_uploads = FileUpload.objects.filter(status='queued').order_by('-priority', 'timestamp')[:1]
                logger.info(f"Found queued files: {file_uploads}")
                if file_uploads:
                    file_upload = file_uploads[0]
                    file_path = file_upload.file_path
                    object_name = file_upload.object_name
                    guid = file_upload.guid
                    logger.info(f"Uploading file: {object_name}")

                    file_upload.status = 'uploading'
                    file_upload.save(update_fields=['status'])

                    process_file_upload.delay(file_path, object_name, guid)
            else:
                for guid, task in upload_tasks.items():
                    file_upload = FileUpload.objects.get(guid=guid)
                    if file_upload.status == 'paused' or file_upload.status == 'canceled':
                        task.pause()
                        if file_upload.status == 'canceled':
                            del upload_tasks[guid]

            time.sleep(5)
        except Exception as e:
            logger.error(f"Error processing queue {queue_name}: {e}")
            time.sleep(5)
