from channels.generic.websocket import AsyncWebsocketConsumer
from .models import FileUpload
import json
import aioredis
import asyncio
import logging

logger = logging.getLogger(__name__)

class UploadProgressConsumer(AsyncWebsocketConsumer):
    guids = []

    async def connect(self):
        await self.accept()
        logger.info("WebSocket connection accepted")

        self.redis = await aioredis.from_url('redis://redis:6379', decode_responses=True)
        await self.start_listening()

    async def disconnect(self, close_code):
        await self.stop_listening()
        await self.redis.close()
        logger.info("WebSocket connection closed")

    async def start_listening(self):
        self.keyspace_channel = f"__keyspace@1__::1:upload_task_*"
        self.pubsub = self.redis.pubsub()
        logger.info("Subscribing to Redis keyspace notifications")
        await self.pubsub.psubscribe(self.keyspace_channel)
        self.listener_task = asyncio.create_task(self.listen_to_redis())
        logger.info("Subscribed to Redis keyspace notifications")

    async def stop_listening(self):
        logger.info("Unsubscribing from Redis keyspace notifications")
        await self.pubsub.punsubscribe(self.keyspace_channel)
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                logger.info("Listener task cancelled")

    async def listen_to_redis(self):
        logger.info("Listening to Redis keyspace notifications")
        async for message in self.pubsub.listen():
            logger.info(f"Received message from Redis: {message}")
            if message['type'] == 'pmessage':
                event_type = message['data']
                key = message['channel'].split(':')[-1]
                for guid in self.guids:
                    if guid in key:
                        if event_type == 'set':
                            value = await FileUpload.get(guid)
                            await self.send(text_data=json.dumps({'event': 'set', 'guid': guid, 'value': value.to_dict()}))
                            logger.info(f"Key {guid} was set to {value}")
                        elif event_type == 'del':
                            await self.send(text_data=json.dumps({'event': 'delete', 'guid': guid}))
                            logger.info(f"Key {guid} was deleted")

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        guid = data.get('guid')

        if action == 'add' and guid:
            if guid not in self.guids:
                self.guids.append(guid)
                logger.info(f"Added GUID {guid} to the list")
                await self.send(text_data=json.dumps({'event': 'guid_added', 'guid': guid}))

        elif action == 'delete' and guid:
            if guid in self.guids:
                self.guids.remove(guid)
                logger.info(f"Removed GUID {guid} from the list")
                await self.send(text_data=json.dumps({'event': 'guid_removed', 'guid': guid}))
