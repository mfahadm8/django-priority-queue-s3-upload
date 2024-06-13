# uploads/observers.py

import threading
from .file_watcher import start_watcher
from .tasks import process_queue

def start_json_watcher():
    start_watcher('.json', 'upload_queue_json')

def start_zip_watcher():
    start_watcher('.zip', 'upload_queue_zip')

def start_watchers():
    json_thread = threading.Thread(target=start_json_watcher)
    json_thread.daemon = True
    json_thread.start()

    zip_thread = threading.Thread(target=start_zip_watcher)
    zip_thread.daemon = True
    zip_thread.start()

def start_queue_processors():
    json_thread = threading.Thread(target=process_queue, args=('upload_queue_json', 0.7))
    json_thread.daemon = True
    json_thread.start()

    zip_thread = threading.Thread(target=process_queue, args=('upload_queue_zip', 10))
    zip_thread.daemon = True
    zip_thread.start()

def start_observers():
    start_watchers()
    start_queue_processors()
