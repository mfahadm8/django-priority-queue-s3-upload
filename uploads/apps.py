import logging
from django.apps import AppConfig
import threading
import os

logging.basicConfig(level=logging.INFO)

class UploadsConfig(AppConfig):
    name = 'uploads'

    def ready(self):
        logging.info("UploadsConfig is ready.")

        def start_all():
            from .observers import start_observers

            # Start observers
            observers_thread = threading.Thread(target=start_observers, daemon=True)
            observers_thread.start()

        threading.Thread(target=start_all, daemon=True).start()
