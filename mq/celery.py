from __future__ import absolute_import

from celery import Celery

app = Celery('task', include=['mq.tasks'])
app.config_from_object('mq.celeryconfig')
