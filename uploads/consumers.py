# uploads/consumers.py

import json
from channels.generic.websocket import WebsocketConsumer
import redis

r = redis.Redis()

class UploadProgressConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)
        guid = data['guid']
        progress = r.get(f'progress:{guid}')
        self.send(text_data=json.dumps({
            'guid': guid,
            'progress': float(progress) if progress else 0
        }))
