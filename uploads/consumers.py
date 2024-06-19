from channels.generic.websocket import AsyncWebsocketConsumer
import json

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))

    @property
    def file_upload_model(self):
        from django.apps import apps
        return apps.get_model('uploads', 'FileUpload')
