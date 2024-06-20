import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
from rest_framework.renderers import JSONRenderer
from .tasks import process_queue
from .models import FileUpload
from .serializers import FileUploadSerializer

WATCHED_DIR = '/tmp/test'

logging.basicConfig(level=logging.DEBUG)

class FileCreationHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            object_name = os.path.basename(file_path)
            guid = object_name
            instance_uid = 'some_instance_uid'
            timestamp = time.time()
            priority = int(timestamp)
            logging.debug(f"New file detected to queue: {guid}")
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
                logging.debug(f"Added file to queue: {file_path}")
            else:
                logging.debug(f"File {file_path} already exists in the queue.")


def start_watcher(extension, queue_name):
    if not os.path.exists(WATCHED_DIR):
        os.makedirs(WATCHED_DIR)

    event_handler = FileCreationHandler()
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
    json_thread = threading.Thread(target=process_queue, args=('upload_queue_json',))
    json_thread.daemon = True
    json_thread.start()

    zip_thread = threading.Thread(target=process_queue, args=('upload_queue_zip',))
    zip_thread.daemon = True
    zip_thread.start()
