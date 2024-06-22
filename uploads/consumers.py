from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.guid = self.scope['url_route']['kwargs']['guid']
        await self.accept()
        logger.info(f"WebSocket connection accepted for GUID: {self.guid}")

        # Start listening to database updates
        await self.start_listening()

    async def disconnect(self, close_code):
        # Stop listening to database updates
        await self.stop_listening()
        logger.info(f"WebSocket connection closed for GUID: {self.guid}")

    async def receive(self, text_data):
        pass  # No need to handle messages from the client

    @property
    def file_upload_model(self):
        return apps.get_model('uploads', 'FileUpload')

    async def start_listening(self):
        self.signal_handler = self.create_signal_handler()
        post_save.connect(self.signal_handler, sender=self.file_upload_model)
        logger.info(f"Started listening to database updates for GUID: {self.guid}")

    async def stop_listening(self):
        post_save.disconnect(self.signal_handler, sender=self.file_upload_model)
        logger.info(f"Stopped listening to database updates for GUID: {self.guid}")

    def create_signal_handler(self):
        @receiver(post_save, sender=self.file_upload_model)
        def handle_file_upload_save(sender, instance, **kwargs):
            if instance.guid == self.guid:
                response = {
                    'guid': instance.guid,
                    'status': instance.status,
                    'progress': instance.progress
                }
                logger.info(f"Database update received for GUID: {self.guid} - Progress: {instance.progress}%")
                # Use async_to_sync to send the message in the async context
                async_to_sync(self.send)(text_data=json.dumps(response))

        return handle_file_upload_save
