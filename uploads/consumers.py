from channels.generic.websocket import AsyncWebsocketConsumer
from .models import FileUpload
import json
import aioredis
import asyncio
import logging

logger = logging.getLogger(__name__)

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.guid = self.scope['url_route']['kwargs']['guid']
        logger.info(f"Connecting to Redis at redis://redis:6379 for GUID: {self.guid}")
        self.redis = await aioredis.from_url('redis://redis:6379', decode_responses=True)
        await self.accept()
        logger.info(f"WebSocket connection accepted for GUID: {self.guid}")

        await self.start_listening()

    async def disconnect(self, close_code):
        await self.stop_listening()
        await self.redis.close()
        logger.info(f"WebSocket connection closed for GUID: {self.guid}")

    async def start_listening(self):
        self.keyspace_channel = f"__keyspace@1__::1:upload_task_*"
        self.pubsub = self.redis.pubsub()
        logger.info(f"Subscribing to Redis keyspace notifications for key: {self.guid}")
        await self.pubsub.psubscribe(self.keyspace_channel)
        self.listener_task = asyncio.create_task(self.listen_to_redis())
        logger.info(f"Subscribed to Redis keyspace notifications for key: {self.guid}")

    async def stop_listening(self):
        logger.info(f"Unsubscribing from Redis keyspace notifications for key: {self.guid}")
        await self.pubsub.punsubscribe(self.keyspace_channel)
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                logger.info(f"Listener task cancelled")

    async def listen_to_redis(self):
        logger.info(f"Listening to Redis keyspace notifications for key: {self.guid}")
        async for message in self.pubsub.listen():
            logger.info(f"Received message from Redis: {message}")
            if message['type'] == 'pmessage':
                event_type = message['data']
                if event_type == 'set':
                    value = FileUpload.get(self.guid)
                    await self.send(text_data=json.dumps({'event': 'set', 'value': value.to_dict()}))
                    logger.info(f"Key {self.guid} was set to {value}")
                elif event_type == 'del':
                    await self.send(text_data=json.dumps({'event': 'delete'}))
                    logger.info(f"Key {self.guid} was deleted")

    async def receive(self, text_data):
        pass  # Handle incoming messages if needed
