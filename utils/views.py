import json
import re

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views import View

from utils.log import logger
from utils.mongo_json import MongoJsonResponse
from utils.response_code import ERROR, ok
from utils.response_code import page as pagination


class ViewProcess:
    logic_delete = None
    detail_exclude = ()
    list_exclude = ()

    def check_post_params(self, request, **kwargs):
        """
        Check params or raise exception.
        """

        return True

    def before_post_json(self, request, **kwargs):
        """

        """
        self.check_post_params(request)
        return request

    def before_post_doc(self, doc, request=None, **kwargs):
        """

        """
        return doc

    def check_get_params(self, request, **kwargs):
        """
        Check params or raise exception.
        """
        return True

    def before_get(self, request, **kwargs):
        """

        """
        self.check_get_params(request)
        return request

    def after_post(self, doc, request=None, **kwargs):
        return doc

    def before_get_return(self, data, request=None, **kwargs):
        """
        data: {
            'itemsPerPage': per_page,
            'totalItems': paginator.count,
            'totalPages': paginator.num_pages,
            'data': documents
        }))
        """
        return data

    def before_post_return(self, data, request=None, **kwargs):
        """
        data: {

        }

        """
        return data

    def before_doc_filter(self, query_dict, request=None, **kwargs):
        if query_dict is None:
            query_dict = {}
        self.logic_delete_fill(query_dict)
        return query_dict

    def logic_delete_fill(self, query_dict):
        if self.logic_delete is not None:
            query_dict[self.logic_delete[0]] = self.logic_delete[1]

    def logic_delete_detail_filter(self, doc):
        if doc is None or self.logic_delete is None:
            return doc

        if hasattr(doc, self.logic_delete[0]) and getattr(doc, self.logic_delete[0]) == self.logic_delete[1]:
            return doc
        else:
            return None


def get_object_by_id(document_list, id, field_name='_id'):
    if hasattr(document_list, 'with_id') and callable(document_list.with_id):
        return document_list.with_id(id)
    return document_list.get(**{field_name: id})


def get_field_choices(f):
    choice_objects = None
    if hasattr(f, 'limit_choices_to') and callable(f.limit_choices_to):
        choice_objects = f.limit_choices_to()
    elif f.__class__.__name__ == 'ReferenceField':
        choice_objects = f.document_type.objects.all()
    elif f.__class__.__name__ == 'ManyToManyField':
        choice_objects = f.remote_field.model.objects.all()

    object_to_value = lambda obj: obj
    if f.__class__.__name__ == 'ReferenceField':
        object_to_value = lambda obj: str(obj.id)
    elif f.__class__.__name__ == 'ManyToManyField':
        object_to_value = lambda obj: obj.id
    elif f.__class__.__name__ == 'EmbeddedDocumentListField':
        object_to_value = lambda obj: obj.id

    if choice_objects is not None:
        return list(map(lambda obj: [object_to_value(obj), str(obj)], choice_objects))
    return getattr(f, 'choices', None)


class ListView(View):
    document = None
    per_page = 25

    embedded_fields = ()
    embedded_pk_kw = ()

    def get_document_list(self, request, **kwargs):
        document_list = self.__class__.document.objects.all()

        embedded_queries = list(zip(self.__class__.embedded_fields, self.__class__.embedded_pk_kw))
        for field, kw in embedded_queries:
            document_list = getattr(get_object_by_id(document_list, kwargs.get(kw, None)), field)

        query_dict = request.GET.dict()
        query_dict.pop('page', None)
        if query_dict:
            document_list = document_list.filter(**query_dict)

        return document_list

    def get(self, request, *args, **kwargs):

        document_list = self.get_document_list(request, **kwargs)

        paginator = Paginator(document_list, self.__class__.per_page)

        page = request.GET.get('page')
        try:
            documents = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            documents = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            documents = paginator.page(paginator.num_pages)

        return MongoJsonResponse({
            'itemsPerPage': self.__class__.per_page,
            'totalItems': paginator.count,
            'totalPages': paginator.num_pages,
            'data': documents
        })


class APIView(View, ViewProcess):
    document = None
    per_page = 25
    page = 1

    embedded_fields = ()
    embedded_pk_kw = ()

    def get_document_list(self, request, **kwargs):
        document_list = self.__class__.document.objects.exclude(*self.list_exclude).all()

        embedded_queries = list(zip(self.__class__.embedded_fields, self.__class__.embedded_pk_kw))
        logger.info('embedded_queries: {}'.format(embedded_queries))
        for field, kw in embedded_queries:
            ol = get_object_by_id(document_list, kwargs.get(kw, None))
            document_list = getattr(ol, field)

        query_dict = request.GET.dict()
        query_dict.pop('page', None)
        query_dict.pop('limit', None)
        query_dict = self.before_doc_filter(query_dict, request, **kwargs)
        if query_dict:
            document_list = document_list.filter(**query_dict)

        return document_list

    def save_document(self, request, doc):
        doc.save()

    def check_permission(self, method, request, **kwargs):
        if method == 'GET':
            return True
        return request.user.is_authenticated

    def get(self, request, *args, **kwargs):
        logger.info('get. **kwargs:{}'.format(kwargs))
        document_list = self.get_document_list(request, **kwargs)
        page = request.GET.get('page', self.page)
        per_page = int(request.GET.get('limit', self.per_page))
        page_result = pagination(document_list, page, per_page)
        page_result = self.before_get_return(page_result, request, **kwargs)
        return page_result

    def post(self, request, **kwargs):
        document = self.__class__.document
        request = self.before_post_json(request, **kwargs)
        new_row = document().from_json(json.dumps(request.REQUEST))
        new_row = self.before_post_doc(new_row, request, **kwargs)
        self.save_document(request, new_row)
        new_row = self.after_post(new_row, request, **kwargs)
        result = MongoJsonResponse(ok(new_row))
        result = self.before_post_return(result, request, **kwargs)
        return result


class APIMetaView(View):
    document = None

    def get_fields(self):
        return [
            self.__class__.document._fields[k]
            for k in self.__class__.document._fields_ordered]

    def get(self, request, **kwargs):
        fields = self.get_fields()

        return JsonResponse({'data': [
            {
                'name': f.name,
                'class': re.sub('Field$', '', f.__class__.__name__),
                'editable': getattr(f, 'editable', None),
                'blank': getattr(f, 'blank', not getattr(f, 'required', False)),
                'choices': get_field_choices(f),
                'verbose_name': getattr(f, 'verbose_name', '').capitalize() or None,
                'widget': getattr(f, 'widget', None),
                'help_text': getattr(f, 'help_text', None),
            }
            for f in fields
        ]})


class APIDetailView(View, ViewProcess):
    document = None
    pk_url_kwarg = 'id'

    embedded_fields = ()
    embedded_pk_kw = ()

    def get_document(self, request, **kwargs):
        document_list = self.__class__.document.objects.exclude(*self.detail_exclude).all()
        embedded_queries = list(zip(self.__class__.embedded_fields, self.__class__.embedded_pk_kw))
        for field, kw in embedded_queries:
            document_list = getattr(get_object_by_id(document_list, kwargs.get(kw, None)), field)

        doc = get_object_by_id(document_list, kwargs.get(self.__class__.pk_url_kwarg))
        doc = self.logic_delete_detail_filter(doc)
        return doc

    def save_document(self, request, doc):
        if hasattr(doc, 'save'):
            doc.save()
        else:
            doc._instance.save()

    def check_permission(self, method, request, **kwargs):
        if method == 'GET':
            return True
        return request.user.is_authenticated

    def get(self, request, **kwargs):
        doc = self.get_document(request, **kwargs)
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        return MongoJsonResponse(ok(doc))

    def post(self, request, **kwargs):
        doc = self.get_document(request, **kwargs)
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        request = self.before_post_json(request, **kwargs)
        json_document = doc.__class__.from_json(json.dumps(request.REQUEST))
        obj_list = dir(json_document)
        for k in request.REQUEST.keys():
            if k in obj_list and k not in self.detail_exclude:
                setattr(doc, k, getattr(json_document, k))
        doc = self.before_post_doc(doc, request, **kwargs)
        self.save_document(request, doc)
        doc = self.after_post(doc, request, **kwargs)
        result = MongoJsonResponse(ok(doc))
        result = self.before_post_return(result, request, **kwargs)
        return result

    put = post

    def delete(self, request, **kwargs):
        doc = self.get_document(request, **kwargs)
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        if self.logic_delete:
            update_op = {'set__' + self.logic_delete[0]: self.logic_delete[2]}
            self.__class__.document.objects(id=doc.id).update_one(**update_op)
        else:
            doc.delete()
        # HTTP Status 204: No Content
        return JsonResponse(ok())
