from __future__ import absolute_import

import json
import traceback
import uuid
from datetime import datetime

from analysis.models import Task, Workflow, SaResult, DetectedResult
from analysis.workflow_handlers import next_handler, WorkflowType, merge_result
from attachment.models import FileStorage, FileMeta
from mq.celery import app
# "celery", "-A", "utils" ,"worker", "-l" ,"info", "-Q", "sa_engine_complete",",sa_compile_complete"
from utils.log import logger


def workflow_finish(workflow, success):
    workflow.status = 1 if success else 2
    time_line = workflow.timeline
    time_line.append(datetime.now())
    workflow.timeline = time_line
    workflow.save()


def sa_task_finish(task_id, success, result):
    sa_results = []
    weakness_count = 0
    try:
        if success:
            for k, v in result.items():
                v['ruleId'] = k
                detected_results = []
                for d in v.get('detectedResults'):
                    detected_result = DetectedResult(**d)
                    sink_path = d.get('path')
                    weakness_count += 1
                    facade = '{}:{}'.format(sink_path[-1].get('javaClass'), sink_path[-1].get('line'))
                    detected_result.facade = facade
                    detected_result.save()
                    detected_results.append(detected_result.id)
                sa_result = SaResult(**v)
                sa_result.taskId = task_id
                sa_result.detectedResults = detected_results
                sa_result.save()
                sa_results.append(sa_result.id)
        send_syslog(task_id)
    except Exception as e:
        traceback.print_exc()

    Task.objects(id=task_id).update_one(set__result=sa_results, set__status=2 if success else 3,
                                        set__end=datetime.now(), set__weakness_count=weakness_count, set__progress=100)


def send_syslog(task_id):
    task = Task.objects(id=task_id).first()
    from utils.syslogger import syslog

    extra = {
        'msgid': uuid.uuid1(),
        'structured_data': {
            'task': {
                'trigger_client': task.trigger_client,
                'project': {
                    'name': task.project.name if task.project else '',
                    'path': task.project.monitor_path if task.project else ''
                },
                'sa_result': [{'rule_name': r.ruleName,
                               'rule_cwe': r.ruleCwe,
                               'rule_category': r.ruleCategory,
                               'rule_level': r.ruleLevel,
                               'detected_count': len(r.detectedResults)} for r in task.result]
            }
        }
    }
    logger.info('extra message:{}'.format(extra))
    syslog.info('test message', extra=extra)


def ml_task_finish(task_id, success, result):
    Task.objects(id=task_id).update_one(set__ml_result=result if success else None, set__ml_status=2 if success else 3,
                                        set__ml_end=datetime.now(), set__ml_progress=100)


@app.task(name="sa_finish")
def sa_engine_complete(msg):
    logger.info(msg)
    res = json.loads(msg)
    workflow_id = res.get('workflowId')
    workflow = Workflow.objects(id=workflow_id).first()
    if not workflow:
        logger.info('no workflow found,abort')
        return
    if workflow.progress != workflow.steps:
        workflow.progress = workflow.progress + 1
        workflow.save()
    task = Task.objects(id=res.get('taskId')).only('id').first()
    if not task:
        logger.info('no task found,abort')
        return
    task_success = res.get('success', False)
    sa_task_finish(res.get('taskId'), task_success, res.get('result', None))
    # sa engine ONLY
    if workflow.type in [WorkflowType.compile_sa.value,
                         WorkflowType.sa.value]:
        workflow_finish(workflow, task_success)
    else:
        task = Task.objects(id=res.get('taskId')).only('ml_status').first()
        ml_success = task.ml_status == 2
        if (task_success or ml_success) and workflow == 0:
            workflow.status = 1
            workflow.save()
        if ml_success and task_success:
            merge_result(res.get('taskId'))

    if workflow.progress == workflow.steps:
        logger.info('workflow finished')
        return
    logger.info('handle next')
    next_handler(workflow).handle()


@app.task(name="compile_finish")
def sa_compile_complete(msg):
    logger.info(msg)
    res = json.loads(msg)
    workflow_id = res.get('workflowId')
    workflow = Workflow.objects(id=workflow_id).first()
    if not workflow:
        logger.info('no workflow found,abort')
        return
    if workflow.status != 0:
        logger.info('workflow has handled,abort')
        return
    if workflow.progress == workflow.steps:
        logger.info('workflow has finished')
        return
    if not res['success']:
        logger.info('workflow error')
        workflow.status = 2
        workflow.save()
        return
    file_name = res['compileResult']['name']
    size = res['compileResult']['size']
    object_key = res['compileResult']['objectKey']
    md5 = res['compileResult']['md5']
    fs = FileStorage(name=file_name, size=size, md5=md5,
                     object_key=object_key, status=0, meta_info=FileMeta(), folder='codedb')
    fs.save()
    coded_data = workflow.code_data
    coded_data.compiled = fs
    coded_data.save()
    workflow.code_data = coded_data

    task = workflow.task
    task.target_object_key = object_key
    task.progress = 20
    task.save()
    workflow.task = task

    workflow.progress = workflow.progress + 1
    if workflow.progress == workflow.steps:
        workflow.status = 1
    time_line = workflow.timeline
    time_line.append(datetime.now())
    workflow.timeline = time_line
    workflow.save()
    if workflow.progress == workflow.steps:
        logger.info('workflow finished')
        return
    logger.info('handle next')
    next_handler(workflow).handle()


@app.task(name="mq.tasks.ml_engine_complete")
def ml_engine_complete(msg):
    logger.info(msg)
    res = json.loads(msg)
    workflow_id = res.get('workflowId')
    workflow = Workflow.objects(id=workflow_id).first()
    if not workflow:
        logger.info('no workflow found,abort')
        return
    if workflow.progress != workflow.steps:
        workflow.progress = workflow.progress + 1
        workflow.save()
    task = Task.objects(id=res.get('taskId')).only('id').first()
    if not task:
        logger.info('no task found,abort')
        return
    task_success = res.get('success', False)
    ml_task_finish(res.get('taskId'), task_success, res.get('result', None))
    # ml engine ONLY
    if workflow.type in [WorkflowType.ml.value]:
        workflow_finish(workflow, task_success)
    else:
        task = Task.objects(id=res.get('taskId')).only('status').first()
        sa_success = task.status == 2
        if (task_success or sa_success) and workflow == 0:
            workflow.status = 1
            workflow.save()
        if sa_success and task_success:
            merge_result(res.get('taskId'))
    if workflow.progress == workflow.steps:
        logger.info('workflow finished')
        return
    logger.info('handle next')
    next_handler(workflow).handle()
