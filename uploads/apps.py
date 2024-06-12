from django.apps import AppConfig

class UploadsConfig(AppConfig):
    name = 'uploads'

    def ready(self):
        from .file_watcher import start_watcher_thread
        start_watcher_thread()
