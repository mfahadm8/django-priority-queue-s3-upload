from django.core.cache import cache
import time
import json
import logging

logger = logging.getLogger(__name__)

class FileUpload:
    def __init__(self, file_path, object_name, guid, instance_uid, priority, total_bytes, status='queued', progress=0, created_at=None, updated_at=None, timestamp=None, bytes_transferred=0):
        self.file_path = file_path
        self.object_name = object_name
        self.guid = guid
        self.instance_uid = instance_uid
        self.priority = priority
        self.status = status
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        self.timestamp = timestamp or time.time()
        self.progress = progress
        self.bytes_transferred = bytes_transferred
        self.total_bytes = total_bytes

    def save(self, use_task_key=False):
        self.updated_at = time.time()
        data = json.dumps(self.to_dict())
        cache.set(self.guid, data)
        if use_task_key or self.status == 'uploading':
            cache.set(f'upload_task_{self.guid}', data)
        elif self.status in ['paused', 'canceled','completed']:
            cache.delete(f'upload_task_{self.guid}')

    def to_dict(self):
        return {
            'file_path': self.file_path,
            'object_name': self.object_name,
            'guid': self.guid,
            'instance_uid': self.instance_uid,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'timestamp': self.timestamp,
            'progress': self.progress,
            'bytes_transferred': self.bytes_transferred,
            'total_bytes': self.total_bytes
        }

    def is_stalled(self):
        stale_threshold = 600
        return time.time() - self.updated_at > stale_threshold

    @classmethod
    def get(cls, guid, use_task_key=False):
        key = f'upload_task_{guid}' if use_task_key else guid
        data = cache.get(key)
        if data:
            try:
                data_dict = json.loads(data)
                return cls(**data_dict)
            except (TypeError, json.JSONDecodeError) as e:
                logger.error(f"Error decoding JSON from cache for key {key}: {e}")
                return None
        return None

    @classmethod
    def filter(cls, prefix='', **kwargs):
        all_keys = cache.keys(f'{prefix}*')
        results = []
        for key in all_keys:
            data = cache.get(key)
            if data:
                try:
                    data_dict = json.loads(data)
                    if isinstance(data_dict, dict) and all(data_dict.get(k) == v for k, v in kwargs.items()):
                        results.append(cls(**data_dict))
                except (TypeError, json.JSONDecodeError):
                    continue
        return results

    @classmethod
    def exists(cls, guid, use_task_key=False):
        key = f'upload_task_{guid}' if use_task_key else guid
        return cache.get(key) is not None

    @classmethod
    def all(cls):
        all_keys = cache.keys('*')
        results = []
        for key in all_keys:
            data = cache.get(key)
            if data:
                try:
                    data_dict = json.loads(data)
                    if isinstance(data_dict, dict):
                        results.append(cls(**data_dict))
                except (TypeError, json.JSONDecodeError):
                    continue
        return results

    def delete(self, use_task_key=False):
        key = f'upload_task_{self.guid}' if use_task_key else self.guid
        cache.delete(self.guid)
        if use_task_key or self.status in ['paused', 'canceled','completed']:
            cache.delete(key)
