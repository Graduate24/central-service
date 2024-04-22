# Create your models here.
from itertools import groupby

from bson import ObjectId
from django.utils import timezone
from mongoengine import *
from mongoengine_pagination import DocumentPro

from attachment.models import FileStorage
from ws.models import OnlineClient


class RuleCategory(DocumentPro):
    name = StringField(max_length=200, required=True)
    is_deleted = IntField(required=True, default=0)
    description = StringField()

    @staticmethod
    def category_map():
        rule_category = list(RuleCategory.objects(is_deleted=0))
        return {k: list(v)[0].name for k, v in groupby(rule_category, key=lambda x: str(x.id))}

    @staticmethod
    def only_fields():
        return 'name', 'description'


class Rule(DocumentPro):
    name = StringField(required=True)
    cwe = StringField()
    category = ReferenceField(RuleCategory)
    engine = StringField(default='thusa')
    # 1, 低，2,中，3,高
    level = IntField(default=1)
    source = ListField(StringField(), default=[])
    sink = ListField(StringField(), default=[])
    is_deleted = IntField(required=True, default=0)
    # 0, 停用 1，启用
    status = IntField(required=True, default=1)
    default = IntField(required=True, default=0)
    description = StringField()
    date_created = DateTimeField(required=True, default=timezone.now)

    @staticmethod
    def only_fields():
        return 'name', 'cwe', 'category', 'engine', 'level', 'source', 'sink', 'status', 'default', 'description'


class RuleTemplate(DocumentPro):
    name = StringField(required=True)
    is_deleted = IntField(required=True, default=0)
    engine = StringField(default='thusa')
    # 0, 停用 1，启用
    status = IntField(required=True, default=1)
    default = IntField(required=True, default=0)
    description = StringField()
    rules = ListField(ReferenceField(Rule))
    date_created = DateTimeField(required=True, default=timezone.now)

    @staticmethod
    def only_fields():
        return 'name', 'engine', 'status', 'default', 'description', 'rules'

    @staticmethod
    def rule_lookup():
        return {"$lookup": {
            "from": "rule",
            "as": "rules_info",
            "let": {"pid": "$rules"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$in": ["$_id", "$$pid"]},
                    {"$eq": ["$is_deleted", 0]},
                    {"$eq": ["$status", 1]}]
                }}},
                {"$project": {"name": 1, "category": 1}}
            ]
        }}

    @staticmethod
    def pre_match(query_dict):
        match = {'is_deleted': 0}
        if query_dict.get('name', None):
            match['name'] = {'$regex': '^' + query_dict.get('name')}
        if query_dict.get('status', None):
            match['status'] = int(query_dict.get('status'))
        if query_dict.get('default', None):
            match['default'] = int(query_dict.get('default'))
        if query_dict.get('engine', None):
            match['engine'] = query_dict.get('engine')
        time_query = {}
        if query_dict.get('date_created_from', None):
            from datetime import datetime
            start_from = datetime.strptime(query_dict.get('date_created_from'), '%Y-%m-%d %H:%M:%S')
            time_query['$gte'] = start_from
        if query_dict.get('date_created_to', None):
            from datetime import datetime
            start_to = datetime.strptime(query_dict.get('date_created_to'), '%Y-%m-%d %H:%M:%S')
            time_query['$lte'] = start_to
        if time_query:
            match['last_update'] = time_query
        if query_dict.get('id', None):
            match['_id'] = ObjectId(query_dict.get('id'))
        return {'$match': match}


class RuleSnapshot(EmbeddedDocument):
    rule_id = StringField()
    name = StringField(required=True)
    cwe = StringField()
    # 1, 低，2,中，3,高
    category = StringField()
    level = IntField(default=1)
    source = ListField(StringField(), default=[])
    sink = ListField(StringField(), default=[])


class ChangeLog(DocumentPro):
    path = StringField(required=True)
    event = StringField(required=True)
    md5 = StringField()
    file = ReferenceField(FileStorage)
    is_deleted = IntField(required=True, default=0)
    date_created = DateTimeField(required=True, default=timezone.now)


class CodeData(DocumentPro):
    source_name = StringField()
    source = ReferenceField(FileStorage, required=True)
    compiled = ReferenceField(FileStorage)
    project = StringField()
    is_deleted = IntField(required=True, default=0)
    date_created = DateTimeField(required=True, default=timezone.now)

    @staticmethod
    def only_fields():
        return 'source', 'compiled', 'source_name'


class MonitorProject(DocumentPro):
    name = StringField()
    monitor_id = StringField()
    monitor = ReferenceField(OnlineClient)
    monitor_path = StringField()
    include = ListField(StringField())
    exclude = ListField(StringField())
    is_deleted = IntField(required=True, default=0)
    version = StringField(required=True)
    change_log = ListField(ReferenceField(ChangeLog), default=[])
    files = ListField(ReferenceField(FileStorage), default=[])
    code_data = ReferenceField(CodeData)
    date_created = DateTimeField(required=True, default=timezone.now)


class RuleTemplateSnapshot(EmbeddedDocument):
    rule_template_id = StringField()
    rule_template_name = StringField()
    rules = EmbeddedDocumentListField(RuleSnapshot)


class PathUnit(EmbeddedDocument):
    file = StringField()
    function = StringField()
    jimpleStmt = StringField()
    javaStmt = StringField()
    jspStmt = StringField()
    line = IntField()
    jspLine = IntField()
    javaClass = StringField()
    jspFile = StringField()


class Audit(EmbeddedDocument):
    # 1.确认，2.误报，3.标记为不会修复
    handle_type = IntField()
    # 1.强制，2.推荐
    audit_level = IntField()
    memo = StringField()
    date_created = DateTimeField(default=timezone.now)


class DetectedResult(DocumentPro):
    sourceSig = StringField()
    sinkSig = StringField()
    path = EmbeddedDocumentListField(PathUnit)
    audit = EmbeddedDocumentField(Audit)
    facade = StringField()
    pathStm = ListField(StringField())

    # date_created = DateTimeField(default=timezone.now)

    @staticmethod
    def only_fields():
        return 'audit', 'facade', 'sourceSig', 'sinkSig'


class SaResult(DocumentPro):
    taskId = StringField()
    ruleId = StringField()
    ruleName = StringField()
    ruleCwe = StringField()
    ruleCategory = StringField()
    ruleLevel = IntField()
    is_deleted = IntField(required=True, default=0)
    detectedResults = ListField(ReferenceField(DetectedResult))


class Task(DocumentPro):
    trigger_client = StringField()
    # compiled code objectKey
    target_object_key = StringField()
    # original source name
    target_object_name = StringField()
    code_data = ReferenceField(CodeData)
    project = ReferenceField(MonitorProject)
    trigger_monitor = ReferenceField(OnlineClient)
    rule_snapshot = EmbeddedDocumentListField(RuleSnapshot)
    rule_template_snapshot = EmbeddedDocumentField(RuleTemplateSnapshot)
    is_deleted = IntField(required=True, default=0)
    # sa = 1, ml = 2, sa_ml = 3
    type = IntField(required=True, default=3)
    # 1，进行中，2,成功，3,异常
    # sa
    status = IntField(required=True, default=1)
    progress = IntField(0, 100, default=0)
    start = DateTimeField()
    end = DateTimeField()
    result = ListField(ReferenceField(SaResult))
    weakness_count = IntField(default=0)
    audit_count = IntField(default=0)
    # ml
    # 1，进行中，2,成功，3,异常
    ml_status = IntField(required=True, default=1)
    ml_progress = IntField(0, 100, default=0)
    ml_start = DateTimeField()
    ml_end = DateTimeField()
    ml_result = DynamicField()
    summary_result = DynamicField()
    date_created = DateTimeField(required=True, default=timezone.now)

    @staticmethod
    def only_fields():
        return 'trigger_client', 'target_object_key', 'rule', 'source', 'sink', 'status', 'progress', 'result', \
               'start', 'end', 'ml_status', 'ml_progress', 'ml_start', 'ml_end', 'ml_result', 'summary_result'


class Workflow(DocumentPro):
    task = ReferenceField(Task)
    # 1,仅编译；2,编译，并静态分析，3,编译，静态分析，机器学习分析。4,静态分析已有程序；
    # 5,机器学习分析已有程序；6,静态分析，机器学习分析已有程序
    type = IntField(required=True, default=3)
    # 0,进行中；1,完成,2,异常终止
    status = IntField(required=True, default=0)
    # 步骤数量
    steps = IntField(required=True, default=0)
    # 当前步骤
    progress = IntField(required=True, default=0)
    # 代码
    code_data = ReferenceField(CodeData)
    # 检测模板
    rule_template = ReferenceField(RuleTemplate)

    trigger_client = StringField()
    is_deleted = IntField(required=True, default=0)
    timeline = ListField(DateTimeField(), default=[])
    date_created = DateTimeField(required=True, default=timezone.now)

    def get_steps(self):
        if self.type == 1:
            return 1
        elif self.type == 2:
            return 2
        elif self.type == 3:
            return 2
        elif self.type == 4:
            return 1
        elif self.type == 5:
            return 1
        elif self.type == 6:
            return 1

    def fill_steps(self):
        self.steps = self.get_steps()


class TaskAuditStatistic(DocumentPro):
    task_id = StringField(required=True, unique_with='detected_result_id')
    detected_result_id = StringField(required=True)
