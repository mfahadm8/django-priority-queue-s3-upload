import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import redis
import json
import time
from .models import FileUpload
from .serializers import FileUploadSerializer

WATCHED_DIR = '/tmp/test'
r = redis.Redis()

logging.basicConfig(level=logging.DEBUG)

class UploadHandler(FileSystemEventHandler):
    def __init__(self, extension, queue_name):
        self.extension = extension
        self.queue_name = queue_name

    def on_created(self, event):
        logging.debug(f"Detected file: {event.src_path}")
        if not event.is_directory and event.src_path.endswith(self.extension):
            file_path = event.src_path
            # Create FileUpload instance
            file_upload = FileUpload(
                file_path=file_path,
                object_name=os.path.basename(file_path),
                guid=os.path.basename(file_path),
                instance_uid='some_instance_uid',
                priority=0,
                status='queued',
                timestamp=time.time()  # Add timestamp for processing delay logic
            )
            # Serialize the instance
            serializer = FileUploadSerializer(file_upload)
            study_info = serializer.data
            # Add to Redis
            r.zadd(self.queue_name, {json.dumps(study_info): 0})  # Default priority 0
            logging.debug(f"Added file to queue: {file_path}")

def start_watcher(extension, queue_name):
    if not os.path.exists(WATCHED_DIR):
        os.makedirs(WATCHED_DIR)

    event_handler = UploadHandler(extension, queue_name)
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()
    logging.debug(f"Started watcher for {extension} files in {queue_name}")

    return observer

def start_observers():
    observers = []
    observers.append(start_watcher('.json', 'upload_queue_json'))
    observers.append(start_watcher('.zip', 'upload_queue_zip'))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()
        for observer in observers:
            observer.join()

def start_queue_processors():
    logging.debug("Starting queue processors.")
    json_thread = threading.Thread(target=process_queue, args=('upload_queue_json', 0.7))
    json_thread.daemon = True
    json_thread.start()

    zip_thread = threading.Thread(target=process_queue, args=('upload_queue_zip', 10))
    zip_thread.daemon = True
    zip_thread.start()
