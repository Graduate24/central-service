import json

from django.contrib.auth import get_user_model
from django.core.serializers import serialize
from django.shortcuts import get_object_or_404
from mongoengine import *

from utils.log import logger


class DjangoUser(EmbeddedDocument):
    pk = LongField()

    meta = {
        'strict': False
    }

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], get_user_model()):
            self.pk = args[0].pk
        super().__init__(*args, **kwargs)

    def to_mongo(self, *args, **kwargs):
        user = super().to_mongo(*args, **kwargs)
        try:
            djangoUser = get_user_model().objects.get(id=self.pk)
        except Exception as e:
            logger.error(e)
            return {}
        # djangoUser = get_object_or_404(get_user_model(), pk=self.pk)

        # JSON serializer in django only accepts iterable objects
        # A array wrapper is needed for serializing a model instance
        # See https://stackoverflow.com/questions/757022/
        user.update(json.loads(serialize('json', [djangoUser]))[0]['fields'])

        user['date_joined'] = djangoUser.date_joined
        user['last_login'] = djangoUser.last_login
        user['pk'] = self.pk
        del user['password']

        return user

    @classmethod
    def _from_son(cls, son, *args, **kwargs):
        if isinstance(son, int):
            return DjangoUser(pk=son)
        return super(DjangoUser, cls)._from_son(son, *args, **kwargs)

    def __eq__(self, other):
        if isinstance(other, DjangoUser):
            return self.pk == other.pk
        if isinstance(other, str):
            return str(self) == other
        return super().__eq__(other)

    @property
    def id(self):
        return self.pk

    @classmethod
    def all(cls, **kwargs):
        return list(map(lambda user: DjangoUser(user.pk), get_user_model().objects.all()))

    @classmethod
    def create_user(cls, username, password):
        try:
            user = get_user_model().objects.get(username=username)
        except:
            user = get_user_model().objects.create_user(username=username, password=password)
        return DjangoUser(pk=user.pk)

    def delete(self):
        djangoUser = get_object_or_404(get_user_model(), pk=self.pk)
        djangoUser.delete()

    @classmethod
    def filter(cls, **kwargs):
        return list(map(lambda user: DjangoUser(user.pk), get_user_model().objects.filter(**kwargs)))

    def __str__(self):
        return get_object_or_404(get_user_model(), pk=self.pk).username
