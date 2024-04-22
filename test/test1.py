from analysis.models import SaResult, DetectedResult

if __name__ == "__main__":
    result = {
        "60c86a23a27aab4a6ab26330": {
            "ruleName": "远端命令注入",
            "ruleCwe": "CWE-78",
            "ruleCategory": "安全功能",
            "ruleLevel": 1,
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
                    ]
                }
            ]
        }
    }
    sa_results = []
    for k, v in result.items():
        v['ruleId'] = k
        detected_results = [DetectedResult(**d) for d in v.get('detectedResults')]
        sa_result = SaResult(**v)
        sa_result.detectedResults = detected_results
        sa_results.append(sa_result)
    print(sa_results)
