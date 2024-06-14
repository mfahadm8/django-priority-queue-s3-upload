# tasks.py

import os
import redis
import boto3
from boto3.s3.transfer import TransferConfig, S3Transfer
import logging
import time
import traceback
import json
import io
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .models import FileUpload
from .serializers import FileUploadSerializer

logging.basicConfig(level=logging.DEBUG)

r = redis.Redis()
s3_client = boto3.client('s3')
BUCKET_NAME = 'cdk-hnb659fds-assets-182426352951-ap-southeast-1'
MAX_UPLOADS = os.cpu_count() or 2  # Default to 2 if os.cpu_count() is None

class ProgressPercentage:
    def __init__(self, filename, size):
        self._filename = filename
        self._size = size
        self._seen_so_far = 0

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        logging.debug(f"Upload progress for {self._filename}: {percentage:.2f}%")
        # Update progress in Redis
        r.set(f'progress:{self._filename}', percentage)

def upload_file(file_path, object_name):
    file_size = os.path.getsize(file_path)
    config = TransferConfig(multipart_threshold=1024*25, max_concurrency=10, multipart_chunksize=1024*25, use_threads=True)
    transfer = S3Transfer(s3_client, config)
    with open(file_path, 'rb') as f:
        transfer.upload_fileobj(
            f, BUCKET_NAME, object_name,
            callback=ProgressPercentage(file_path, file_size)
        )

def update_status_in_queue(queue_name, filename, new_status):
    with r.pipeline() as pipe:
        elements = pipe.zrangebyscore(queue_name, min=0, max=float('inf'), withscores=True)
        elements = pipe.execute()[0]

        for member, score in elements:
            try:
                data = json.loads(member.decode('utf-8'))
                if data['file_path'] == filename:
                    data['status'] = new_status
                    pipe.zremrangebyscore(queue_name, score, score)
                    pipe.zadd(queue_name, {json.dumps(data): score})
                    logging.info(f"Updated status of {filename} to {new_status} in {queue_name}")
                    break
            except (json.JSONDecodeError, KeyError):
                logging.error(f"Error decoding or processing element in {queue_name}")

        pipe.execute()

def count_uploading_tasks():
    # Count the number of tasks with 'uploading' status
    uploading_tasks = FileUpload.objects.filter(status='uploading').count()
    return uploading_tasks

def process_queue(queue_name, wait_time):
    logging.debug(f"Starting to process queue: {queue_name}")
    while True:
        try:
            if count_uploading_tasks() < MAX_UPLOADS:
                logging.debug(f"Attempting to fetch from queue: {queue_name}")
                study_info_list = r.zrange(queue_name, 0, 0, withscores=False)
                logging.debug(f"Study info from {queue_name}: {study_info_list}")

                if study_info_list:
                    study_info_str = study_info_list[0].decode('utf-8')
                    study_info = json.loads(study_info_str)
                    logging.info(study_info)

                    serializer = FileUploadSerializer(data=study_info)
                    if serializer.is_valid():
                        study_info = serializer.validated_data
                        file_path = study_info['file_path']
                        object_name = study_info['object_name']
                        guid = study_info['guid']
                        status_key = f'status:{guid}'

                        r.set(status_key, 'uploading')
                        update_status_in_queue(queue_name, file_path, 'uploading')

                        try:
                            upload_file(file_path, object_name)

                            r.set(status_key, 'completed')
                            update_status_in_queue(queue_name, file_path, 'completed')
                            r.zrem(queue_name, study_info_str)
                            FileUpload.objects.filter(guid=guid).update(status='completed')
                            logging.debug(f"Successfully uploaded {file_path} from {queue_name}")

                            if file_path.endswith('.json'):
                                r.lpush('upload_completed_json_queue', study_info_str)
                            elif file_path.endswith('.zip'):
                                r.lpush('upload_completed_zip_queue', study_info_str)
                            # Call a dummy API
                            # Implement the dummy API call here if required

                        except Exception as e:
                            logging.error(f"Error uploading {file_path} from {queue_name}: {e}")
                            r.set(status_key, 'failed')
                            update_status_in_queue(queue_name, file_path, 'failed')
                            FileUpload.objects.filter(guid=guid).update(status='failed')

                    else:
                        logging.error(f"Invalid data: {serializer.errors}")
            time.sleep(wait_time)
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f"Error processing queue {queue_name}: {e}")
        time.sleep(wait_time)
