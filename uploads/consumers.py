# uploads/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import aioredis
import logging
from .models import FileUpload

logger = logging.getLogger(__name__)

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.guid = self.scope['url_route']['kwargs']['guid']
        self.redis = await aioredis.create_redis_pool('redis://localhost:6379')
        await self.accept()
        logger.info(f"WebSocket connection accepted for GUID: {self.guid}")

        await self.start_listening()

    async def disconnect(self, close_code):
        await self.stop_listening()
        self.redis.close()
        await self.redis.wait_closed()
        logger.info(f"WebSocket connection closed for GUID: {self.guid}")

    async def receive(self, text_data):
        pass

    async def start_listening(self):
        self.pubsub_channel = f"upload_progress_{self.guid}"
        await self.redis.subscribe(self.pubsub_channel)
        self.listener_task = self.channel_layer.loop.create_task(self.listen_to_redis())
        logger.info(f"Subscribed to Redis channel for GUID: {self.guid}")

    async def stop_listening(self):
        await self.redis.unsubscribe(self.pubsub_channel)
        if self.listener_task:
            self.listener_task.cancel()
            logger.info(f"Unsubscribed from Redis channel for GUID: {self.guid}")

    async def listen_to_redis(self):
        channel = self.redis.channels[self.pubsub_channel]
        while await channel.wait_message():
            msg = await channel.get_json()
            await self.send(text_data=json.dumps(msg))
            logger.info(f"Message received from Redis for GUID: {self.guid} - {msg}")
