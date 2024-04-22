import random
import uuid

from django.http import JsonResponse
# Create your views here.
from django.views import View

from analysis.models import Task
from mq.tasks import analysis_task, ml_analysis_task
from utils.response_code import ok
from ws.ws import send_group_message


class TestView(View):
    def get(self, request):
        client = request.GET.get('client', '')
        action = request.GET.get('action', '')
        send_group_message({'action': action, 'data': {'a': 1, 'b': 2}}, client)
        return JsonResponse(ok())


class MqTestView(View):
    def get(self, request):
        client = request.GET.get('id', '')
        ml_analysis_task.delay({'source': client})
        return JsonResponse(ok())


class SysLogTestView(View):
    def get(self, request):
        from utils.syslogger import syslog
        task = Task.objects(id="61949263355bc1c8bed7a18e").first()
        from utils.syslogger import syslog

        extra = {
            'msgid': uuid.uuid1(),
            'structured_data': {
                'task': {
                    'trigger_client': task.trigger_client,
                    'project': {
                        'name': task.project.name,
                        'path': task.project.monitor_path
                    },
                    'sa_result': [{'rule_name': r.ruleName,
                                   'rule_cwe': r.ruleCwe,
                                   'rule_category': r.ruleCategory,
                                   'rule_level': r.ruleLevel,
                                   'detected_count': len(r.detectedResults)} for r in task.result]
                }
            }
        }
        print(extra)
        syslog.info('test message', extra=extra)
        return JsonResponse(ok())
