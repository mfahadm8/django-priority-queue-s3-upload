from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
import asyncio
from django.db.models.signals import post_save
from django.dispatch import receiver

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.guid = self.scope['url_route']['kwargs']['guid']
        await self.accept()

        # Start listening to database updates
        await self.start_listening()

    async def disconnect(self, close_code):
        # Stop listening to database updates
        await self.stop_listening()

    async def receive(self, text_data):
        pass  # No need to handle messages from the client

    @database_sync_to_async
    def get_file_upload(self, guid):
        FileUpload = self.file_upload_model
        return FileUpload.objects.filter(guid=guid).first()

    @property
    def file_upload_model(self):
        from django.apps import apps
        return apps.get_model('uploads', 'FileUpload')

    async def start_listening(self):
        @database_sync_to_async
        @receiver(post_save, sender=self.file_upload_model)
        def handle_file_upload_save(sender, instance, **kwargs):
            if instance.guid == self.guid:
                response = {
                    'guid': instance.guid,
                    'status': instance.status,
                    'progress': instance.progress
                }
                asyncio.create_task(self.send(text_data=json.dumps(response)))

    async def stop_listening(self):
        # This would stop the signal listening, but signals don't have an easy way to disconnect dynamically in Django.
        pass
