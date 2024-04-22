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

    def apply_rule(self, threshold_low=0.85, threshold_high=0.95):
        """
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
        :param threshold_low:
        :param threshold_high:
        :return:
        """
        self.threshold_low = threshold_low
        self.threshold_high = threshold_high
        if self.from_sa and self.cross_file:
            self.level = 0
            return
        elif self.from_sa and not self.cross_file and self.from_ml and self.ml_probability < self.threshold_low:
            self.level = 0
            return
        elif not self.from_sa and self.from_ml and self.ml_probability >= self.threshold_low:
            self.level = 0
            return
        elif not self.from_sa and self.from_ml and self.ml_probability >= self.threshold_high:
            self.level = 1
            return
        elif self.from_sa and not self.cross_file and self.from_ml and self.ml_probability < self.threshold_high:
            self.level = 1
            return
        else:
            self.level = -1


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


def check_cross_file(target, path):
    for p in path:
        if target == p['file']:
            return True
    return False


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
        "/WEB-INF/classes/org/apache/jsp/welcome_jsp.java": {
            "22": 0.000023,
            "78": 0.999331,
            "89": 0.000453,
            "status": 200
        },
        "/WEB-INF/classes/org/apache/jsp/login_jsp.java": {
            "22": 0.000022,
            "78": 0.052638,
            "89": 0.00001,
            "status": 200
        }
    }
    mr_result = _merge(sa_result, ml_result)
    for r in mr_result:
        print(r.__dict__)
