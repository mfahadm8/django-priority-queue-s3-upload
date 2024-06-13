# tasks.py

import os
import redis
import boto3
from boto3.s3.transfer import TransferConfig
import logging
import time
import traceback
import json
import io  # Import io module
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

def upload_file(file_path, object_name):
    file_size = os.path.getsize(file_path)
    config = TransferConfig(multipart_threshold=1024*25, max_concurrency=10, multipart_chunksize=1024*25, use_threads=True)
    with open(file_path, 'rb') as f:
        s3_client.upload_fileobj(
            f, BUCKET_NAME, object_name,
            Config=config,
            Callback=ProgressPercentage(file_path, file_size)
        )


def update_status_in_queue(queue_name, filename, new_status):
    """
    Updates the status of an item in a Redis Sorted Set based on filename.

    Args:
        queue_name (str): Name of the Redis Sorted Set (e.g., "upload_queue_json").
        filename (str): Filename of the item to update.
        new_status (str): The new status for the item (e.g., "uploading", "completed").
    """
    with r.pipeline() as pipe:
        # Find elements with matching filename
        elements = pipe.zrangebyscore(queue_name, min=0, max=float('inf'), withscores=True)
        # Execute commands in the pipeline
        elements = pipe.execute()[0]

        for member, score in elements:
        # Decode the member (JSON string)
        try:
            data = json.loads(member.decode('utf-8'))
            # Check if filenames match
            if data['file_path'] == filename:
            # Update score if necessary (optional)
            # new_score = calculate_new_score(data)  # Implement logic for new score
            pipe.zremrangebyscore(queue_name, score, score)
            pipe.zadd(queue_name, json.dumps(data), score)  # Update with new status
            logging.info(f"Updated status of {filename} to {new_status} in {queue_name}")
            break  # Exit loop after finding and updating the matching item
        except (json.JSONDecodeError, KeyError):
            logging.error(f"Error decoding or processing element in {queue_name}")

    # Execute remaining pipeline commands (if any)
    pipe.execute()
    
    
def process_queue(queue_name, wait_time):
  logging.debug(f"Starting to process queue: {queue_name}")
  while True:
    try:
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
          timestamp = study_info['timestamp']
          guid = study_info['guid']
          status_key = f'status:{guid}'

          # Update status to 'uploading' in Redis
          r.set(status_key, 'uploading')

          # Upload the file with progress updates
          try:
            total_size = os.path.getsize(file_path)
            upload_file(file_path, os.path.basename(file_path))

            # Upload successful, update status in Redis and database
            r.set(status_key, 'completed')
            r.zrem(queue_name, study_info_str)
            FileUpload.objects.filter(guid=guid).update(status='completed')
            logging.debug(f"Successfully uploaded {file_path} from {queue_name}")

          except Exception as e:
            logging.error(f"Error uploading {file_path} from {queue_name}: {e}")
            r.set(status_key, 'failed')
            FileUpload.objects.filter(guid=guid).update(status='failed')

        else:
          logging.error(f"Invalid data: {serializer.errors}")
    except Exception as e:
      logging.error(traceback.format_exc())
      logging.error(f"Error processing queue {queue_name}: {e}")
    time.sleep(5)

class ProgressPercentage:
  def __init__(self, filename, size):
    self._filename = filename
    self._size = size
    self._seen_so_far = 0

  def __call__(self, bytes_amount):
    self._seen_so_far += bytes_amount
    percentage = (self._seen_so_far / self._size) * 100
    logging.debug(f"Upload progress for {self._filename}: {percentage:.2f}%")
    # Update progress in Redis (optional)
    # r.set(f'progress:{self._filename}', percentage)