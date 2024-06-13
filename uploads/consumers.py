# uploads/consumers.py

import json
import redis
from channels.generic.websocket import WebsocketConsumer

r = redis.Redis()

class UploadProgressConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)
        file_path = data['file_path']
        progress = r.get(f'progress:{file_path}')
        self.send(json.dumps({
            'file_path': file_path,
            'progress': float(progress) if progress else 0
        }))
