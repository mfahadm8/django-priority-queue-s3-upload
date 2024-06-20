from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.apps import apps
import logging
from channels.db import database_sync_to_async

logging.getLogger().setLevel(logging.INFO)

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        logging.info(text_data)
        text_data_json = json.loads(text_data)
        guid = text_data_json['guid']

        FileUpload = self.file_upload_model
        try:
            file_upload = await self.get_file_upload(guid)
            response = {
                'guid': guid,
                'status': file_upload.status,
                'progress': file_upload.progress
            }
        except FileUpload.DoesNotExist:
            response = {
                'error': 'File not found',
                'guid': guid
            }

        await self.send(text_data=json.dumps(response))

    @property
    def file_upload_model(self):
        return apps.get_model('uploads', 'FileUpload')

    async def get_file_upload(self, guid):
        FileUpload = self.file_upload_model
        return await database_sync_to_async(FileUpload.objects.get)(guid=guid)
