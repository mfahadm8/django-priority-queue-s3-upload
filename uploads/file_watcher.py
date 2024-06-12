import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
from .tasks import queue_file_upload  
import redis 

r = redis.Redis()

WATCHED_DIR = '/tmp/test'
JSON_OLDER_IN_MIN = 7
ZIP_OLDER_IN_MIN = 10

class UploadHandler(FileSystemEventHandler):
    def __init__(self, extension, older_than_min):
        self.extension = extension
        self.older_than_min = older_than_min

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(self.extension):
            file_age_minutes = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(event.src_path))).total_seconds() / 60
            if file_age_minutes > self.older_than_min:
                queue_file_upload(event.src_path)
                
        if not event.is_directory and event.src_path.endswith(self.extension):
            file_path = event.src_path
            study_info = {
                'path': file_path,
                'guid': os.path.basename(file_path),
                'InstanceUID': 'some_instance_uid'  # This would be derived from your actual use case
            }
            r.zadd('upload_queue', {str(study_info): 0})  # Default priority 0

def check_and_queue_files(extension, older_than_min):
    now = datetime.now()
    for root, _, files in os.walk(WATCHED_DIR):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                file_age_minutes = (now - datetime.fromtimestamp(os.path.getmtime(file_path))).total_seconds() / 60
                if file_age_minutes > older_than_min:
                    queue_file_upload(file_path)

def start_watcher(extension, older_than_min):
    if not os.path.exists(WATCHED_DIR):
        os.makedirs(WATCHED_DIR)

    event_handler = UploadHandler(extension, older_than_min)
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()

    # Check and queue existing files
    check_and_queue_files(extension, older_than_min)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def json_watcher():
    start_watcher('.json', JSON_OLDER_IN_MIN)

def zip_watcher():
    start_watcher('.zip', ZIP_OLDER_IN_MIN)

def start_watchers():
    json_thread = threading.Thread(target=json_watcher)
    json_thread.daemon = True
    json_thread.start()

    zip_thread = threading.Thread(target=zip_watcher)
    zip_thread.daemon = True
    zip_thread.start()

    while True:
        if not json_thread.is_alive():
            print("JSON watcher thread died. Restarting...")
            json_thread = threading.Thread(target=json_watcher)
            json_thread.daemon = True
            json_thread.start()

        if not zip_thread.is_alive():
            print("ZIP watcher thread died. Restarting...")
            zip_thread = threading.Thread(target=zip_watcher)
            zip_thread.daemon = True
            zip_thread.start()

        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    start_watchers()
