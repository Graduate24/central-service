import datetime
import json

from bson import json_util, ObjectId
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from mongoengine import Document, EmbeddedDocument, QuerySet


class MongoJsonDecoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(obj, 'to_mongo'):
            return obj.to_mongo()
        if hasattr(obj, 'to_json'):
            return json.loads(obj.to_json())
        if hasattr(obj, '__iter__'):
            return list(obj)
        # TODO
        if isinstance(obj, ObjectId):
            return str(obj)
        return json_util.default(obj)


class MongoJsonResponse(JsonResponse):
    def __init__(self, data, *args, **kwargs):
        kwargs.setdefault('encoder', MongoJsonDecoder)
        super().__init__(data, *args, **kwargs)


def dumps(data):
    return json.dumps(data, cls=MongoJsonDecoder)


class BaseEmbeddedDocument(EmbeddedDocument):
    meta = {
        'abstract': True,
    }

    @classmethod
    def from_json(cls, json_data, created=False):
        son = json_util.loads(json_data)
        return cls._from_son(son, created=created)


def clean(data_dict, only_fields=None):
    if not only_fields:
        return data_dict
    data_dict = data_dict.copy()
    for k in list(data_dict.keys()):
        if not only_fields.__contains__(k):
            del data_dict[k]
    return data_dict


def to_dict(exclude=None):
    if exclude is None:
        exclude = []

    def expand(obj):
        if isinstance(obj, (QuerySet, list)):
            return list(map(expand, obj))
        elif isinstance(obj, (Document, EmbeddedDocument)):
            doc = {}
            for field_name, field_type in obj._fields.items():
                if field_name not in exclude:
                    field_value = getattr(obj, field_name)
                    del_id = False
                    if field_name == 'id' and isinstance(field_value, ObjectId):
                        doc['_id'] = expand(field_value)
                        del_id = True
                    doc[field_name] = expand(field_value)
                    if del_id:
                        del doc['id']
            return doc
        else:
            return obj

    return expand


if __name__ == '__main__':
    print(isinstance('None', str))
