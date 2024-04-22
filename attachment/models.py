import time

from django import forms
from django.utils import timezone
from mongoengine import *
# Create your models here.
from mongoengine_pagination import DocumentPro

from sacentral.settings import FILE_DEFAULT_FOLDER
from utils import file_server
from utils.file_server import preview
from utils.log import logger


# Create your models here.
from ws.models import OnlineClient


class FileMeta(EmbeddedDocument):
    content_type = StringField()
    measurement = ListField(IntField())
    # 图片缩略图
    thumbnail = StringField(max_length=65535)


class MultipartRecord(EmbeddedDocument):
    part = IntField(required=True)
    size = LongField(required=True)
    # 0, 成功 1，上传中
    status = IntField(required=True, default=1)
    md5 = StringField(max_length=65535)
    etag = StringField(default='')


class FileStorage(DocumentPro):
    name = StringField(required=True)
    # multi upload upload_id
    upload_id = StringField(required=False)
    # multi upload total parts
    parts = IntField(required=False)
    md5 = StringField(required=True)
    size = LongField(required=True)
    # 0, 成功 1，上传中
    status = IntField(required=True, default=1)
    is_deleted = IntField(required=True, default=0)
    # 1,小文件直接上传，2，大文件分批上传
    type = IntField(required=True, default=1)
    folder = StringField(required=True, default=FILE_DEFAULT_FOLDER)
    uploader = ReferenceField(OnlineClient)
    local = IntField(default=0)
    meta_info = EmbeddedDocumentField(FileMeta, required=True)
    part_record = EmbeddedDocumentListField(MultipartRecord, required=False)
    object_key = StringField(required=True)
    source_path = StringField()
    version = StringField()
    time = DateTimeField(default=timezone.now)

    def set_object_key(self):
        self.object_key = self.folder + '/' + self.md5 + '/' + self.name

    def download(self, path):
        payload = {
            'objectKey': self.object_key,
            'fileName': self.name,
            # 有效期24小时
            'expiresTime': int(time.time()) + 60 * 60 * 24,
        }
        url = file_server.download(payload)
        file_server.download_write_local(url, path)

    def preview(self):
        if self.status != 0:
            return None
        try:
            payload = {
                'objectKey': self.object_key,
                'fileName': self.name,
                'expiresTime': int(time.time()) + 60 * 60 * 24,
            }
            url = preview(payload)
            return url
        except Exception as e:
            logger.error(e)
        return None


class MultipartInitForm(forms.Form):
    name = forms.CharField(required=True)
    size = forms.IntegerField(required=True)
    md5 = forms.CharField(required=True)
    parts = forms.IntegerField(required=True)
    content_type = forms.CharField(required=False)


class MultipartPutForm(forms.Form):
    part_number = forms.IntegerField(required=True)
