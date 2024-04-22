from kombu import Queue, Exchange

from sacentral.settings import BROKER_URL
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sacentral.settings')
django.setup()

BROKER_URL = BROKER_URL

CELERY_TIMEZONE = 'Asia/Shanghai'
# CELERY_TIMEZONE='UTC'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

CELERY_DEFAULT_EXCHANGE = 'tasks'
CELERY_IGNORE_RESULT = True