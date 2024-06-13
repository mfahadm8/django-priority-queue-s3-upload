import logging
from django.apps import AppConfig
import threading

logging.basicConfig(level=logging.DEBUG)

class UploadsConfig(AppConfig):
    name = 'uploads'

    def ready(self):
        logging.debug("UploadsConfig is ready.")

        def start_all():
            from .observers import start_observers, start_queue_processors

            # Start observers and queue processors
            observers_thread = threading.Thread(target=start_observers, daemon=True)
            observers_thread.start()

            queue_processors_thread = threading.Thread(target=start_queue_processors, daemon=True)
            queue_processors_thread.start()

        threading.Thread(target=start_all, daemon=True).start()
