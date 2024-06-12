import boto3
import redis
import os
from django_rq import job

r = redis.Redis()

BUCKET_NAME = 'cdk-hnb659fds-assets-182426352951-ap-southeast-1'

s3_client = boto3.client('s3')

def upload_file(file_path, object_name): # Maintain redis Queue 
    file_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f:
        s3_client.upload_fileobj(
            f, BUCKET_NAME, object_name,
            Callback=ProgressPercentage(file_path, file_size)
        )

class ProgressPercentage:
    def __init__(self, filename, size):
        self._filename = filename
        self._size = size
        self._seen_so_far = 0

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        r.set(f'progress:{self._filename}', percentage)

@job
def queue_file_upload(file_path):
    object_name = os.path.basename(file_path)
    upload_file(file_path, object_name)
