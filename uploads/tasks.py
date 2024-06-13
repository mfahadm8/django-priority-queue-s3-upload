# uploads/tasks.py

import os
import redis
import boto3
from boto3.s3.transfer import TransferConfig
import logging
import time
from .models import FileUpload

logging.basicConfig(level=logging.DEBUG)

r = redis.Redis()
s3_client = boto3.client('s3')
BUCKET_NAME = 'cdk-hnb659fds-assets-182426352951-ap-southeast-1'

class ProgressPercentage:
    def __init__(self, filename, size):
        self._filename = filename
        self._size = size
        self._seen_so_far = 0

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        r.set(f'progress:{self._filename}', percentage)

def upload_file(file_path, object_name):
    file_size = os.path.getsize(file_path)
    config = TransferConfig(multipart_threshold=1024*25, max_concurrency=10, multipart_chunksize=1024*25, use_threads=True)
    with open(file_path, 'rb') as f:
        s3_client.upload_fileobj(
            f, BUCKET_NAME, object_name,
            Config=config,
            Callback=ProgressPercentage(file_path, file_size)
        )

def process_queue(queue_name, wait_time):
    logging.debug(f"Starting to process queue: {queue_name}")
    while True:
        try:
            study_info_list = r.zrange(queue_name, 0, 0, withscores=False)
            logging.debug(f"Study info from {queue_name}: {study_info_list}")
            if study_info_list:
                study_info = eval(study_info_list[0])
                file_path = study_info['path']
                timestamp = study_info['timestamp']
                current_time = time.time()

                if current_time - timestamp >= wait_time * 60:
                    file_upload = FileUpload.objects.get(guid=study_info['guid'])
                    if file_upload.status in ['queued', 'paused']:
                        file_upload.status = 'uploading'
                        file_upload.save()

                        object_name = os.path.basename(file_path)
                        try:
                            upload_file(file_path, object_name)
                            file_upload.status = 'completed'
                            file_upload.save()
                            r.zrem(queue_name, str(study_info))
                            logging.debug(f"Successfully uploaded {file_path} from {queue_name}")
                        except Exception as e:
                            file_upload.status = 'failed'
                            file_upload.save()
                            logging.error(f"Error uploading {file_path} from {queue_name}: {e}")
        except Exception as e:
            logging.error(f"Error processing queue {queue_name}: {e}")
        time.sleep(5)
