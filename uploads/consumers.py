from channels.generic.websocket import AsyncWebsocketConsumer
import json
import aioredis
import asyncio
import logging
from .models import FileUpload

logger = logging.getLogger(__name__)

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.guid = self.scope['url_route']['kwargs']['guid']
        self.redis = await aioredis.from_url('redis://redis:6379', decode_responses=True)
        await self.accept()
        logger.info(f"WebSocket connection accepted for GUID: {self.guid}")

        await self.start_listening()

    async def disconnect(self, close_code):
        await self.stop_listening()
        await self.redis.close()
        logger.info(f"WebSocket connection closed for GUID: {self.guid}")

    async def receive(self, text_data):
        pass

    async def start_listening(self):
        self.pubsub_channel = f"{self.guid}"
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.pubsub_channel)
        self.listener_task = asyncio.create_task(self.listen_to_redis())
        logger.info(f"Subscribed to Redis channel for GUID: {self.guid}")

    async def stop_listening(self):
        await self.pubsub.unsubscribe(self.pubsub_channel)
        if self.listener_task:
            self.listener_task.cancel()
            logger.info(f"Unsubscribed from Redis channel for GUID: {self.guid}")

    async def listen_to_redis(self):
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                msg = json.loads(message['data'])
                await self.send(text_data=json.dumps(msg))
                logger.info(f"Message received from Redis for GUID: {self.guid} - {msg}")
