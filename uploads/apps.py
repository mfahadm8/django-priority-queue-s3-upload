import logging
from django.apps import AppConfig
import threading
import os
import sys

logging.basicConfig(level=logging.INFO)


class UploadsConfig(AppConfig):
    name = 'uploads'
    
    def is_celery_command(self):
        """
        Checks if the current command is for Celery.
        """
        logging.info(sys.argv)
        return 'celery_worker' in sys.argv


    def ready(self):
        logging.info("UploadsConfig is ready.")
        # Only run start_observers for main Django app commands
        if not self.is_celery_command():
            def start_all():
                from .observers import start_observers

                # Start observers
                observers_thread = threading.Thread(target=start_observers, daemon=True)
                observers_thread.start()

            threading.Thread(target=start_all, daemon=True).start()
        else:
            print("Running as a Celery worker. Observers will not be started.")
