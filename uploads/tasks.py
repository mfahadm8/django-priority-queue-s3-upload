import os
import boto3
from celery import shared_task, current_task
from file_uploader.celery import app
import time
from boto3.s3.transfer import S3Transfer, TransferConfig
from .models import FileUpload
from .serializers import FileUploadSerializer
import logging
from .redis_util import redis_connection as r

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
        r.set(f'progress:{self._filename}', percentage)
        current_task.update_state(state='PROGRESS', meta={'progress': percentage})

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

@app.task(time_limit=10800)
def process_file_upload(self, file_path, object_name, guid):
    try:
        upload_file(file_path, object_name)
        r.set(f'status:{guid}', 'completed')
        FileUpload.objects.filter(guid=guid).update(status='completed')
        if file_path.endswith('.json'):
            r.lpush('upload_completed_json_queue', file_path)
        elif file_path.endswith('.zip'):
            r.lpush('upload_completed_zip_queue', file_path)
        return {'status': 'completed'}
    except Exception as e:
        logging.error(f"Error uploading {file_path}: {e}")
        r.set(f'status:{guid}', 'failed')
        FileUpload.objects.filter(guid=guid).update(status='failed')
        return {'status': 'failed', 'error': str(e)}


def process_queue(self, queue_name):
    while True:
        try:
            uploading_tasks = FileUpload.objects.filter(status='uploading').count()
            if uploading_tasks < MAX_UPLOADS:
                study_info_list = r.zrange(queue_name, 0, 0, withscores=False)
                if study_info_list:
                    study_info_str = study_info_list[0].decode('utf-8')
                    study_info = json.loads(study_info_str)
                    serializer = FileUploadSerializer(data=study_info)
                    if serializer.is_valid():
                        study_info = serializer.validated_data
                        file_path = study_info['file_path']
                        object_name = study_info['object_name']
                        guid = study_info['guid']

                        # Update status to 'uploading'
                        r.set(f'status:{guid}', 'uploading')
                        update_status_in_queue(queue_name, file_path, 'uploading')

                        process_file_upload.delay(file_path, object_name, guid)

                        # Remove from the queue
                        r.zrem(queue_name, study_info_str)
                    else:
                        logging.error(f"Invalid data: {serializer.errors}")
            time.sleep(5)
        except Exception as e:
            logging.error(f"Error processing queue {queue_name}: {e}")
            time.sleep(5)
