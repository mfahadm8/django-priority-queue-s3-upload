import os
import boto3
import hashlib
from celery import shared_task
import logging
from django.conf import settings
from .models import FileUpload
from django.core.cache import cache
import traceback
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = boto3.client('s3')
BUCKET_NAME = 'cdk-hnb659fds-assets-182426352951-ap-southeast-1'

class S3MultipartUpload:
    PART_MINIMUM = int(5 * 1024 * 1024)

    def __init__(self, bucket, key, local_path, guid, part_size=int(25 * 1024 * 1024), profile_name=None, region_name="ap-southeast-1", verbose=True): # For chunk size > 16, Aws calculates SHA-1 instead of MD5
        self.bucket = bucket
        self.key = key
        self.path = local_path
        self.guid = guid
        self.total_bytes = os.stat(local_path).st_size
        self.part_bytes = part_size
        assert part_size > self.PART_MINIMUM
        self.s3 = boto3.session.Session(profile_name=profile_name, region_name=region_name).client("s3")
        if verbose:
            boto3.set_stream_logger(name="botocore")

    def get_all_parts(self, upload_id):
        parts = self.s3.list_parts(Bucket=self.bucket, Key=self.key, UploadId=upload_id)
        rparts = [{"PartNumber": part["PartNumber"], "ETag": part["ETag"]} for part in parts.get("Parts", [])]
        return rparts

    def get_next_part(self, upload_id):
        parts = self.s3.list_parts(Bucket=self.bucket, Key=self.key, UploadId=upload_id)
        next_part_marker = parts.get("NextPartNumberMarker", 0)
        return next_part_marker

    def abort_resume(self, action):
        mpus = self.s3.list_multipart_uploads(Bucket=self.bucket)
        upload_parts_exists = False
        logger.info(f"FileUpload action {action}")
        if "Uploads" in mpus:
            for u in mpus["Uploads"]:
                upload_id = u["UploadId"]
                if u["Key"] != self.key:
                    continue
                upload_parts_exists = True
                if action == "abort":
                    self.s3.abort_multipart_upload(Bucket=self.bucket, Key=self.key, UploadId=upload_id)
                elif action == "resume":
                    try:
                        next_part = self.get_next_part(upload_id)
                        self.update_progress(next_part - 1)
                        new_parts = self.upload(upload_id, next_part)
                        new_parts = self.get_all_parts(upload_id)
                        self.complete(upload_id, new_parts)
                    except self.s3.exceptions.NoSuchUpload:
                        mpu_id = self.create()
                        new_parts = self.upload(mpu_id, 1)
                        self.complete(mpu_id, new_parts)

        if action == "resume" and not upload_parts_exists:
            mpu_id = self.create()
            new_parts = self.upload(mpu_id, 1)
            self.complete(mpu_id, new_parts)

    def create(self):
        mpu = self.s3.create_multipart_upload(Bucket=self.bucket, Key=self.key)
        mpu_id = mpu["UploadId"]
        return mpu_id

    def upload(self, mpu_id, part_number):
        parts = []
        with open(self.path, "rb") as f:
            for i in range(1, part_number):
                f.read(self.part_bytes)
            while True:
                data = f.read(self.part_bytes)
                if not data:
                    break
                part = self.s3.upload_part(Body=data, Bucket=self.bucket, Key=self.key, UploadId=mpu_id, PartNumber=part_number)
                parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                part_number += 1
                self.update_progress(part_number)
        return parts

    def complete(self, mpu_id, parts):
        result = self.s3.complete_multipart_upload(Bucket=self.bucket, Key=self.key, UploadId=mpu_id, MultipartUpload={"Parts": parts})
        self.verify_checksum()
        return result

    def verify_checksum(self):
        local_checksum = self.calculate_sha256(self.path)
        s3_checksum = self.calculate_s3_sha256(self.bucket, self.key)
        if local_checksum == s3_checksum:
            logger.info(f"Checksum verification passed for {self.path}")
            os.remove(self.path)
        else:
            logger.error(f"Checksum verification failed for {self.path}")

    @staticmethod
    def calculate_sha256(file_path):
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def calculate_s3_sha256(self, bucket, key):
        s3_object = self.s3.get_object(Bucket=bucket, Key=key)
        s3_sha256 = hashlib.sha256(s3_object['Body'].read()).hexdigest()
        return s3_sha256

    def update_progress(self, part_number):
        progress = min(100,(part_number * self.part_bytes / self.total_bytes) * 100)
        logger.info(f"FileUpload progress {self.guid} : {progress}")
        file_upload = FileUpload.get(self.guid, use_task_key=True)
        if not file_upload:
            logger.error(f"FileUpload data not found in cache for guid: {self.guid}")
            raise Exception("Invalid file upload data returned from get method")
        file_upload.progress = progress
        file_upload.bytes_transferred = part_number * self.part_bytes
        file_upload.save()
        task_status_key = f'upload_task_{self.guid}'
        task_guid = cache.get(task_status_key)
        if not task_guid:
            self.abort_resume("abort")
            raise Exception("Upload paused")

@shared_task(time_limit=10800)
def process_file_upload(file_path, object_name, guid):
    try:
        file_upload = FileUpload.get(guid)
        if not file_upload:
            logger.error(f"FileUpload data not found in cache for guid: {guid}")
            raise Exception("Invalid file upload data returned from get method")

        file_upload.status = 'uploading'
        file_upload.save(use_task_key=True)

        file_size = os.stat(file_path).st_size
        file_upload.total_bytes = file_size
        file_upload.save()

        uploader = S3MultipartUpload(BUCKET_NAME, object_name, file_path, guid)
        uploader.abort_resume("resume")

        file_upload.status = 'completed'
        file_upload.progress = 100
        file_upload.save(use_task_key=True)
    except Exception as e:
        logger.error(f"Error processing file upload: {e}\n{traceback.format_exc()}")
        file_upload = FileUpload.get(guid)
        if file_upload:
            file_upload.status = 'failed'
            file_upload.save(use_task_key=True)
        raise e

@shared_task
def process_queue():
    try:
        uploading_tasks = len(FileUpload.filter(prefix='', status='uploading'))
        if uploading_tasks < settings.MAX_UPLOADS:
            file_uploads = sorted(FileUpload.filter(prefix='', status='queued'), key=lambda x: (x.priority, x.created_at))[:1]
            if file_uploads:
                file_upload = file_uploads[0]
                file_path = file_upload.file_path
                object_name = file_upload.object_name
                guid = file_upload.guid
                file_upload.status = 'uploading'
                file_upload.save(use_task_key=True)
                process_file_upload.delay(file_path, object_name, guid)
    except Exception as e:
        logger.error(f"Error processing queue: {e}")
        logger.error(traceback.format_exc())

@shared_task
def monitor_stalled_uploads():
    uploading_tasks = FileUpload.filter(prefix='', status='uploading')
    for file_upload in uploading_tasks:
        if file_upload.is_stalled():
            logger.info(f"Task is in stalled state, changing status to queued")
            file_upload.status = 'queued'
            file_upload.save()
