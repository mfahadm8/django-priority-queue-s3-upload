from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
import pika
import threading
from channels.db import database_sync_to_async
from django.apps import apps  # Add this line

logging.getLogger().setLevel(logging.INFO)

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.guid = self.scope['url_route']['kwargs']['guid']
        self.queue_name = f'upload_{self.guid}'

        await self.accept()
        self.listen_to_queue(self.queue_name)

    async def disconnect(self, close_code):
        if hasattr(self, 'rabbitmq_connection'):
            self.rabbitmq_connection.close()

    async def receive(self, text_data):
        logging.info(text_data)
        text_data_json = json.loads(text_data)
        guid = text_data_json['guid']

        try:
            file_upload = await self.get_file_upload(guid)
            if file_upload:
                response = {
                    'guid': guid,
                    'status': file_upload.status,
                    'progress': file_upload.progress
                }
            else:
                response = {
                    'error': 'File not found',
                    'guid': guid
                }
        except Exception as e:
            response = {
                'error': str(e),
                'guid': guid
            }

        await self.send(text_data=json.dumps(response))

    @database_sync_to_async
    def get_file_upload(self, guid):
        FileUpload = apps.get_model('uploads', 'FileUpload')
        return FileUpload.objects.filter(guid=guid).first()

    def listen_to_queue(self, queue_name):
        connection_params = pika.ConnectionParameters(host='rabbitmq')
        self.rabbitmq_connection = pika.BlockingConnection(connection_params)
        channel = self.rabbitmq_connection.channel()
        channel.queue_declare(queue=queue_name)

        def callback(ch, method, properties, body):
            message = json.loads(body)
            self.send(text_data=json.dumps(message))

        channel.basic_consume(
            queue=queue_name, on_message_callback=callback, auto_ack=True)
        
        thread = threading.Thread(target=channel.start_consuming)
        thread.start()
