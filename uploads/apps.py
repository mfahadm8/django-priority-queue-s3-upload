from django.apps import AppConfig
from .observers import start_observers

class UploadsConfig(AppConfig):
    name = 'uploads'

    def ready(self):
        start_watchers()
