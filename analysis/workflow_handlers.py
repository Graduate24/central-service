import ntpath
import traceback
from datetime import datetime
from enum import Enum

from analysis.models import Workflow, CodeData, RuleSnapshot, Task, RuleTemplateSnapshot, MonitorProject
from attachment.models import FileStorage, FileMeta
from mq.tasks import compile_task, analysis_task, ml_analysis_task
from utils.log import logger
from utils.mongo_json import to_dict
from ws.models import OnlineClient


class WorkflowType(Enum):
    # 为序列值指定value值
    # 1,仅编译；2,编译，并静态分析，3,编译，静态分析，机器学习分析。4,静态分析已有程序；
    # 5,机器学习分析已有程序；6,静态分析，机器学习分析已有程序
    compile = 1
    compile_sa = 2
    compile_sa_ml = 3
    sa = 4
    ml = 5
    sa_ml = 6


class CompileHandler:
    def __init__(self, workflow, timeout=20, max_memory=6):
        self.workflow = workflow
        self.name = 'compile handler'
        self.timeout = timeout
        self.max_memory = max_memory

    def handle(self):
        logger.info(self.name)
        # send compile task
        fs = self.workflow.code_data.source
        url = fs.preview()
        data = {'workflowId': str(self.workflow.id), 'source': url, 'filename': fs.name}
        # analysis_task.delay(data)
        compile_task.delay(data)


class AnalysisHandler:
    def __init__(self, workflow, timeout=20, max_memory=6):
        self.workflow = workflow
        self.name = 'analysis handler'
        self.timeout = timeout
        self.max_memory = max_memory

    def handle(self):
        logger.info(self.name)
        compiled_code = self.workflow.code_data.compiled
        # start task.
        rule_template = self.workflow.rule_template
        task = self.workflow.task

        rule = rule_template.rules
        if not rule or len(list(rule)) == 0:
            logger.info('No default rule found. Abort analysis.')
            task.progress = 100
            task.status = 3
            self.workflow.status = 2
            task.save()
            self.workflow.save()
            return

        rules = [{'id': str(r.id), 'name': r.name, 'cwe': r.cwe,
                  'category': r.category.name, 'level': r.level, 'source': r.source, 'sink': r.sink} for r in rule]

        rule_snapshot = [
            RuleSnapshot(rule_id=str(r.id), name=r.name, cwe=r.cwe, category=r.category.name, level=r.level,
                         source=r.source,
                         sink=r.sink) for r in rule]
        rule_template_snapshot = RuleTemplateSnapshot(rule_template_id=str(rule_template.id),
                                                      rule_template_name=rule_template.name,
                                                      rules=rule_snapshot)
        task.code_data = self.workflow.code_data
        task.target_object_key = compiled_code.object_key
        task.rule_template_snapshot = rule_template_snapshot
        if self.workflow.type in [WorkflowType.compile_sa.value,
                                  WorkflowType.sa.value]:
            task.type = 1
        elif self.workflow.type in [WorkflowType.ml.value]:
            task.type = 2
            task.ml_start = datetime.now()
        elif self.workflow.type in [WorkflowType.compile_sa_ml.value, WorkflowType.sa_ml.value]:
            task.type = 3
            task.ml_start = datetime.now()

        task.save()
        url = compiled_code.preview()

        data = {'workflowId': str(self.workflow.id), 'taskId': str(task.id), 'source': url,
                'filename': compiled_code.name, 'rules': rules, 'maxMemory': self.max_memory, 'timeout': self.timeout}

        if self.workflow.type in [WorkflowType.compile_sa_ml.value,
                                  WorkflowType.compile_sa.value,
                                  WorkflowType.sa.value,
                                  WorkflowType.sa_ml.value]:
            logger.info('-----------------send sa task')
            analysis_task.delay(data)
        if self.workflow.type in [WorkflowType.compile_sa_ml.value,
                                  WorkflowType.ml.value,
                                  WorkflowType.sa_ml.value]:
            logger.info('=================send ml task')
            ml_analysis_task.delay(data)


class MergeResult:
    def __init__(self, cwe, name, facade, cross_file, line_number, from_sa=False, from_ml=False):
        self.cwe = cwe
        self.name = name
        self.facade = facade
        self.cross_file = cross_file
        self.line_number = line_number
        # 0 ERROR; 1 WARNING; -1 None
        self.level = None
        self.ml_probability = None
        self.from_sa = from_sa
        self.from_ml = from_ml
        self.threshold_low = None
        self.threshold_high = None

    def __str__(self):
        return '{' + f'"cwe" :{self.cwe},"name":{self.name},"facade":{self.facade},"cross_file":{self.cross_file},' \
                     f'"line_number":{self.line_number},"level":{self.level},"ml_probability":{self.ml_probability},' \
                     f'"from_sa":{self.from_sa},"from_ml":{self.from_ml}"' + '}'

    def apply_rule(self, threshold_low=0.05, threshold_high=0.95):
        """
        +-----------------------------------------------------------------------------+
        |风险等级	     |         输入和引擎返回结果                                     |
        +-----------------------------------------------------------------------------+
        |ERROR	         |  a)静态分析引擎检测出跨文件漏洞。                                |
        |                |  b)静态分析引擎检测出单文件漏洞，机器学习引擎无结果(C=NULL)或结果
        |                |  不是高可信度判定为无漏洞（判定方法为：C>=Low）                      |
        |                |  c)不可编译到字节码的JSP文件，机器学习引擎结果为高可信度             |
        |                |                    （判定方法为：C>High）                     |
        +-----------------------------------------------------------------------------+
        |WARNING	     | a）单文件，静态分析引擎未检测出漏洞，机器学习引擎高可信度判定为有漏洞      |
        |                |                   （判定方法为：C>High）。                       |
        |                | b）单文件，静态分析引擎检测出漏洞，机器学习引擎高可信度判定为无漏洞（C<Low)|
        +------------------------------------------------------------------------------+
        :param threshold_low:
        :param threshold_high:
        :return:
        """
        self.threshold_low = threshold_low
        self.threshold_high = threshold_high
        # 静态分析引擎检测出跨文件漏洞
        if self.from_sa and self.cross_file:
            self.level = 0
            return
        # 静态分析引擎检测出单文件漏洞，机器学习引擎无结果(C=NULL)
        if self.from_sa and not self.from_ml:
            self.level = 0
            return
        # 静态分析引擎检测出单文件漏洞，机器学习引擎结果高可信度判定为无漏洞（判定方法为：C>=Low）
        elif self.from_sa and not self.cross_file and self.from_ml and self.ml_probability >= self.threshold_low:
            self.level = 0
            return
        # 不可编译到字节码的JSP文件，机器学习引擎结果为高可信度 （判定方法为：C>High）
        elif not self.from_sa and self.from_ml and self.ml_probability >= self.threshold_high:
            # TODO
            self.level = 1
            return
        # 单文件，静态分析引擎未检测出漏洞，机器学习引擎高可信度判定为有漏洞（判定方法为：C>High）
        elif not self.from_sa and self.from_ml and self.ml_probability >= self.threshold_high:
            self.level = 1
            return
        # 单文件，静态分析引擎检测出漏洞，机器学习引擎高可信度判定为无漏洞（C<Low)
        elif self.from_sa and not self.cross_file and self.from_ml and self.ml_probability < self.threshold_low:
            self.level = 1
            return
        else:
            self.level = -1


handlers = [CompileHandler, AnalysisHandler]
analysers = [AnalysisHandler]


def next_handler(workflow, timeout=20, max_memory=6):
    if workflow.type in [WorkflowType.compile.value, WorkflowType.compile_sa.value, WorkflowType.compile_sa_ml.value]:
        if workflow.progress < workflow.steps:
            return handlers[workflow.progress](workflow, timeout, max_memory)
    elif workflow.type in [WorkflowType.sa.value, WorkflowType.sa_ml.value]:
        if workflow.progress < workflow.steps:
            return analysers[workflow.progress](workflow, timeout, max_memory)
    elif workflow.type == WorkflowType.ml.value:
        if workflow.progress < workflow.steps:
            return analysers[workflow.progress](workflow, timeout, max_memory)
    else:
        return None


def file_archive(payload):
    watch_path = payload.get('watchPath')
    file_name = ntpath.basename(watch_path)
    machine_code = payload.get('machine_code')
    uploader = OnlineClient.objects(machine_code=machine_code).exclude('client_info').first()
    fs = FileStorage(name=file_name, size=payload.get('size'), md5=payload.get('md5'),
                     object_key=payload.get('objectKey'), status=0, meta_info=FileMeta(), uploader=uploader)
    fs.save()

    # TODO
    # mp = MonitorProject.objects(is_deleted=0, monitor_path=payload.get('monitorDir'), monitor=uploader).first()
    # if not mp:
    #     pf = ProjectFile(name=file_name, path=watch_path, file=fs, monitor=uploader, md5=payload.get('md5'),
    #                      parent=os.path.dirname(watch_path))
    #     pf.save()
    #     mp = MonitorProject.objects(monitor_path=payload.get('monitorDir'), monitor=uploader, files=[pf])
    #     mp.save()
    # else:
    #     pf = ProjectFile.objects(monitor=uploader, path=watch_path).first()
    #     if not pf:
    #         pf = ProjectFile(name=file_name, path=watch_path, file=fs, monitor=uploader, md5=payload.get('md5'),
    #                          parent=os.path.dirname(watch_path))
    #         pf.save()
    #         mp.update(add_to_set__files=pf)
    #     elif pf.md5 != payload.get('md5'):
    #         mp.update_one(pull__files=pf)
    #         pf.update(is_latest=0)
    #
    #         pf = ProjectFile(name=file_name, path=watch_path, file=fs, monitor=uploader, md5=payload.get('md5'),
    #                          parent=os.path.dirname(watch_path))
    #         pf.save()
    #         mp.update_one(add_to_set__files=pf)
    #     else:
    #         pass

    return fs


def post_codedata(fs, project=None):
    code_data = CodeData(source=fs, source_name=fs.name, project=str(project.id) if project else None)
    code_data.save()
    if project:
        MonitorProject.objects(id=project.id).update_one(set__code_data=code_data)
    return code_data


def init_workflow(type_code, code, trigger_client, rule_template=None, project=None, monitor=None):
    task = Task(trigger_client=trigger_client, code_data=code, target_object_name=code.source.name,
                start=datetime.now(), project=project, trigger_monitor=monitor)
    task.save()
    workflow = Workflow(type=type_code, task=task, code_data=code, trigger_client=trigger_client,
                        rule_template=rule_template)
    workflow.fill_steps()
    workflow.save()
    return workflow


def check_cross_file(target, path):
    for p in path:
        if target == p['file']:
            return True
    return False


def merge_result(task_id):
    """
    #### 返回格式
    以json格式返回，如对于一个输入机器学习的文件夹A， 里面有B.Java C.java 文件
    机器学习分析结果返回格式如下:
    {
        'B.Java':{
            'status': 200,
            'Rce': 90%,
            'Sqli': 80%,
            'PathTraver': 60%
        },
        'C.java':{
            'status': 200,
            'Rce': 90%,
            'Sqli': 80%,
            'PathTraver': 60%
        }
    }
    [
      {
        "file": "/home/model-server/tmp/tmp_vl5fofl/jsp-demo2/jsp-demo2/WEB-INF/classes/org/apache/jsp/welcome_jsp.java",
        "label": "99.9986%"
      },
      {
        "file": "/home/model-server/tmp/tmp_vl5fofl/jsp-demo2/jsp-demo2/WEB-INF/classes/org/apache/jsp/login_jsp.java",
        "label": "6.2011%"
      }
    ]
    其中status表示机器学习针对该文件的处理状态(200代表处理成功，)
    Rce，Sqli,PathTraver 键值对分别对应目标文件存在命令执行、sql注入、目录穿透型漏洞的概率，
    当然如果目标存在某种漏洞的概率不大（根据阈值判定）的话，该键值对不一定要存在，
    比如对于B.java文件可能是个正常文件，并且机器学习引擎在处理其时发生程序意外错误，那么返回结果应如下：
    {
        'B.Java':{
            'status': 500
        },
        'C.java':{
            'status': 200,
            'Rce': 90%,
            'Sqli': 80%,
            'PathTraver': 60%
        }
    }
    Q:
    1. 返回数据key是文件名还是文件路径？
    2. 如果是jsp文件，key是原始的jsp,还是编译后的java文件？
    A:
    1. 文件路径
    2. 如果是jsp文件为编译后的java文件名
    ----------------

    静态分析引擎的精度更高，因此在集成方案中，优先采信静态分析引擎的检测结果，以机器学习作为辅助：
    如果机器学习检测结果极高概率与静态分析引擎有冲突时，下调静态分析结果的风险等级。
    此外，出于缺乏依赖等因素，一部分JSP文件无法编译到字节码。这一部分代码文件仅能由机器学习引擎进行检测，
    如果较高概率被判定为有漏洞则也视为ERROR级别风险。
    +-----------------------------------------------------------------------------+
    |风险等级	     |         输入和引擎返回结果                                     |
    +-----------------------------------------------------------------------------+
    |ERROR	         |    静态分析引擎检测出跨文件漏洞。                                |
    |                |    静态分析引擎检测出单文件漏洞，机器学习引擎结果非高阈值无漏洞。      |
    |                |    不可编译到字节码的JSP文件，机器学习引擎正常阈值，检测结果为有漏洞。 |
    +-----------------------------------------------------------------------------+
    |WARNING	     |   a）单文件，静态分析引擎未检测出漏洞，机器学习引擎高阈值检测出漏洞。   |
    |                |   b）单文件，静态分析引擎检测出漏洞，机器学习引擎高阈值检测结果为无漏洞。|
    +------------------------------------------------------------------------------+

    =============================
    sa result
     "result": [
                    {
                        "taskId": "611b8e010efe5100ccf07466",
                        "ruleId": "60c86a23a27aab4a6ab26330",
                        "ruleName": "远端命令注入",
                        "ruleCwe": "CWE-78",
                        "ruleCategory": "安全功能",
                        "ruleLevel": 1,
                        "is_deleted": 0,
                        "detectedResults": [{
                            "sourceSig": "<javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>",
                            "sinkSig": "<java.sql.Statement: java.sql.ResultSet executeQuery(java.lang.String)>",
                            "path": [{
                                "file": "org/apache/jsp/jsp_005fcustom_005fspy_005ffor_005fmysql_jsp",
                                "function": "<org.apache.jsp.jsp_005fcustom_005fspy_005ffor_005fmysql_jsp: void _jspService(javax.servlet.http.HttpServletRequest,javax.servlet.http.HttpServletResponse)>",
                                "jimpleStmt": "$r107 = interfaceinvoke r0.<javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>(\"z3\")",
                                "javaStmt": "$r107 = interfaceinvoke r0.<javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>(\"z3\")",
                                "jspStmt": "$r107 = interfaceinvoke r0.<javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)>(\"z3\")",
                                "line": 426
                            }, {
                                "file": "org/apache/jsp/jsp_005fcustom_005fspy_005ffor_005fmysql_jsp",
                                "function": "<org.apache.jsp.jsp_005fcustom_005fspy_005ffor_005fmysql_jsp: java.lang.String executeSQL(java.lang.String,java.lang.String,java.lang.String,java.lang.String,java.lang.String,boolean)>",
                                "jimpleStmt": "r20 = interfaceinvoke r18.<java.sql.Statement: java.sql.ResultSet executeQuery(java.lang.String)>(r19)",
                                "javaStmt": "r20 = interfaceinvoke r18.<java.sql.Statement: java.sql.ResultSet executeQuery(java.lang.String)>(r19)",
                                "jspStmt": "r20 = interfaceinvoke r18.<java.sql.Statement: java.sql.ResultSet executeQuery(java.lang.String)>(r19)",
                                "line": 72
                            }],
                            "audit": null,
                            "facade": "org/apache/jsp/jsp_005fcustom_005fspy_005ffor_005fmysql_jsp:72",
                            "_id": "61949274c0aba7b5b2e274d8",
                        }],
                        "_id": "611b8e0a03cb3a4b762aba0a",
                    }
                ]

    ========================
    {
      "/home/model-server/tmp/tmptn_z5_ux/jsp-demo2/jsp-demo2/WEB-INF/classes/org/apache/jsp/welcome_jsp.java": {
        "status": 200,
        "cwe78": 0.9993
      },
      "/home/model-server/tmp/tmptn_z5_ux/jsp-demo2/jsp-demo2/WEB-INF/classes/org/apache/jsp/login_jsp.java": {
        "status": 200,
        "cwe78": 0.052638
      }
    }
    =======================
    merge result

    :param task_id:
    :return:
    """
    try:
        logger.info('merge result')
        task = Task.objects(id=task_id, is_deleted=0).first()
        if task is None:
            logger.info(f'task id {task_id} not found. Abort merge')
            return
        task_dict = to_dict(exclude=['code_data', 'project', 'trigger_monitor'])(task)
        sa_result = task_dict.get('result', None)
        ml_result = task_dict.get('ml_result', None)
        rule_template_snapshot = task_dict.get('rule_template_snapshot', None)
        rule_map = {}
        if rule_template_snapshot:
            rules = rule_template_snapshot['rules']
            for r in rules:
                rule_map[r['cwe']] = r['name']
        if not sa_result or not ml_result:
            logger.info('sa result or ml result none. Abort merge')
            return

        result = _merge(sa_result, ml_result, rule_map)
        result = [r.__dict__ for r in result]
        detected_result = list(filter(lambda x: x['level'] != -1, result))
        # TODO
        Task.objects(id=task_id).update_one(set__summary_result=detected_result,
                                            set__weakness_count=len(detected_result))
    except Exception:
        traceback.print_exc()


def _merge(sa_result, ml_result, rule_map=None):
    if rule_map is None:
        rule_map = {}
    mr_list = []
    sa_mr_map = {}
    for r in sa_result:
        cwe = r['ruleCwe']
        name = r['ruleName']
        for path_unit in r['detectedResults']:
            facade, line_number = path_unit['facade'].split(':')
            cross_file = check_cross_file(facade, path_unit['path'])
            mr = MergeResult(cwe, name, facade, cross_file, line_number, from_sa=True)
            mr_list.append(mr)
            if sa_mr_map.get(facade, None):
                extend_result = sa_mr_map[facade]
                extend_result.append(mr)
                sa_mr_map[facade] = extend_result
            else:
                sa_mr_map[facade] = [mr]

    for f, r in ml_result.items():
        if r['status'] != 200:
            continue
        del r['status']
        i = f.find('WEB-INF/classes/')
        if i != -1:
            facade = f[i:].lstrip('WEB-INF/classes/')
        else:
            facade = f
        if sa_mr_map.get(facade, None) is None:
            # no result from sa engine
            for rule, prob in r.items():
                cwe = rule
                name = rule_map.get(cwe, cwe)
                mr = MergeResult(cwe, name, facade, False, None, from_ml=True)
                mr.ml_probability = prob
                mr_list.append(mr)
        else:
            # find result from sa engine
            sa_mr = sa_mr_map.get(facade)
            for rule, prob in r.items():
                cwe = rule
                name = rule_map.get(cwe, cwe)
                samr_result = filter_with(cwe, sa_mr)
                if not samr_result:
                    mr = MergeResult(cwe, name, facade, False, None, from_ml=True)
                    mr.ml_probability = prob
                    mr_list.append(mr)
                else:
                    samr_result.from_ml = True
                    samr_result.ml_probability = prob
    for r in mr_list:
        r.apply_rule()
    return mr_list


def filter_with(cwe, sa_mr):
    for r in sa_mr:
        if r.cwe == cwe:
            return r
    return None


if __name__ == '__main__':
    sa_result = [
        {
            "taskId": "620c712823d08926fdc68397",
            "ruleId": "6184ba8d1de6fe71dc56a8e9",
            "ruleName": "\u547d\u4ee4\u6ce8\u5165",
            "ruleCwe": "78",
            "ruleCategory": "\u5b89\u5168\u529f\u80fd",
            "ruleLevel": 3,
            "is_deleted": 0,
            "detectedResults": [
                {
                    "sourceSig": "&lt;javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)&gt;",
                    "sinkSig": "&lt;java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])&gt;",
                    "path": [
                        {
                            "file": "org/apache/jsp/welcome_jsp.java",
                            "function": "&lt;org.apache.jsp.welcome_jsp: void _jspService(javax.servlet.http.HttpServletRequest,javax.servlet.http.HttpServletResponse)&gt;",
                            "jimpleStmt": "r35 = interfaceinvoke r0.&lt;javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)&gt;(\"j_username\")",
                            "javaStmt": "r35 = interfaceinvoke r0.&lt;javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)&gt;(\"j_username\")",
                            "jspStmt": "r35 = interfaceinvoke r0.&lt;javax.servlet.http.HttpServletRequest: java.lang.String getParameter(java.lang.String)&gt;(\"j_username\")",
                            "line": 136
                        },
                        {
                            "file": "org/apache/jsp/welcome_jsp.java",
                            "function": "&lt;org.apache.jsp.welcome_jsp: void _jspService(javax.servlet.http.HttpServletRequest,javax.servlet.http.HttpServletResponse)&gt;",
                            "jimpleStmt": "r7 = virtualinvoke r35.&lt;java.lang.String: java.lang.String[] split(java.lang.String)&gt;(\" \")",
                            "javaStmt": "r7 = virtualinvoke r35.&lt;java.lang.String: java.lang.String[] split(java.lang.String)&gt;(\" \")",
                            "jspStmt": "r7 = virtualinvoke r35.&lt;java.lang.String: java.lang.String[] split(java.lang.String)&gt;(\" \")",
                            "line": 143
                        },
                        {
                            "file": "org/apache/jsp/welcome_jsp.java",
                            "function": "&lt;org.apache.jsp.welcome_jsp: void _jspService(javax.servlet.http.HttpServletRequest,javax.servlet.http.HttpServletResponse)&gt;",
                            "jimpleStmt": "$r39[0] = r7",
                            "javaStmt": "$r39[0] = r7",
                            "jspStmt": "$r39[0] = r7",
                            "line": 144
                        },
                        {
                            "file": "org/apache/jsp/welcome_jsp.java",
                            "function": "&lt;org.apache.jsp.welcome_jsp: void _jspService(javax.servlet.http.HttpServletRequest,javax.servlet.http.HttpServletResponse)&gt;",
                            "jimpleStmt": "$r41 = virtualinvoke r38.&lt;java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])&gt;(null, $r39)",
                            "javaStmt": "$r41 = virtualinvoke r38.&lt;java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])&gt;(null, $r39)",
                            "jspStmt": "$r41 = virtualinvoke r38.&lt;java.lang.reflect.Method: java.lang.Object invoke(java.lang.Object,java.lang.Object[])&gt;(null, $r39)",
                            "line": 144
                        }
                    ],
                    "facade": "org/apache/jsp/welcome_jsp.java:144",
                    "_id": "620c7137ec14fd382e1ca5cb"
                }
            ],
            "_id": "620c7137ec14fd382e1ca5cc"
        }
    ]
    ml_result = {
        "/home/model-server/tmp/tmptn_z5_ux/jsp-demo2/jsp-demo2/WEB-INF/classes/org/apache/jsp/welcome_jsp.java": {
            "status": 200,
            "cwe78": 0.9993
        },
        "/home/model-server/tmp/tmptn_z5_ux/jsp-demo2/jsp-demo2/WEB-INF/classes/org/apache/jsp/login_jsp.java": {
            "status": 200,
            "cwe78": 0.052638
        }
    }
    mr_result = _merge(sa_result, ml_result)
    print(mr_result)
