from __future__ import absolute_import

from celery import Celery

app = Celery('task', include=['task.tasks'])
app.config_from_object('task.celeryconfig')
