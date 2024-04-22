# Create your views here.
import json
import mimetypes
import ntpath
import os
import posixpath
import traceback
from itertools import groupby
from pathlib import Path

from bson import ObjectId
from django.http import (
    FileResponse, Http404, HttpResponseNotModified,
)
from django.http import JsonResponse
from django.utils._os import safe_join
from django.utils.http import http_date
from django.utils.translation import gettext as _
from django.views.generic.base import View
from django.views.static import directory_index, was_modified_since

from analysis.models import Rule, Task, CodeData, RuleTemplate, RuleCategory, DetectedResult, TaskAuditStatistic, \
    MonitorProject, SaResult
from analysis.workflow_handlers import post_codedata, init_workflow, WorkflowType, next_handler, merge_result
from attachment.models import FileStorage
from sacentral.settings import CODE_ROOT
from utils.log import logger
from utils.mongo_json import MongoJsonResponse, clean, to_dict
from utils.response_code import ok, mongoengine_page, request_page, ERROR, page_get, page
from utils.zip_util import extractall


class RuleView(View):
    def post(self, request):
        """
        @api {POST} api/analysis/rule 创建规则
        @apiVersion 1.0.0
        @apiName Create Rule
        @apiGroup Rule
        @apiDescription 创建规则

        @apiParam {String} name 名称
        @apiParam {String} description 描述
        @apiParam {Number} [default] 是否默认，1 默认，0 非默认
        @apiParam {List} sink sink列表
        @apiParam {List} source source列表
        @apiParam {String} cwe cwe编号
        @apiParam {String} category 缺陷分类id
        @apiParam {String} [engine=thusa] 引擎
        @apiParam {Number} [level=1] level，1,低，2，中，3,高

        @apiParamExample {json} Request-Example:
        {
            "name":"rule",
            "default":1,
            "cwe":"CWE-398",
            "category": {
                "name": "安全功能",
                "is_deleted": 0,
                "description": "安全功能",
                "id": "610cde17eebaabab23aaa1a6"
            },
            "engine":"thusa",
            "level":1,
            "source":[
                "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>"
            ],
            "sink":[
                "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>"
            ]
        }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "_id": "60f8d49e6a828ecea1b621ee",
                    "name": "规则a",
                    "cwe": "CWE-398",
                    "category": "API滥用",
                    "engine": "thusa",
                    "level": 1,
                    "source": [
                        "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>"
                    ],
                    "sink": [
                        "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>"
                    ],
                    "is_deleted": 0,
                    "status": 1,
                    "default": 0,
                    "description": "adsfasdfa",
                    "date_created": "2021-07-22 10:14:54"
                }
            }
        """
        data_dict = clean(request.REQUEST, Rule.only_fields())
        category = data_dict.get('category', None)
        if isinstance(category, dict):
            data_dict.update({'category': category.get('id', None)})
        rule = Rule.from_json(json.dumps(data_dict))
        rule.save()
        return MongoJsonResponse(ok(rule))

    def put(self, request, id):
        """
        @api {PUT} api/analysis/rule/:id 编辑规则
        @apiVersion 1.0.0
        @apiName Update Rule
        @apiGroup Rule
        @apiDescription 编辑规则

        @apiParam {String} id id
        @apiParam {String} [name] 名称
        @apiParam {String} [description] 描述
        @apiParam {Number} [default] 是否默认，1 默认，0 非默认
        @apiParam {List} [sink] sink列表
        @apiParam {List} [source] source列表
        @apiParam {String} [cwe] cwe编号
        @apiParam {String} [category] 缺陷分类id
        @apiParam {String} [engine] 引擎
        @apiParam {Number} [level] level，1,低，2，中，3,高
        @apiParamExample {json} Request-Example:
        {
            "name":"rule",
            "default":1,
            "source":[
                "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>"
            ],
            "sink":[
                "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>"
            ]
        }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": null
            }
        """
        doc = Rule.objects(id=id, is_deleted=0).first()
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)

        data_dict = clean(request.REQUEST, Rule.only_fields())
        category = data_dict.get('category', None)
        if isinstance(category, dict):
            data_dict.update({'category': category.get('id', None)})
        data_json = json.dumps(data_dict)
        rule = Rule.from_json(data_json)

        obj_list = dir(doc)
        for k in data_dict.keys():
            if k in obj_list:
                setattr(doc, k, getattr(rule, k))
        doc.save()
        return MongoJsonResponse(ok())

    def get(self, request, id):
        """
        @api {GET} api/analysis/rule/:id 规则详情
        @apiVersion 1.0.0
        @apiName Rule Detail
        @apiGroup Rule
        @apiDescription 规则详情

        @apiParam {String} id 规则id

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "_id": "60f8d49e6a828ecea1b621ee",
                    "name": "规则a",
                    "cwe": "CWE-398",
                    "category": {
                        "name": "安全功能",
                        "is_deleted": 0,
                        "description": "安全功能",
                        "id": "610cde17eebaabab23aaa1a6"
                    },
                    "engine": "thusa",
                    "level": 1,
                    "source": [
                        "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>"
                    ],
                    "sink": [
                        "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>"
                    ],
                    "is_deleted": 0,
                    "status": 1,
                    "default": 0,
                    "description": "adsfasdfa",
                    "date_created": "2021-07-22 10:14:54"
                }
            }
        """
        rule = Rule.objects(id=id, is_deleted=0).first()
        if rule is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        return MongoJsonResponse(ok(to_dict()(rule)))

    def delete(self, request, id):
        """
        @api {DELETE} api/analysis/rule/:id 删除规则
        @apiVersion 1.0.0
        @apiName Rule Delete
        @apiGroup Rule
        @apiDescription 删除规则

        @apiParam {String} id 规则id

        @apiSuccessExample Response-Success:
        HTTP 1.1/ 200K
        {
            "code": 200,
            "msg": "ok"
        }
        """
        rule = Rule.objects(id=id, is_deleted=0).first()
        if rule is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        # check rule template
        template = RuleTemplate.objects(rules__contains=id, is_deleted=0).first()
        if template:
            return JsonResponse(ERROR.DELETE_REFERENCE_ERROR('被规则集“{}”引用'.format(template.name)))
        Rule.objects(id=id).update_one(set__is_deleted=1)
        return MongoJsonResponse(ok())


class RuleListView(View):
    query_fields = 'name', 'cwe', 'category', 'engine', 'level', 'status', 'default'
    list_exclude = ['source', 'sink']

    def get(self, request):
        """
        @api {GET} api/analysis/rule/list 规则列表
        @apiVersion 1.0.0
        @apiName Rule List
        @apiGroup Rule
        @apiDescription 规则列表

        @apiParam {Number}  [page=1] 当前页码
        @apiParam {Number}  [limit=25] 每页记录数
        @apiParam {Number}  [level] level
        @apiParam {Number}  [status] 状态
        @apiParam {String}  [name] 规则名称
        @apiParam {String}  [cwe] cwe
        @apiParam {String}  [category] 类别id
        @apiParam {String}  [engine] 引擎


        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 25,
                "totalItems": 3,
                "totalPages": 1,
                "data": [
                   {
                    "_id": "60f8d49e6a828ecea1b621ee",
                    "name": "规则a",
                    "cwe": "CWE-398",
                    "category": {
                        "name": "安全功能",
                        "is_deleted": 0,
                        "description": "安全功能",
                        "id": "610cde17eebaabab23aaa1a6"
                    },
                    "engine": "thusa",
                    "level": 1,
                    "source": [
                        "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>"
                    ],
                    "sink": [
                        "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>"
                    ],
                    "is_deleted": 0,
                    "status": 1,
                    "default": 0,
                    "description": "adsfasdfa",
                    "date_created": "2021-07-22 10:14:54"
                },
                    {
                    "_id": "60f8d49e6a828ecea1b621ee",
                    "name": "规则a",
                    "cwe": "CWE-398",
                    "category": {
                        "name": "安全功能",
                        "is_deleted": 0,
                        "description": "安全功能",
                        "id": "610cde17eebaabab23aaa1a6"
                    },
                    "engine": "thusa",
                    "level": 1,
                    "source": [
                        "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>"
                    ],
                    "sink": [
                        "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>"
                    ],
                    "is_deleted": 0,
                    "status": 1,
                    "default": 0,
                    "description": "adsfasdfa",
                    "date_created": "2021-07-22 10:14:54"
                }
                ]
            }
        }
        """
        page, per_page = request_page(request)
        query = clean(dict(request.GET.dict(), **request.REQUEST), self.__class__.query_fields)
        query['is_deleted'] = 0
        return MongoJsonResponse(
            ok(mongoengine_page(Rule, query, page, per_page, exclude=self.__class__.list_exclude, map=to_dict())))


class TaskListView(View):
    query_fields = Task.only_fields() + ('start__gte', 'start__gt', 'end__lt', 'end__lte',
                                         'start__lte', 'start__lt', 'end__gt', 'end__gte',
                                         'trigger_client__startswith', 'weakness_count__gte', 'weakness_count__lte',
                                         'audit_count__gte', 'audit_count__lte')
    list_exclude = 'result', 'ml_result', 'rule_snapshot', 'rule_template_snapshot', 'trigger_monitor'

    def get(self, request):
        """
        @api {GET} api/analysis/task/list 任务列表
        @apiVersion 1.0.0
        @apiName Task List
        @apiGroup Analysis
        @apiDescription 任务列表

        @apiParam {Number}  [page=1] 当前页码
        @apiParam {Number}  [limit=25] 每页记录数
        @apiParam {Number}  [status] 任务状态1，进行中，2,成功，3,异常
        @apiParam {String}  [trigger_client__startswith] 任务触发客户端ip
        @apiParam {Number}  [type] 任务引擎类型，1,静态分析，2,机器学习，3,静态分析和机器学习
        @apiParam {String}  [start__gte] 任务开始时间from
        @apiParam {String}  [start__lte] 任务开始时间to
        @apiParam {String}  [end__gte] 任务结束时间from
        @apiParam {String}  [end__lte] 任务结束时间to
        @apiParam {Number}  [weakness_count__gte] 缺陷数量from
        @apiParam {Number}  [weakness_count__lte] 缺陷数量to
        @apiParam {Number}  [audit_count__gte] 缺陷数量from
        @apiParam {Number}  [audit_count__lte] 缺陷数量to

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 25,
                "totalItems": 1,
                "totalPages": 1,
                "data": [
                    {
                        "_id": "60f6708becc743b3fde86c31",
                        "trigger_client": "172.20.0.9:54580",
                        "target_object_key": "codedb/a098124a664b263469e0436721d6eb21/jsp-demo1.zip",
                        "target_object_name": "jsp-demo1.war", // 原文件名称
                        "code_data": "60f6707e5c900a3bd0a57a54", // 代码库id
                        "rule_snapshot": [],
                        "is_deleted": 0,
                        "type": 3,
                        "status": 2,
                        "progress": 100,
                        "start": "2021-07-20 14:43:23",
                        "end": "2021-07-20 14:43:34",
                        "ml_status": 2,
                        "ml_progress": 100,
                        "ml_start": "2021-07-20 14:43:23",
                        "ml_end": "2021-07-20 14:43:36",
                        "date_created": "2021-07-20 14:43:23"
                    }
                ]
            }
        }
        """
        page, per_page = request_page(request)
        query = clean(dict(request.GET.dict(), **request.REQUEST), self.__class__.query_fields)
        query['is_deleted'] = 0
        return MongoJsonResponse(
            ok(mongoengine_page(Task, query, page, per_page, self.__class__.list_exclude, '-date_created')))


class TaskView(View):
    def get(self, request, id):
        """
        @api {GET} api/analysis/task/:id 任务详情
        @apiVersion 1.0.0
        @apiName Task Detail
        @apiGroup Analysis
        @apiDescription 任务详情

        @apiParam {String} id 任务id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "_id": "60f6708becc743b3fde86c31",
                "trigger_client": "172.20.0.9:54580",
                "target_object_key": "codedb/a098124a664b263469e0436721d6eb21/jsp-demo1.zip",
                "target_object_name": "jsp-demo1.war",
                "code_data": "60f6707e5c900a3bd0a57a54",
                "rule_snapshot": [
                    {
                        "rule_id": "60c86a23a27aab4a6ab26330",
                        "source": [
                            "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>"
                        ],
                        "sink": [
                            "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>"
                        ]
                    }
                ],
                "is_deleted": 0,
                "type": 3,
                "status": 2,
                "progress": 100,
                "start": "2021-07-20 14:43:23",
                "end": "2021-07-20 14:43:34",
                 "result": [
                    {
                        "taskId": "611b8e010efe5100ccf07466",
                        "ruleId": "60c86a23a27aab4a6ab26330",
                        "ruleName": "远端命令注入",
                        "ruleCwe": "CWE-78",
                        "ruleCategory": "安全功能",
                        "ruleLevel": 1,
                        "is_deleted": 0,
                        "detectedResults": [
                            {
                                "sourceSig": "<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>",
                                "sinkSig": "<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>",
                                "path": [
                                    {
                                        "file": "org.apache.jsp.welcome_jsp",
                                        "function": "<org.apache.jsp.welcome_jsp: void _jspService(jakarta.servlet.http.HttpServletRequest,jakarta.servlet.http.HttpServletResponse)>",
                                        "jimpleStmt": "r35 = interfaceinvoke r0.<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>(\"j_username\")",
                                        "javaStmt": "r35 = interfaceinvoke r0.<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>(\"j_username\")",
                                        "jspStmt": "r35 = interfaceinvoke r0.<jakarta.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>(\"j_username\")",
                                        "line": 142
                                    },
                                    {
                                        "file": "org.apache.jsp.welcome_jsp",
                                        "function": "<org.apache.jsp.welcome_jsp: void _jspService(jakarta.servlet.http.HttpServletRequest,jakarta.servlet.http.HttpServletResponse)>",
                                        "jimpleStmt": "r6 = virtualinvoke r35.<java.lang.String: java.lang.String[] split(java.lang.String)>(\" \")",
                                        "javaStmt": "r6 = virtualinvoke r35.<java.lang.String: java.lang.String[] split(java.lang.String)>(\" \")",
                                        "jspStmt": "r6 = virtualinvoke r35.<java.lang.String: java.lang.String[] split(java.lang.String)>(\" \")",
                                        "line": 148
                                    },
                                    {
                                        "file": "org.apache.jsp.welcome_jsp",
                                        "function": "<org.apache.jsp.welcome_jsp: void _jspService(jakarta.servlet.http.HttpServletRequest,jakarta.servlet.http.HttpServletResponse)>",
                                        "jimpleStmt": "$r39[0] = r6",
                                        "javaStmt": "$r39[0] = r6",
                                        "jspStmt": "$r39[0] = r6",
                                        "line": 149
                                    },
                                    {
                                        "file": "org.apache.jsp.welcome_jsp",
                                        "function": "<org.apache.jsp.welcome_jsp: void _jspService(jakarta.servlet.http.HttpServletRequest,jakarta.servlet.http.HttpServletResponse)>",
                                        "jimpleStmt": "$r41 = virtualinvoke r38.<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>(null, $r39)",
                                        "javaStmt": "$r41 = virtualinvoke r38.<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>(null, $r39)",
                                        "jspStmt": "$r41 = virtualinvoke r38.<java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])>(null, $r39)",
                                        "line": 149
                                    }
                                ],
                                "audit": null,
                                "facade": "org.apache.jsp.welcome_jsp:149",
                                "_id": "611b8e0a03cb3a4b762aba09",
                                "id": "611b8e0a03cb3a4b762aba09"
                            }
                        ],
                        "_id": "611b8e0a03cb3a4b762aba0a",
                        "id": "611b8e0a03cb3a4b762aba0a"
                    }
                ],
                "weakness_count": 1,
                "audit_count": null,
                "ml_status": 2,
                "ml_progress": 100,
                "ml_start": "2021-07-20 14:43:23",
                "ml_end": "2021-07-20 14:43:36",
                "ml_result": [
                    {
                        "file": "/home/model-server/tmp/tmpnanae574/jsp-demo1/jsp-demo1/org.apache.jsp.welcome_jsp.jimple",
                        "label": "1"
                    },
                    {
                        "file": "/home/model-server/tmp/tmpnanae574/jsp-demo1/jsp-demo1/org.apache.jsp.login_jsp.jimple",
                        "label": "1"
                    }
                ],
                "date_created": "2021-07-20 14:43:23"
            }
        }
        """
        task = Task.objects(id=id, is_deleted=0).first()
        if task is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        # todo code_data
        ret = to_dict(exclude=['code_data', 'project', 'trigger_monitor'])(task)
        ret['code_data'] = str(task.code_data.id) if task.code_data else None
        if task.project:
            project = MonitorProject.objects(id=task.project.id).exclude('change_log', 'files').first()
            if project:
                ret['project'] = to_dict(exclude=['change_log', 'files', 'monitor'])(project)
                monitor = project.monitor
                if monitor:
                    ret['trigger_monitor'] = {'_id': str(monitor.id), 'name': monitor.name}
        return MongoJsonResponse(ok(ret))

    def post(self, request):
        return JsonResponse(ok())

    def delete(self, request, id):
        """
        @api {DELETE} api/analysis/task/:id 删除任务
        @apiVersion 1.0.0
        @apiName Task Delete
        @apiGroup Analysis
        @apiDescription 删除任务

        @apiParam {String} id 任务id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        task = Task.objects(id=id, is_deleted=0).first()
        if task is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        Task.objects(id=id).update_one(set__is_deleted=1)
        SaResult.objects(taskId=id).update(set__is_deleted=1)
        return JsonResponse(ok())


class TaskReanalysisView(View):
    def post(self, request, id):
        task = Task.objects(id=id).first()
        if task is None:
            return JsonResponse(ERROR.NOT_FOUND_404)

        return JsonResponse(ok())


class TaskMergeView(View):
    def post(self, request, id):
        task = Task.objects(id=id).first()
        if task is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        if not task.ml_result or not task.result:
            return JsonResponse(ERROR.ENGINE_NOT_READY)
        merge_result(id)
        return JsonResponse(ok())


class FileCodeView(View):
    def post(self, request, id):
        """
        @api {POST} api/analysis/file/:id/code 上传代码新建仓库
        @apiVersion 1.0.0
        @apiName Code Create
        @apiGroup Analysis
        @apiDescription 新建代码库。根据上传的代码文件，创建代码仓库

        @apiParam {String} id 文件id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        file = FileStorage.objects(id=id, is_deleted=0).exclude('part_record').first()
        if not file:
            return JsonResponse(ERROR.NOT_FOUND_404)
        code_data = post_codedata(file)
        # init workflow
        workflow = init_workflow(WorkflowType.compile.value, code_data, 'localhost')
        handler = next_handler(workflow)
        if handler:
            handler.handle()
        return JsonResponse(ok())


class CodeListView(View):
    def get(self, request):
        """
        @api {GET} api/analysis/code/list 代码仓库列表
        @apiVersion 1.0.0
        @apiName Code List
        @apiGroup Analysis
        @apiDescription 代码仓库列表

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 1,
                "totalItems": 41,
                "totalPages": 41,
                "data": [
                    {
                        "_id": "60f675945c900a3bd0a57a56",
                        "source_name": "jsp-demo1.war",
                        "source": "60f6707e5c900a3bd0a57a53",
                        "compiled": "60f675a11e794dd820e86c31",
                        "is_deleted": 0,
                        "date_created": "2021-07-20 15:04:52"
                    }
                ]
            }
        }
        """
        page, per_page = page_get(request.GET)
        query = {'is_deleted': 0}
        return MongoJsonResponse(ok(mongoengine_page(CodeData, query, page, per_page)))


class CodeTaskView(View):
    def post(self, request, id):
        """
        @api {POST} api/analysis/code/:id/task 选择代码开始任务
        @apiVersion 1.0.0
        @apiName Local code task
        @apiGroup Analysis
        @apiDescription 选择代码开始任务

        @apiParam {String} id 代码仓库id
        @apiParam {String} rule_template_id 规则模板id
        @apiParam {Integer} [timeout] 最大等待时间 1-30 单位分钟
        @apiParam {Integer} [max_memory] 最大内存 1-16 单位g

        @apiParamExample {json} Request-Example:
        {
            "rule_template_id":"xxx",
        }
        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        code_data = CodeData.objects(id=id).first()
        if code_data is None:
            return JsonResponse(ERROR.NOT_FOUND_404)

        rule_template_id = request.REQUEST.get('rule_template_id', None)
        if not rule_template_id:
            rule_template = RuleTemplate.objects(is_deleted=0, status=1, default=1).first()
        else:
            rule_template = RuleTemplate.objects(is_deleted=0, status=1, id=rule_template_id).first()

        if not rule_template:
            logger.info('no default rule template found')
            return JsonResponse(ERROR.NOT_FOUND_404)
        timeout = int(request.REQUEST.get('timeout', 20))
        max_memory = int(request.REQUEST.get('max_memory', 6))

        workflow = init_workflow(WorkflowType.sa_ml.value if code_data.compiled else WorkflowType.compile_sa_ml.value,
                                 code_data, 'localhost', rule_template)
        handler = next_handler(workflow, timeout, max_memory)
        if handler:
            handler.handle()
        return JsonResponse(ok())


class CodeView(View):

    def post(self, request):
        data_dict = clean(request.REQUEST, CodeData.only_fields())
        code = CodeData.from_json(json.dumps(data_dict))
        code.save()
        return MongoJsonResponse(ok(code))

    def put(self, request, id):
        doc = CodeData.objects(id=id, is_deleted=0).first()
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)

        data_dict = clean(request.REQUEST, CodeData.only_fields())
        data_json = json.dumps(data_dict)
        client = CodeData.from_json(data_json)

        obj_list = dir(doc)
        for k in data_dict.keys():
            if k in obj_list:
                setattr(doc, k, getattr(client, k))
        doc.save()
        return MongoJsonResponse(ok())

    def delete(self, request, id):
        """
        @api {DELETE} api/analysis/code/:id 删除代码
        @apiVersion 1.0.0
        @apiName code delete
        @apiGroup Analysis
        @apiDescription 删除代码

        @apiParam {String} id 代码仓库id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        doc = CodeData.objects(id=id, is_deleted=0).first()
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        task = Task.objects(code_data=id, is_deleted=0).first()
        if task:
            return JsonResponse(
                ERROR.DELETE_REFERENCE_ERROR('被创建于 {}，由节点{}触发的任务引用'.format(task.date_created, task.trigger_client)))
        CodeData.objects(id=id).update_one(set__is_deleted=1)
        return JsonResponse(ok())


def rebase_dir(path, newroot):
    if path and path[0] == '/':
        path = path[1:]
    path = os.path.normpath(os.path.join(newroot, path))

    # Prevent visiting parent directory
    if os.path.relpath(path, newroot).startswith(os.pardir):
        path = newroot

    return path


class CodeDirectoryView(View):
    def path_to_dict(self, path):
        d = {'name': ntpath.basename(path)}
        if os.path.isdir(path):
            d['type'] = "directory"
            d['children'] = [self.path_to_dict(os.path.join(path, x)) for x in os.listdir(path)]
        else:
            d['type'] = "file"
        return d

    def get(self, request, id):
        """
        @api {GET} api/analysis/code/:id/listdir 仓库文件树
        @apiVersion 1.0.0
        @apiName Code Dir List
        @apiGroup Analysis
        @apiDescription 仓库文件树

        @apiParam {String} id 仓库id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "name": "60f675945c900a3bd0a57a56",
                "type": "directory",
                "children": [
                    {
                        "name": "jsp-demo1",
                        "type": "directory",
                        "children": [
                            {
                                "name": "WEB-INF",
                                "type": "directory",
                                "children": [
                                    {
                                        "name": "lib",
                                        "type": "directory",
                                        "children": [
                                            {
                                                "name": "jakarta.servlet.jsp.jstl-2.0.0.jar",
                                                "type": "file"
                                            },
                                            {
                                                "name": "jakarta.activation-2.0.0.jar",
                                                "type": "file"
                                            },
                                            {
                                                "name": "jakarta.servlet-api-5.0.0.jar",
                                                "type": "file"
                                            },
                                            {
                                                "name": "jakarta.xml.bind-api-3.0.0.jar",
                                                "type": "file"
                                            },
                                            {
                                                "name": "jakarta.el-api-4.0.0.jar",
                                                "type": "file"
                                            },
                                            {
                                                "name": "jakarta.servlet.jsp.jstl-api-2.0.0.jar",
                                                "type": "file"
                                            }
                                        ]
                                    },
                                    {
                                        "name": "web.xml",
                                        "type": "file"
                                    }
                                ]
                            },
                            {
                                "name": "login.jsp",
                                "type": "file"
                            },
                            {
                                "name": "welcome.jsp",
                                "type": "file"
                            },
                            {
                                "name": "org.apache.jsp.welcome_jsp.jimple",
                                "type": "file"
                            },
                            {
                                "name": "org.apache.jsp.login_jsp.jimple",
                                "type": "file"
                            },
                            {
                                "name": "org",
                                "type": "directory",
                                "children": [
                                    {
                                        "name": "apache",
                                        "type": "directory",
                                        "children": [
                                            {
                                                "name": "jsp",
                                                "type": "directory",
                                                "children": [
                                                    {
                                                        "name": "welcome_jsp.class.smap",
                                                        "type": "file"
                                                    },
                                                    {
                                                        "name": "welcome_jsp.java",
                                                        "type": "file"
                                                    },
                                                    {
                                                        "name": "login_jsp.class.smap",
                                                        "type": "file"
                                                    },
                                                    {
                                                        "name": "login_jsp.class",
                                                        "type": "file"
                                                    },
                                                    {
                                                        "name": "login_jsp.java",
                                                        "type": "file"
                                                    },
                                                    {
                                                        "name": "welcome_jsp.class",
                                                        "type": "file"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "name": "META-INF",
                                "type": "directory",
                                "children": [
                                    {
                                        "name": "maven",
                                        "type": "directory",
                                        "children": [
                                            {
                                                "name": "org.example",
                                                "type": "directory",
                                                "children": [
                                                    {
                                                        "name": "jsp-demo",
                                                        "type": "directory",
                                                        "children": [
                                                            {
                                                                "name": "pom.properties",
                                                                "type": "file"
                                                            },
                                                            {
                                                                "name": "pom.xml",
                                                                "type": "file"
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "name": "MANIFEST.MF",
                                        "type": "file"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        """
        code = CodeData.objects(id=id, is_deleted=0).first()
        if not code:
            return JsonResponse(ERROR.NOT_FOUND_404)
        path = os.path.join(CODE_ROOT, id)

        if not os.path.exists(path):
            os.makedirs(path)
        if code.compiled and not any(os.scandir(path)):
            try:
                compiled_file_path = os.path.join(path, code.compiled.name)
                logger.info('compiled_file_path:{}'.format(compiled_file_path))
                code.compiled.download(compiled_file_path)
                extractall(compiled_file_path, path)
                os.remove(compiled_file_path)
            except Exception:
                traceback.print_exc()

        return JsonResponse(ok(self.path_to_dict(path)))


class CodeDataView(View):
    def get(self, request, id, path):
        """
        @api {GET} api/analysis/codesource/:id/:path 仓库文件详情
        @apiVersion 1.0.0
        @apiName Code Content
        @apiGroup Analysis
        @apiDescription 仓库文件详情

        @apiParam {String} id 仓库id
        @apiParam {String} path 文件路径

        @apiSuccessExample Response-Success:
        文件二进制内容

        """
        code = CodeData.objects(id=id, is_deleted=0).first()
        if not code:
            return JsonResponse(ERROR.NOT_FOUND_404)
        path = posixpath.normpath(os.path.join(id, path)).lstrip('/')
        fullpath = Path(safe_join(CODE_ROOT, path))
        if fullpath.is_dir():
            return directory_index(path, fullpath)
        if not fullpath.exists():
            raise Http404(_('“%(path)s” does not exist') % {'path': fullpath})
        # Respect the If-Modified-Since header.
        statobj = fullpath.stat()
        if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
                                  statobj.st_mtime, statobj.st_size):
            return HttpResponseNotModified()
        content_type, encoding = mimetypes.guess_type(str(fullpath))
        content_type = content_type or 'application/octet-stream'
        response = FileResponse(fullpath.open('rb'), content_type=content_type)
        response["Last-Modified"] = http_date(statobj.st_mtime)
        if encoding:
            response["Content-Encoding"] = encoding
        return response


class LocalCodeTaskView(View):
    def post(self, request, id):
        """
        @api {POST} api/analysis/file/:id/task 手动上传开始任务
        @apiVersion 1.0.0
        @apiName Local file task
        @apiGroup Analysis
        @apiDescription 手动上传开始任务

        @apiParam {String} id 文件id
        @apiParam {String} rule_template_id 规则模板id

        @apiParamExample {json} Request-Example:
        {
            "rule_template_id":"xxx",
        }
        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        file = FileStorage.objects(id=id, is_deleted=0).exclude('part_record').first()
        if not file:
            logger.info('no file found')
            return JsonResponse(ERROR.NOT_FOUND_404)
        code_data = post_codedata(file)

        rule_template_id = request.REQUEST.get('rule_template_id', None)
        if not rule_template_id:
            rule_template = RuleTemplate.objects(is_deleted=0, status=1, default=1).first()
        else:
            rule_template = RuleTemplate.objects(is_deleted=0, status=1, id=rule_template_id).first()

        if not rule_template:
            logger.info('no default rule template found')
            return JsonResponse(ERROR.NOT_FOUND_404)

        workflow = init_workflow(WorkflowType.compile_sa_ml.value, code_data, 'localhost', rule_template)
        handler = next_handler(workflow)
        if handler:
            handler.handle()
        return JsonResponse(ok())


class RuleTemplateListView(View):
    list_exclude = ()
    query_fields = 'id', 'name', 'engine', 'status', 'default'

    def get(self, request):
        """
        @api {GET} api/analysis/ruletemplate/list 规则模板列表
        @apiVersion 1.0.0
        @apiName RuleTemplate List
        @apiGroup Rule
        @apiDescription 规则模板列表

        @apiParam {Number}  [page=1] 当前页码
        @apiParam {Number}  [limit=25] 每页记录数
        @apiParam {String}  [name] 名称
        @apiParam {String}  [engine] 引擎
        @apiParam {Number}  [status] 状态，0停用，1启用
        @apiParam {Number}  [default] 是否默认，0不是，1是

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 25,
                "totalItems": 1,
                "totalPages": 1,
                "data": [
                    {
                        "name": "安全漏洞",
                        "is_deleted": 0,
                        "engine": "thusa",
                        "status": 1,
                        "default": 1,
                        "description": "webshell漏洞",
                        "rules": [
                            {
                                "name": "远端命令注入",
                                "cwe": "CWE-78",
                                "category": {
                                    "name": "安全功能",
                                    "is_deleted": 0,
                                    "description": "安全功能",
                                    "id": "610cde17eebaabab23aaa1a6"
                                },
                                "engine": "thusa",
                                "level": 1,
                                "is_deleted": 0,
                                "status": 1,
                                "default": 1,
                                "description": "该规则为远端命令注入，属于webshell中常见安全漏洞",
                                "date_created": "2021-07-21 18:04:08",
                                "id": "60c86a23a27aab4a6ab26330"
                            }
                        ],
                        "date_created": "2021-08-10 17:15:08",
                        "id": "60f7e37da5a802bd35915dd1"
                    }
                ]
            }
        }
        """

        page, per_page = request_page(request)
        query = clean(dict(request.GET.dict(), **request.REQUEST), self.__class__.query_fields)
        query['is_deleted'] = 0
        return MongoJsonResponse(
            ok(mongoengine_page(RuleTemplate, query, page, per_page, map=to_dict(['source', 'sink']))))

        # page, per_page = request_page(request)
        # query = clean(dict(request.GET.dict(), **request.REQUEST), self.__class__.query_fields)
        # pipeline = [RuleTemplate.pre_match(query), {'skip'}, {'limit'}, RuleTemplate.rule_lookup()]
        # logger.info(pipeline)
        # templates = pipeline_page(RuleTemplate, pipeline, page, per_page)
        # rule_category_map = RuleCategory.category_map()
        # rule_infos = [rule_info for template in templates.get('data', []) for rule_info in template.get('rules_info')]
        # for rule_info in rule_infos:
        #     rule_info['category_name'] = rule_category_map.get(str(rule_info.get('category', None)), 'unknown')
        # return MongoJsonResponse(ok(templates))


class RuleTemplateTreeListView(View):
    list_exclude = ()
    query_fields = 'id', 'name', 'engine', 'status', 'default'

    def get(self, request):
        """
        @api {GET} api/analysis/ruletemplate/list/tree 规则模板列表树
        @apiVersion 1.0.0
        @apiName RuleTemplate List Tree
        @apiGroup Rule
        @apiDescription 规则模板列表树

        @apiParam {Number}  [page=1] 当前页码
        @apiParam {Number}  [limit=25] 每页记录数
        @apiParam {String}  [name] 名称
        @apiParam {String}  [engine] 引擎
        @apiParam {Number}  [status] 状态，0停用，1启用
        @apiParam {Number}  [default] 是否默认，0不是，1是

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 25,
                "totalItems": 1,
                "totalPages": 1,
                "data": [
                    {
                        "name": "安全漏洞",
                        "is_deleted": 0,
                        "engine": "thusa",
                        "status": 1,
                        "default": 1,
                        "description": "webshell漏洞",
                        "rules": [
                            {
                                "name": "远端命令注入",
                                "cwe": "CWE-78",
                                "category": {
                                    "name": "安全功能",
                                    "is_deleted": 0,
                                    "description": "安全功能",
                                    "id": "610cde17eebaabab23aaa1a6"
                                },
                                "engine": "thusa",
                                "level": 1,
                                "is_deleted": 0,
                                "status": 1,
                                "default": 1,
                                "description": "该规则为远端命令注入，属于webshell中常见安全漏洞",
                                "date_created": "2021-07-21 18:04:08",
                                "id": "60c86a23a27aab4a6ab26330"
                            }
                        ],
                        "date_created": "2021-08-10 17:15:40",
                        "id": "60f7e37da5a802bd35915dd1",
                        "categorized_rules_info": {
                            "安全功能": [
                                {
                                    "name": "远端命令注入",
                                    "cwe": "CWE-78",
                                    "category": {
                                        "name": "安全功能",
                                        "is_deleted": 0,
                                        "description": "安全功能",
                                        "id": "610cde17eebaabab23aaa1a6"
                                    },
                                    "engine": "thusa",
                                    "level": 1,
                                    "is_deleted": 0,
                                    "status": 1,
                                    "default": 1,
                                    "description": "该规则为远端命令注入，属于webshell中常见安全漏洞",
                                    "date_created": "2021-07-21 18:04:08",
                                    "id": "60c86a23a27aab4a6ab26330"
                                }
                            ]
                        }
                    }
                ]
            }
        }
        """
        page, per_page = request_page(request)
        query = clean(dict(request.GET.dict(), **request.REQUEST), self.__class__.query_fields)
        query['is_deleted'] = 0
        templates = mongoengine_page(RuleTemplate, query, page, per_page, map=to_dict(['source', 'sink']))
        for template in templates.get('data', []):
            categorized = {k: list(v) for k, v in
                           groupby(template.get('rules'), key=lambda x: (x.get('category', {}).get('name', 'unknown')))}
            template['categorized_rules_info'] = categorized

        # page, per_page = request_page(request)
        # query = clean(dict(request.GET.dict(), **request.REQUEST), self.__class__.query_fields)
        # pipeline = [RuleTemplate.pre_match(query), {'skip'}, {'limit'}, RuleTemplate.rule_lookup()]
        # templates = pipeline_page(RuleTemplate, pipeline, page, per_page)
        # rule_category_map = RuleCategory.category_map()
        # rule_infos = [rule_info for template in templates.get('data', []) for rule_info in template.get('rules_info')]
        # for rule_info in rule_infos:
        #     rule_info['category_name'] = rule_category_map.get(str(rule_info.get('category', None)), 'unknown')
        # for template in templates.get('data', []):
        #     categorized = {k: list(v) for k, v in
        #                    groupby(template.get('rules_info'), key=lambda x: (x.get('category_name', 'unknown')))}
        #     template['categorized_rules_info'] = categorized
        return MongoJsonResponse(ok(templates))


class RuleTemplateView(View):
    def get(self, request, id):
        """
        @api {GET} api/analysis/ruletemplate/:id 规则模板详情
        @apiVersion 1.0.0
        @apiName RuleTemplate Detail
        @apiGroup Rule
        @apiDescription 规则模板详情

        @apiParam {String} id id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "_id": "60f7e37da5a802bd35915dd1",
                "name": "cwe",
                "is_deleted": 0,
                "engine": "thusa",
                "status": 1,
                "default": 1,
                "description": "asdfasdfasdf",
                "rules": [
                    "60c86a23a27aab4a6ab26330",
                    "60f5234b3a3cada021d3b722"
                ],
                "date_created": "2021-07-22 10:52:52"
            }
        }
        """
        template = RuleTemplate.objects(id=id, is_deleted=0).first()
        if template is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        return MongoJsonResponse(ok(to_dict()(template)))

    def post(self, request):
        """
        @api {POST} api/analysis/ruletemplate 创建规则模板
        @apiVersion 1.0.0
        @apiName RuleTemplate Create
        @apiGroup Rule
        @apiDescription 创建规则模板

        @apiParam {String} name 名称
        @apiParam {String} [engine=thusa] 引擎
        @apiParam {Number} [status=1] 状态 0停用，1启用
        @apiParam {Number} [default=0] 是否默认 0不是，1是
        @apiParam {String} description 描述
        @apiParam {List} rules 规则列表

        @apiParamExample {json} Request-Example:
        {
            "name":"cwe2",
            "engine":"thusa",
            "status":1,
            "default":1,
            "description":"asdfasdfasdf",
            "rules":[
                "60f6b2b8f44a9ed159d25c88",
                "60f6b2d3f44a9ed159d25c89"
            ]

        }

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "_id": "60f7e37da5a802bd35915dd1",
                "name": "cwe",
                "is_deleted": 0,
                "engine": "thusa",
                "status": 1,
                "default": 1,
                "description": "asdfasdfasdf",
                "rules": [
                    "60c86a23a27aab4a6ab26330",
                    "60f5234b3a3cada021d3b722"
                ],
                "date_created": "2021-07-22 10:52:52"
            }
        }
        """
        data_dict = clean(request.REQUEST, RuleTemplate.only_fields())
        rules = data_dict.get('rules', [])
        rules = list(filter(lambda x: x is not None and x != '',
                            map(lambda x: x if isinstance(x, str) else x.get('id', x.get('_id')), rules)))
        data_dict.update({'rules': rules})
        template = RuleTemplate.from_json(json.dumps(data_dict))
        template.save()
        return MongoJsonResponse(ok(template))

    def put(self, request, id):
        """
        @api {PUT} api/analysis/ruletemplate/:id 编辑规则模板
        @apiVersion 1.0.0
        @apiName RuleTemplate Update
        @apiGroup Rule
        @apiDescription 编辑规则模板

        @apiParam {String} [name] 名称
        @apiParam {String} [engine] 引擎
        @apiParam {Number} [status] 状态 0停用，1启用
        @apiParam {Number} [default] 是否默认 0不是，1是
        @apiParam {String} [description] 描述
        @apiParam {List} [rules] 规则列表

        @apiParamExample {json} Request-Example:
        {
            "name":"cwe2",
            "engine":"thusa",
            "status":1,
            "default":1,
            "description":"asdfasdfasdf",
            "rules":[
                "60f6b2b8f44a9ed159d25c88",
                "60f6b2d3f44a9ed159d25c89"
            ]

        }
        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
        }
        """
        doc = RuleTemplate.objects(id=id, is_deleted=0).first()
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)

        data_dict = clean(request.REQUEST, RuleTemplate.only_fields())
        data_json = json.dumps(data_dict)
        template = RuleTemplate.from_json(data_json)

        obj_list = dir(doc)
        for k in data_dict.keys():
            if k in obj_list:
                setattr(doc, k, getattr(template, k))
        doc.save()
        return MongoJsonResponse(ok())

    def delete(self, request, id):
        """
        @api {DELETE} api/analysis/ruletemplate/:id 删除规则集
        @apiVersion 1.0.0
        @apiName RuleTemplate Delete
        @apiGroup Rule
        @apiDescription 删除规则集

        @apiParam {String} id 规则集id

        @apiSuccessExample Response-Success:
        HTTP 1.1/ 200K
        {
            "code": 200,
            "msg": "ok"
        }
        """
        rule_template = RuleTemplate.objects(id=id, is_deleted=0).first()
        if rule_template is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        # check rule template
        if rule_template.default == 1:
            return JsonResponse(ERROR.DELETE_REFERENCE_ERROR('规则集“{}”为默认规则集，无法删除'.format(rule_template.name)))
        count = RuleTemplate.objects(is_deleted=0).count()
        if count == 1:
            return JsonResponse(ERROR.DELETE_REFERENCE_ERROR('规则集“{}”为最后一条规则集，无法删除'.format(rule_template.name)))

        RuleTemplate.objects(id=id).update_one(set__is_deleted=1)
        return MongoJsonResponse(ok())


class RuleCategoryListView(View):
    def get(self, request):
        """
        @api {GET} api/analysis/rulecategory/list 规则分类列表
        @apiVersion 1.0.0
        @apiName RuleCategory List
        @apiGroup Rule
        @apiDescription 规则分类列表

        @apiParam {Number}  [page=1] 当前页码
        @apiParam {Number}  [limit=25] 每页记录数

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 10,
                "totalItems": 4,
                "totalPages": 1,
                "data": [
                    {
                        "_id": "610cde17eebaabab23aaa1a6",
                        "name": "安全功能",
                        "is_deleted": 0,
                        "description": "安全功能"
                    },
                    {
                        "_id": "610cde4ceebaabab23aaa1a8",
                        "name": "代码质量",
                        "is_deleted": 0,
                        "description": "代码质量"
                    },
                    {
                        "_id": "610cde53eebaabab23aaa1a9",
                        "name": "Api滥用",
                        "is_deleted": 0,
                        "description": "Api滥用"
                    },
                    {
                        "_id": "610cde78eebaabab23aaa1aa",
                        "name": "错误",
                        "is_deleted": 0,
                        "description": "错误"
                    }
                ]
            }
        }
        """
        page, per_page = page_get(request.GET)
        query = {'is_deleted': 0}
        return MongoJsonResponse(ok(mongoengine_page(RuleCategory, query, page, per_page)))


class RuleCategoryView(View):
    def post(self, request):
        """
        @api {POST} api/analysis/ruletecategory 创建规则分类
        @apiVersion 1.0.0
        @apiName RuleCategory Create
        @apiGroup Rule
        @apiDescription 创建规则分类

        @apiParam {String} name 名称
        @apiParam {String} [description] 描述

        @apiSuccessExample Response-Success:
         {
            "code": 200,
            "msg": "ok",
            "data": {
                "_id": "610cde53eebaabab23aaa1a9",
                "name": "Api滥用",
                "is_deleted": 0,
                "description": "Api滥用"
            }
        }
        """
        data_dict = clean(request.REQUEST, RuleCategory.only_fields())
        category = RuleCategory.from_json(json.dumps(data_dict))
        category.save()
        return MongoJsonResponse(ok(category))

    def put(self, request, id):
        """
        @api {PUT} api/analysis/ruletecategory/:id 编辑规则分类
        @apiVersion 1.0.0
        @apiName RuleCategory Update
        @apiGroup Rule
        @apiDescription 编辑规则分类

        @apiParam {String} id 规则分类id
        @apiParam {String} [name] 名称
        @apiParam {String} [description] 描述

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        doc = RuleCategory.objects(id=id, is_deleted=0).first()
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)

        data_dict = clean(request.REQUEST, RuleCategory.only_fields())
        data_json = json.dumps(data_dict)
        category = RuleCategory.from_json(data_json)

        obj_list = dir(doc)
        for k in data_dict.keys():
            if k in obj_list:
                setattr(doc, k, getattr(category, k))
        doc.save()
        return MongoJsonResponse(ok())

    def delete(self, request, id):
        doc = RuleCategory.objects(id=id, is_deleted=0).first()
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        rule = Rule.objects(category=id, is_deleted=0).first()
        if rule:
            return JsonResponse(ERROR.DELETE_REFERENCE_ERROR('作为规则“{}”的类别，无法删除'.format(rule.name)))
        RuleCategory.objects(id=id).update_one(set__is_deleted=1)
        return JsonResponse(ok())


class AuditView(View):
    def put(self, request, tid, id):
        """
        @api {PUT} api/analysis/task/:tid/detectedresult/:id/audit 审计缺陷
        @apiVersion 1.0.0
        @apiName Audit weakness
        @apiGroup Analysis
        @apiDescription 审计缺陷

        @apiParam {String} tid 任务id
        @apiParam {String} id detectedresult id
        @apiParam {Object} audit 审计信息

        @apiParamExample {json} Request-Example:
        {
            "audit": {
                "handle_type": 3,# 1.确认，2.误报，3.标记为不会修复
                "audit_level": 2,# 1.强制，2.推荐
                "memo": "asdfasdfaasdfasdfasdf"
            }
        }

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        detected_result = DetectedResult.objects(id=id).first()
        if not detected_result:
            return JsonResponse(ERROR.NOT_FOUND_404)

        data_dict = clean(request.REQUEST, DetectedResult.only_fields())
        data_json = json.dumps(data_dict)
        audit = DetectedResult.from_json(data_json)
        if not audit.audit or not audit.audit.handle_type:
            return JsonResponse(ERROR.HANDLE_TYPE_EMPTY)

        obj_list = dir(detected_result)
        for k in data_dict.keys():
            if k in obj_list:
                setattr(detected_result, k, getattr(audit, k))
        detected_result.save()

        audited = TaskAuditStatistic.objects(task_id=tid, detected_result_id=id).first()
        if not audited:
            TaskAuditStatistic(task_id=tid, detected_result_id=id).save()
        audited_count = TaskAuditStatistic.objects(task_id=tid).count()
        Task.objects(id=tid).update_one(set__audit_count=audited_count)
        return MongoJsonResponse(ok())


class ProjectListView(View):
    query_fields = ('monitor', 'name', 'version')

    def get(self, request):
        """
        @api {GET} api/analysis/project/list 项目列表
        @apiVersion 1.0.0
        @apiName Project List
        @apiGroup Analysis
        @apiDescription 项目列表

        @apiParam {Number} [page] 页码，默认1
        @apiParam {Number} [limit] 每页条数，默认25
        @apiParam {String} [monitor] 主机id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 25,
                "totalItems": 2,
                "totalPages": 1,
                "data": [
                    {
                        "_id": {
                            "monitor": "60f66fc45c900a3bd0a57a4f",
                            "monitor_path": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo"
                        },
                        "monitor_path": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo", //监控地址
                        "name": "jsp-demo", //项目名称
                        "monitor_id": "60f66fc45c900a3bd0a57a4f",
                        "history_projects": [ // 项目抓取历史列表
                            {
                                "_id": "612c762c997b9baccc43f26b",
                                "name": "jsp-demo", // 项目名称
                                "version": "1630303788324", // 版本号
                                "date_created": "2021-08-30 14:09:48" // 创建日期
                            }
                        ],
                        "monitor": { // 主机信息
                            "_id": "60f66fc45c900a3bd0a57a4f", // 主机id
                            "name": "LG Electronics17Z90N-V.AA76C (version: 0.1)" //主机名称
                        }
                    },
                    {
                        "_id": {
                            "monitor": "60f66fc45c900a3bd0a57a4f",
                            "monitor_path": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo1"
                        },
                        "monitor_path": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo1",
                        "name": "jsp-demo1",
                        "monitor_id": "60f66fc45c900a3bd0a57a4f",
                        "history_projects": [
                            {
                                "_id": "612c74f20d1da3f38317de33",
                                "name": "jsp-demo1",
                                "version": "1630303474455",
                                "date_created": "2021-08-30 14:04:34"
                            },
                            {
                                "_id": "612c75a6997b9baccc43f256",
                                "name": "jsp-demo1",
                                "version": "1630303654418",
                                "date_created": "2021-08-30 14:07:34"
                            }
                        ],
                        "monitor": {
                            "_id": "60f66fc45c900a3bd0a57a4f",
                            "name": "LG Electronics17Z90N-V.AA76C (version: 0.1)"
                        }
                    }
                ]
            }
        }
        """
        cp, per_page = page_get(request.GET)
        query = clean(dict(request.GET.dict(), **request.REQUEST), self.__class__.query_fields)
        query['is_deleted'] = 0
        if query.get('monitor', None):
            query['monitor'] = ObjectId(query.get('monitor'))

        lookup = {"$lookup": {
            "from": "online_client",
            "let": {"id": "$monitor_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$id"]}}},
                {"$project": {"name": 1}}
            ],
            "as": "monitor"
        }}
        monitor = {'$arrayElemAt': ["$monitor", 0]}
        add_fields = {'$addFields': {'monitor': monitor}}
        pipeline = [{'$match': query},
                    {'$project': {
                        'name': 1,
                        'monitor': 1,
                        'monitor_path': 1,
                        'version': 1,
                        'date_created': 1,
                    }},
                    {
                        '$group': {
                            '_id': {'monitor': '$monitor', 'monitor_path': '$monitor_path'},
                            'monitor_path': {'$first': '$monitor_path'},
                            'name': {'$first': '$name'},
                            'monitor_id': {'$first': '$monitor'},
                            'history_projects': {'$push': {'_id': "$_id", 'name': "$name", "version": "$version",
                                                           'date_created': '$date_created'}}
                        }
                    },
                    lookup, add_fields]

        return page(list(MonitorProject.objects.aggregate(*pipeline)), cp, per_page)


class ProjectDetailView(View):
    def get(self, request, id):
        """
        @api {GET} api/analysis/project/:id 项目详情
        @apiVersion 1.0.0
        @apiName Project Detail
        @apiGroup Analysis
        @apiDescription 项目详情

        @apiParam {String} id 项目id

        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "name": "jsp-demo", //项目名称
                "monitor_id": null,
                "monitor_path": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo", // 监控路径
                "include": [],
                "exclude": [],
                "is_deleted": 0,
                "version": "1630303788324", // 版本号
                "change_log": [],
                "files": [],
                "date_created": "2021-08-30 14:09:48", // 创建日期
                "_id": "612c762c997b9baccc43f26b",
                "id": "612c762c997b9baccc43f26b",
                "code_data": { // 项目代码（即代码仓库，其id为代码仓库id）
                    "source_name": "jsp-demo.zip",
                    "is_deleted": 0,
                    "date_created": "2021-08-30 14:10:02",
                    "_id": "612c763a997b9baccc43f26d",
                    "id": "612c763a997b9baccc43f26d"
                },
                "monitor": { // 所属主机信息
                    "_id": "60f66fc45c900a3bd0a57a4f",
                    "name": "LG Electronics17Z90N-V.AA76C (version: 0.1)"
                },
                "tasks": [ // 项目历史任务（与任务列表相同）
                    {
                        "_id": "612c7afdd0ca64454976878a",
                        "trigger_client": "localhost",
                        "target_object_key": "codedb/bea1d0fbbd3fed7cb489c1ec4be2c37c/jsp-demo.zip",
                        "target_object_name": "jsp-demo.zip",
                        "project": "612c762c997b9baccc43f26b",
                        "rule_snapshot": [],
                        "is_deleted": 0,
                        "type": 3,
                        "status": 2,
                        "progress": 100,
                        "start": "2021-08-30 14:30:21",
                        "end": "2021-08-30 14:30:30",
                        "result": [],
                        "weakness_count": 1,
                        "audit_count": 0,
                        "ml_status": 1,
                        "ml_progress": 0,
                        "ml_start": "2021-08-30 14:30:21",
                        "date_created": "2021-08-30 14:30:21"
                    },
                    {
                        "_id": "612c763a997b9baccc43f26e",
                        "trigger_client": "LG Electronics17Z90N-V.AA76C (version: 0.1)",
                        "target_object_key": "codedb/bea1d0fbbd3fed7cb489c1ec4be2c37c/jsp-demo.zip",
                        "target_object_name": "jsp-demo.zip",
                        "project": "612c762c997b9baccc43f26b",
                        "rule_snapshot": [],
                        "is_deleted": 0,
                        "type": 3,
                        "status": 2,
                        "progress": 100,
                        "start": "2021-08-30 14:10:02",
                        "end": "2021-08-30 14:10:31",
                        "result": [],
                        "weakness_count": 1,
                        "audit_count": 0,
                        "ml_status": 2,
                        "ml_progress": 100,
                        "ml_start": "2021-08-30 14:10:15",
                        "ml_end": "2021-08-30 14:10:36",
                        "date_created": "2021-08-30 14:10:02"
                    }
                ]
            }
        }
        """
        project = MonitorProject.objects(id=id, is_deleted=0).exclude('files', 'change_log').first()
        if not project:
            return JsonResponse(ERROR.NOT_FOUND_404)

        ret = to_dict(exclude=['code_data', 'monitor'])(project)
        if project.code_data:
            ret['code_data'] = to_dict(['source', 'compiled', 'project'])(project.code_data)
        if project.monitor:
            ret['monitor'] = {'_id': str(project.monitor.id), 'name': project.monitor.name}
        tasks = Task.objects(project=project, is_deleted=0).exclude('result', 'ml_result', 'rule_snapshot',
                                                                    'rule_template_snapshot', 'code_data',
                                                                    'trigger_monitor').order_by('-date_created')
        ret['tasks'] = list(tasks)
        return MongoJsonResponse(ok(ret))


class ProjectTaskView(View):
    def post(self, request, id):
        """
        @api {POST} api/analysis/project/:id/task 手动执行项目检测
        @apiVersion 1.0.0
        @apiName project task
        @apiGroup Analysis
        @apiDescription 手动执行项目检测

        @apiParam {String} id 项目id
        @apiParam {String} rule_template_id 规则模板id
        @apiParam {Integer} [timeout] 最大等待时间 1-30 单位分钟
        @apiParam {Integer} [max_memory] 最大内存 1-16 单位g

        @apiParamExample {json} Request-Example:
        {
            "rule_template_id":"xxx",
        }
        @apiSuccessExample Response-Success:
        {
            "code": 200,
            "msg": "ok"
        }
        """
        project = MonitorProject.objects(id=id, is_deleted=0).first()
        if project is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        if project.code_data is None:
            return JsonResponse(ERROR.PROJECT_CODE_DATA_EMPTY)
        rule_template_id = request.REQUEST.get('rule_template_id', None)
        if not rule_template_id:
            rule_template = RuleTemplate.objects(is_deleted=0, status=1, default=1).first()
        else:
            rule_template = RuleTemplate.objects(is_deleted=0, status=1, id=rule_template_id).first()
        if not rule_template:
            logger.info('no default rule template found')
            return JsonResponse(ERROR.NOT_FOUND_404)
        timeout = int(request.REQUEST.get('timeout', 20))
        max_memory = int(request.REQUEST.get('max_memory', 6))
        workflow = init_workflow(
            WorkflowType.sa_ml.value if project.code_data.compiled else WorkflowType.compile_sa_ml.value,
            project.code_data, 'localhost', rule_template, project, project.monitor)

        handler = next_handler(workflow, timeout, max_memory)
        if handler:
            handler.handle()
        return JsonResponse(ok())
