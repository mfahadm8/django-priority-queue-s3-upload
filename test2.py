import aioredis
import asyncio

async def listen_to_redis():
    redis = await aioredis.from_url('redis://0.0.0.0:6379', decode_responses=True)
    keyspace_channel = "__keyspace@1__::1:d57.zip*"  # Listen to all keys in database 0
    pubsub = redis.pubsub()
    await pubsub.psubscribe(keyspace_channel)  # Pattern subscribe to keyspace notifications
    
    print("Subscribed to Redis keyspace notifications for all keys")
    
    async for message in pubsub.listen():
        print(f"Received message from Redis: {message}")
        if message['type'] == 'pmessage':  # Pattern message
            channel = message['channel']
            event_type = message['data']
            key = channel.split(':')[-1]
            if event_type == 'set':
                value = await redis.get(key)
                print(f"Key {key} was set to {value}")
            elif event_type == 'del':
                print(f"Key {key} was deleted")

asyncio.run(listen_to_redis())
