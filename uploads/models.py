# uploads/models.py

from django.db import models

class FileUpload(models.Model):
    file_path = models.CharField(max_length=255)
    object_name = models.CharField(max_length=255)
    guid = models.CharField(max_length=255,primary_key=True)
    instance_uid = models.CharField(max_length=255)
    priority = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='queued')  # 'queued', 'uploading', 'paused', 'completed', 'canceled'
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    timestamp = models.FloatField()
    progress = models.FloatField(default=0)
