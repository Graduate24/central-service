from kombu import Queue, Exchange

from sacentral.settings import BROKER_URL

BROKER_URL = BROKER_URL

CELERY_TIMEZONE = 'Asia/Shanghai'
# CELERY_TIMEZONE='UTC'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

CELERY_DEFAULT_EXCHANGE = 'tasks'
CELERY_IGNORE_RESULT = True
exchange = Exchange('sa')

CELERY_QUEUES = (
    Queue('sa_engine', exchange, routing_key='sa'),
    Queue('sa_compile', exchange, routing_key='sa'),
    Queue('ml_engine', exchange, routing_key='ml'),
)

CELERY_ROUTES = (
    {'mq.tasks.analysis_task': {'queue': 'sa_engine',
                                'routing_key': 'sa'}},
    {'mq.tasks.compile_task': {'queue': 'sa_compile',
                               'routing_key': 'sa'}},
    {'mq.tasks.ml_analysis_task': {'queue': 'ml_engine',
                                   'routing_key': 'ml'}},
)
