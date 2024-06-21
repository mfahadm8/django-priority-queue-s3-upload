from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
import asyncio

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.guid = self.scope['url_route']['kwargs']['guid']
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        while True:
            try:
                file_upload = await self.get_file_upload(self.guid)
                response = {
                    'guid': self.guid,
                    'status': file_upload.status,
                    'progress': file_upload.progress
                }
            except self.file_upload_model.DoesNotExist:
                response = {
                    'error': 'File not found',
                    'guid': self.guid 
                }

            await self.send(text_data=json.dumps(response))
            await asyncio.sleep(10)  # Use asyncio.sleep for non-blocking sleep

    @database_sync_to_async
    def get_file_upload(self, guid):
        FileUpload = self.file_upload_model
        return FileUpload.objects.filter(guid=guid).first()
    
    @property
    def file_upload_model(self):
        from django.apps import apps
        return apps.get_model('uploads', 'FileUpload')
