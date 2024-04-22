import functools
import json
from math import ceil

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from utils.log import logger
from utils.mongo_json import MongoJsonResponse


def ok(data=None):
    return {
        'code': 200,
        'msg': 'ok',
        'data': data
    }


def error(code=500, msg='Internal error.'):
    return {
        'code': code,
        'msg': msg,
        'data': None
    }


def coded_error(code):
    def msg_error(msg):
        return {
            'code': code,
            'msg': msg,
            'data': None
        }

    return msg_error


def NOT_FOUND_404_MSG(msg):
    return {
        'code': '100101',
        'msg': '未找到记录: ' + msg if msg else '未找到记录',
        'data': None
    }


def valid_fail(failed_dict):
    """

    {"username": [{"message": "\u7528\u6237\u540d\u4e0d\u80fd\u4e3a\u7a7a", "code": "required"}],
    "password": [{"message": "\u8fd9\u4e2a\u5b57\u6bb5\u662f\u5fc5\u586b\u9879\u3002", "code": "required"}]}

    """
    failed_dict = json.loads(failed_dict)
    key = list(failed_dict.keys())[0]
    code = int(str(hash(key))[-6:])
    msg = key + failed_dict[key][0]['message']
    return error(code, msg)


def log(text):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        return wrapper

    return decorator


def page(doc_list, page=1, per_page=25, wrapper=None):
    paginator = Paginator(doc_list, per_page)

    try:
        documents = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        documents = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        documents = paginator.page(paginator.num_pages)

    return MongoJsonResponse(ok({
        'itemsPerPage': per_page,
        'totalItems': paginator.count,
        'totalPages': paginator.num_pages,
        'data': [wrapper(d) for d in documents] if wrapper else documents
    }))


def mongoengine_page(cls, query_dict=None, page=1, per_page=25, exclude=None, order_by=None, map=None):
    if exclude is None:
        exclude = []
    if query_dict is None:
        query_dict = {}
    try:
        data = cls.objects(**query_dict).order_by(order_by).exclude(*exclude).paginate(page, per_page)
        result_list, total_items, total_page = data.items, data.total, data.pages
    except AssertionError as e:
        logger.info('mongoengine_page error:{}'.format(str(e)))
        data = cls.objects(**query_dict).exclude(*exclude).paginate(1, per_page)
        result_list, total_items, total_page = data.items, data.total, data.pages
    return {
        'itemsPerPage': per_page,
        'totalItems': total_items,
        'totalPages': total_page,
        'data': result_list if map is None else map(result_list)
    }


def skip_limit(page=1, per_page=25):
    page = max(1, page)
    per_page = min(5000, per_page)
    return {'$skip': (page - 1) * per_page}, {'$limit': per_page}


def to_count_pipeline(pipeline):
    count_pipeline = []
    for stage in pipeline:
        if isinstance(stage, dict) and stage.__contains__('$skip'):
            break
        if isinstance(stage, dict) and stage.__contains__('$limit'):
            continue
        count_pipeline.append(stage)
    count_pipeline.append({'$project': {'_id': 1}})
    count_pipeline.append({'$group': {'_id': 'null', 'count': {'$sum': 1}}})
    return count_pipeline


def count_aggregate(cls, count_pipeline):
    count = list(cls.objects().aggregate(*count_pipeline))
    return 0 if not count else count[0].get('count')


def request_page(request):
    page, limit = page_get(request.GET)
    return page, limit


def clean_get(query_dict, pop_page_info=True, exclude_fields=[]):
    if pop_page_info:
        query_dict.pop('page', None)
        query_dict.pop('limit', None)
    for field in exclude_fields:
        query_dict.pop(field, None)
    return query_dict


def page_get(request_get):
    try:
        page = int(request_get.get('page', 1))
        per_page = int(request_get.get('limit', 25))
        if per_page < 1:
            per_page = 5000
        return max(page, 1), per_page
    except Exception as e:
        print(str(e))
        return 1, 25


def pipeline_page(cls, pipeline, page=1, per_page=25):
    skip, limit = skip_limit(page, per_page)
    for index, stage in enumerate(pipeline):
        if isinstance(stage, set) and stage.__contains__('skip'):
            pipeline[index] = skip
            continue
        if isinstance(stage, set) and stage.__contains__('limit'):
            pipeline[index] = limit
            continue
    count_pipeline = to_count_pipeline(pipeline)
    count = count_aggregate(cls, count_pipeline)
    return {
        'itemsPerPage': per_page,
        'totalItems': count,
        'totalPages': 0 if count == 0 else ceil(count / per_page),
        'data': list(cls.objects().aggregate(*pipeline))
    }


def visible(cleaned, param):
    keys = param.keys()
    for key in list(cleaned.keys()):
        if key not in keys:
            del cleaned[key]
    return cleaned


class ERROR:
    # =========COMMON===========
    NOT_FOUND_404 = error(100100, '未找到记录')
    DELETE_REFERENCE_ERROR = coded_error(100200)
    # =========COMMON===========

    # ==========AUTH============
    LOGIN_REQUIRED = error(200001, '未登录')
    USER_EXISTS = error(200100, '用户名已存在')
    LOGIN_ERROR = error(200102, '用户或密码错误')
    ROLE_RESOURCE_NOT_EMPTY = error(200104, '该角色与资源绑定，无法删除')
    # ==========AUTH============
    # ==========FILE============
    FILE_PUT_SIZE_ERROR = error(300100, '直接上传文件最大不超过5Mb')
    FILE_PUT_ERROR = error(300102, '直接上传文件失败')
    FILE_PART_INIT_ERROR = error(300104, '初始化上传文件失败')
    FILE_PART_SIZE_ERROR = error(300106, '分段上传文件最大不超过5Mb')
    FILE_PART_EXISTS = error(300108, '分段上传文件已完成')
    FILE_PART_PUT_ERROR = error(300110, '分段上传异常')
    FILE_TYPE_ERROR = error(300112, '上传类型异常')
    FILE_PART_COMPLETE_ERROR = error(300114, '完成上传异常')
    FILE_PREVIEW_ERROR = error(300116, '预览文件异常')
    FILE_DOWNLOAD_ERROR = error(300116, '预览文件异常')
    FILE_STATUS_ERROR = error(300118, '文件状态异常')
    FILE_REFERRED_DATA_PUBLIC = error(300200, '文件被数据引用，无法删除')
    FILE_REFERRED_DATA_PRIVATE = error(300202, '文件被数据私有引用，无法删除')
    FILE_REFERRED_ENTRANCE = error(300204, '文件被入口文件引用，无法删除')
    FILE_REFERRED_ALGORITHM = error(300206, '文件被提交算法文件引用，无法删除')
    FILE_REFERRED_OUTPUT = error(300208, '文件被记录输出文件引用，无法删除')
    FILE_REFERRED_ENCRYPT = error(300210, '文件被记数据集加密文件引用，无法删除')
    FILE_DELETE_ERROR = error(300212, '文件删除失败')
    FILE_ARCHIVE_NOT_FOUND = error(300214, '归档不存在，先创建归档')
    # ==========FILE============

    # ==========AUDIT============
    HANDLE_TYPE_EMPTY = error(400100, '处理类型为空')

    # ==========PROJECT============
    PROJECT_CODE_DATA_EMPTY = error(500100, '项目代码不存在')

    # ==========TASK============
    ENGINE_NOT_READY = error(600100, '引擎检测未完成')
