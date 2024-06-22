import os
import logging
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rest_framework.renderers import JSONRenderer
from .tasks import process_queue
from .models import FileUpload
from .serializers import FileUploadSerializer

WATCHED_DIR = '/tmp/test'
STABILITY_CHECK_INTERVAL = 5  
STABILITY_THRESHOLD = 3  

logging.basicConfig(level=logging.INFO)

class FileCreationHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if self.is_file_stable(file_path):
                self.process_file(file_path)

    def process_file(self, file_path):
        object_name = os.path.basename(file_path)
        guid = object_name
        instance_uid = 'some_instance_uid'
        timestamp = time.time()
        priority = int(timestamp)
        logging.info(f"New file detected to queue: {guid}")
        try:
            if not FileUpload.objects.filter(file_path=file_path).exists():
                file_upload = FileUpload(
                    file_path=file_path,
                    object_name=object_name,
                    guid=guid,
                    instance_uid=instance_uid,
                    priority=priority,
                    status='queued',
                    timestamp=timestamp
                )
                file_upload.save()
                logging.info(f"Added file to queue: {file_path}")
            else:
                logging.info(f"File {file_path} already exists in the queue.")
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")

    def is_file_stable(self, file_path):
        previous_size = -1
        stable_count = 0

        while stable_count < STABILITY_THRESHOLD:
            current_size = os.path.getsize(file_path)
            if current_size == previous_size:
                stable_count += 1
            else:
                stable_count = 0
            previous_size = current_size
            time.sleep(STABILITY_CHECK_INTERVAL)
            logging.info(f"Checking file stability: {file_path}")

        logging.info(f"File is stable: {file_path}")
        return True

def start_watcher(extension, queue_name):
    if not os.path.exists(WATCHED_DIR):
        os.makedirs(WATCHED_DIR)

    event_handler = FileCreationHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()
    logging.info(f"Started watcher for {extension} files in {queue_name}")

    return observer

def start_observers():
    observers = [
        start_watcher('.json', 'upload_queue_json'),
        start_watcher('.zip', 'upload_queue_zip')
    ]

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()
        for observer in observers:
            observer.join()

def start_queue_processors():
    logging.info("Starting queue processors.")
    json_thread = threading.Thread(target=process_queue, args=('upload_queue_json',))
    json_thread.daemon = True
    json_thread.start()

    zip_thread = threading.Thread(target=process_queue, args=('upload_queue_zip',))
    zip_thread.daemon = True
    zip_thread.start()
