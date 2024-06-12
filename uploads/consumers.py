import json
from channels.generic.websocket import AsyncWebsocketConsumer
import redis
# import pdb

# pdb.set_trace()
r = redis.Redis()

class UploadProgressConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        await self.accept()
        # self.r = redis.Redis(host='localhost', port=6379, db=0)
        print("connected")

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        filename = "text"
        print("text_data",text_data)
        progress = self.r.get(f'progress:{filename}')
        progress = 0.0
        progress = float(progress) if progress else 0.0

        await self.send(text_data=json.dumps({
            'filename': filename,
            'progress': progress
        }))