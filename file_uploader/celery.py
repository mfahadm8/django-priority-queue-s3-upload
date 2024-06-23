from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
from uploads.tasks import process_queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'file_uploader.settings')

app = Celery('file_uploader')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls process_queue() every 5 seconds.
    sender.add_periodic_task(5.0, process_queue.s(), name='process queue every 5 seconds')
