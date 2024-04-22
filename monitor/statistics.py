import logging

from analysis.models import Task, SaResult, MonitorProject
from sacentral.settings import MONGODB_BROKER_URL
from ws.models import OnlineClient

logging.debug(MONGODB_BROKER_URL)


def client_statistic():
    count = OnlineClient.objects().only('id').count()
    online_count = OnlineClient.objects(status=1).only('id').count()
    return {'client_count': count, 'online_client_count': online_count}


def weakness_audit_statistic():
    pipeline = [{'$match': {'is_deleted': 0, 'status': 2}},
                {'$project': {
                    'status': 1,
                    'weakness_count': 1,
                    'audit_count': 1,
                }},
                {'$group':
                    {
                        '_id': None,
                        'weakness_count': {'$sum': "$weakness_count"},
                        'audit_count': {'$sum': "$audit_count"}
                    }
                }]

    ret = list(Task.objects.aggregate(*pipeline))
    return ret[0] if len(ret) != 0 else {}


def category_weakness_statistic():
    pipeline = [
        {'$match':
            {
                'is_deleted': 0,
                'detectedResults': {'$exists': True, '$ne': []}
            }

        },
        {'$group':
            {
                '_id': "$ruleCategory",
                'category': {'$first': '$ruleCategory'},
                'count': {'$sum': 1}

            }
        }
    ]
    ret = list(SaResult.objects.aggregate(*pipeline))
    return ret


def rule_weakness_statistic():
    pipeline = [
        {'$match':
            {
                'is_deleted': 0,
                'detectedResults': {'$exists': True, '$ne': []}
            }

        },
        {'$group':
            {
                '_id': "$ruleId",
                'rule': {'$first': '$ruleName'},
                'count': {'$sum': 1}

            }
        }
    ]
    ret = list(SaResult.objects.aggregate(*pipeline))
    return ret


def level_weakness_statistic():
    pipeline = [
        {'$match':
            {
                'is_deleted': 0,
                'detectedResults': {'$exists': True, '$ne': []}
            }

        },
        {'$group':
            {
                '_id': "$ruleLevel",
                'level': {'$first': '$ruleLevel'},
                'count': {'$sum': 1}

            }
        }
    ]
    ret = list(SaResult.objects.aggregate(*pipeline))
    return ret


def detected_result():
    pipeline = [
        {'$match':
            {
                'is_deleted': 0,
                'detectedResults': {'$exists': True, '$ne': []},
                'ruleCategory': {'$exists': True, '$ne': []}
            }

        },
        {"$lookup": {
            "from": "detected_result",
            "as": "detected_result",
            'let': {'pid': '$detectedResults'},
            'pipeline': [
                {'$match':
                    {'$expr': {
                        '$and': [
                            {'$in': ['$_id', '$$pid']},
                            # {'$eq': ['$audit', None]}
                        ]
                    }}
                },
                {"$project": {"audit.handle_type": 1}}]
        }}
    ]

    return list(SaResult.objects.aggregate(*pipeline))


def detected_result_list():
    pipeline = [
        {"$match": {"is_deleted": 0, "detectedResults": {"$exists": 1, "$ne": []}}},
        {"$lookup": {
            "from": "task",
            "as": "task",
            "let": {"pid": {"$toObjectId": "$taskId"}},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$_id", "$$pid"]},
                    {"$eq": ["$status", 2]},
                    {"$eq": ["$is_deleted", 0]}]
                }}},
                {"$project": {"project": 1, "trigger_monitor": 1}}
            ]
        }},
        {"$project": {
            "ruleId": 1,
            "ruleName": 1,
            "ruleCwe": 1,
            "ruleCategory": 1,
            "ruleLevel": 1,
            "detectedResults": 1,
            "task": {"$arrayElemAt": ["$task", 0]}
        }},
        {"$addFields": {"project": "$task.project", "client": "$task.trigger_monitor"}},
        {"$match": {"task": {"$exists": 1}}},
        {"$lookup": {
            "from": "detected_result",
            "as": "detected_results",
            "let": {"pid": "$detectedResults"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$in": ["$_id", "$$pid"]}]
                }}},
                {"$project": {"facade": 1, "audit.handle_type": 1}}
            ]
        }},
        {"$project": {
            "detectedResults": 0,
            "task": 0
        }},
        {"$lookup": {
            "from": "monitor_project",
            "as": "project",
            "let": {"pid": "$project"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$_id", "$$pid"]}]
                }}},
                {"$project": {"name": 1}}
            ]
        }},

        {"$addFields": {"project": {"$arrayElemAt": ["$project", 0]}}},
        {"$lookup": {
            "from": "online_client",
            "as": "client",
            "let": {"pid": "$client"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$_id", "$$pid"]}]
                }}},
                {"$project": {"name": 1}}
            ]
        }},

        {"$addFields": {"client": {"$arrayElemAt": ["$client", 0]}}},
        {"$unwind": "$detected_results"}

    ]
    return list(SaResult.objects.aggregate(*pipeline))


def result_count(result):
    count = 0
    for r in result:
        count += len(r['detectedResults'])
    return count


def audit_count(result):
    count = 0
    for r in result:
        count += len(list(filter(lambda x: x.get('audit', None) is not None, r['detected_result'])))
    return count

def _groupby(l, k):
    r = {}
    for e in l:
        if r.get(k(e), None) is None:
            t = [e]
            r[k(e)] = t
        else:
            t = r[k(e)]
            t.append(e)
            r[k(e)] = t
    return r

def clc_category_weakness_statistic(detect_result):
    ret = []
    for k, v in _groupby(detect_result, lambda x: x['ruleCategory']).items():
        vs = list(v)
        count = result_count(vs)
        auditcount = audit_count(vs)
        ret.append({'category': k, 'count': count, 'audit': auditcount})
    return ret


def clc_rule_weakness_statistic(detect_result):
    ret = []
    for k, v in _groupby(detect_result, lambda x: x['ruleId']).items():
        vs = list(v)
        if len(vs) == 0:
            continue
        name = vs[0]['ruleName']
        count = result_count(vs)
        auditcount = audit_count(vs)
        ret.append({'rule': name, 'count': count, 'audit': auditcount})
    return ret


def clc_level_weakness_statistic(detect_result):
    ret = []
    for k, v in _groupby(detect_result, lambda x: x['ruleLevel']).items():
        vs = list(v)
        count = result_count(vs)
        auditcount = audit_count(vs)
        ret.append({'level': k, 'count': count, 'audit': auditcount})
    return ret


def project_statistic():
    pipeline = [
        {'$match':
            {
                'is_deleted': 0,
            }
        },
        {"$project": {"monitor_path": 1}},
        {
            '$group': {
                '_id': "$monitor_path",
            }
        },
        {'$group':
            {
                '_id': None,
                'count': {'$sum': 1}
            }
        }
    ]
    ret = list(MonitorProject.objects.aggregate(*pipeline))
    return ret[0] if len(ret) != 0 else {}


def statistics():
    result = detected_result()
    stat = {
        'client_statistic': client_statistic(),
        'weakness_audit_statistic': weakness_audit_statistic(),
        'category_weakness_statistic': clc_category_weakness_statistic(result),
        'rule_weakness_statistic': clc_rule_weakness_statistic(result),
        'level_weakness_statistic': clc_level_weakness_statistic(result),
        'project_statistic': project_statistic(),
        'detected_result_list': detected_result_list()
    }
    return stat


if __name__ == "__main__":
    ret = statistics()
    print(ret)
