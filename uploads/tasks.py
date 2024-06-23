import os
import boto3
from celery import shared_task, Celery
import time
from boto3.s3.transfer import S3Transfer, TransferConfig
import logging
from django.conf import settings
from .models import FileUpload
from django.core.cache import cache
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = boto3.client('s3')
BUCKET_NAME = 'cdk-hnb659fds-assets-182426352951-ap-southeast-1'

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
            file_upload = FileUpload.get(self._guid)
            file_upload.progress = percentage
            file_upload.save()
            logger.info(f"Updated progress for {self._guid}: {percentage:.2f}%")
            self._last_saved_progress = percentage

def upload_file(file_path, object_name, guid):
    file_size = os.path.getsize(file_path)
    config = TransferConfig(multipart_threshold=1024*25, max_concurrency=10, multipart_chunksize=1024*25, use_threads=True)
    transfer = S3Transfer(s3_client, config)

    transfer.upload_file(
        file_path, BUCKET_NAME, object_name,
        callback=ProgressPercentage(file_path, file_size, guid)
    )

@shared_task(time_limit=10800)
def process_file_upload(file_path, object_name, guid):
    try:
        logger.info("Worker started")
        logger.info(f"Processing file: {object_name}")
        upload_file(file_path, object_name, guid)
        file_upload = FileUpload.get(guid)
        file_upload.status = 'completed'
        file_upload.progress = 100
        file_upload.save()
        return {'status': 'completed'}
    except Exception as e:
        logger.error(f"Error uploading {file_path}: {e}")
        logger.error(traceback.format_exc())
        file_upload = FileUpload.get(guid)
        file_upload.status = 'failed'
        file_upload.save()
        return {'status': 'failed', 'error': str(e)}

@shared_task
def process_queue():
    try:
        logger.info("Processing queue")
        uploading_tasks = len(FileUpload.filter(status='uploading'))
        if uploading_tasks < settings.MAX_UPLOADS:
            file_uploads = sorted(FileUpload.filter(status='queued'), key=lambda x: (-x.priority, x.timestamp))[:1]
            logger.info("Uploading files: " + str(uploading_tasks))
            if file_uploads:
                file_upload = file_uploads[0]
                file_path = file_upload.file_path
                object_name = file_upload.object_name
                guid = file_upload.guid
                logger.info(f"Uploading file: {object_name}")
                file_upload.status = 'uploading'
                file_upload.save()

                process_file_upload.delay(file_path, object_name, guid)
        else:
            for key in cache.scan_iter("upload_task_*"):
                task = cache.get(key)
                if task:
                    file_upload = FileUpload.get(key.split('_')[-1])
                    if file_upload and (file_upload.status == 'paused' or file_upload.status == 'canceled'):
                        task.pause()
                        if file_upload.status == 'canceled':
                            cache.delete(key)

    except Exception as e:
        logger.error(f"Error processing queue: {e}")
        logger.error(traceback.format_exc())
