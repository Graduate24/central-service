import time

from analysis.models import CodeData
from sacentral.settings import FILE_PUT_SIZE, FILE_PART_SIZE
from utils.file_server import md5_hash, init_part, part_put, part_complete, download, preview, delete
from utils.file_server import upload_file
from utils.mongo_json import to_dict
from utils.response_code import valid_fail, page_get, mongoengine_page
from utils.views import *
from .models import FileStorage, FileMeta, MultipartInitForm, MultipartPutForm, MultipartRecord


class MiniFileView(View):
    def post(self, request):
        """
        @api {POST} api/attachments/file/put 上传小文件
        @apiVersion 1.0.0
        @apiName upload file
        @apiGroup Attachment
        @apiDescription 上传小于30M的文件

        @apiParam {Number}  [hist=0] 是否直方均衡
        @apiParam {File} file 文件

         @apiHeaderExample {json} Header-Example:
         {
         "Content-Type": "multipart/form-data"
         }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "_id": {
                        "$oid": "5ece92b7899e23d9f0704551"
                    },
                    "name": "03992_oneontarapids_6400x4000.jpg",
                    "md5": "e1e48f5d9f9d0cf061f72706c403e3f1",
                    "size": 14743865,
                    "status": 0,
                    "type": 1,
                    "folder": "common",
                    "meta_info": {
                        "hist": 0,
                        "content_type": "image/jpeg",
                        "measurement": [
                            6400,
                            4000
                        ],
                        "thumbnail": "data:image/png;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQND...."
                    },
                    "part_record": [],
                    "time": {
                        "$date": 1590625079138
                    }
                }
            }
        """
        name = request.FILES['file'].name
        logger.info('start post attachment {}'.format(name))
        file = request.FILES['file']
        if file.size > FILE_PUT_SIZE:
            return JsonResponse(ERROR.FILE_PUT_SIZE_ERROR)

        # objectKey looks like this: "folder/fileName".If objectKey = "fileName",
        # we will put the object into the bucket's root. File name should be unique,
        # otherwise it will be replaced.
        hash_code = md5_hash(file)
        md5 = str(hash_code).lower()
        file_storage_ex = FileStorage.objects.filter(md5=md5, status=1).first()
        if file_storage_ex:
            file_storage_ex.delete()

        file_storage_ex = FileStorage.objects.filter(md5=md5, status=0).first()
        if file_storage_ex:
            if file_storage_ex.name == name:
                return MongoJsonResponse(ok(file_storage_ex))
            else:
                new_doc = FileStorage(name=name, md5=file_storage_ex.md5, size=file_storage_ex.size,
                                      meta_info=file_storage_ex.meta_info, object_key=file_storage_ex.object_key,
                                      status=0)
                new_doc.save()
                return MongoJsonResponse(ok(new_doc))

        meta = FileMeta(content_type=file.content_type)
        file_storage = FileStorage(name=name, md5=md5, size=file.size, meta_info=meta)
        file_storage.set_object_key()
        file_storage.save()
        try:
            payload = {'objectKey': file_storage.object_key}
            file.seek(0)
            files = [
                ('file', file)
            ]
            upload_file(files, payload)
            file_storage.status = 0
            file_storage.save()

        except Exception as e:
            logger.error(e)
            file_storage.delete()
            return JsonResponse(ERROR.FILE_PUT_ERROR)

        return MongoJsonResponse(ok(file_storage))


class MultiPartInitView(View):
    def post(self, request):
        """
        @api {POST} api/attachments/file/part/init 初始化大文件分段上传
        @apiVersion 1.0.0
        @apiName upload part init
        @apiGroup Attachment
        @apiDescription 初始化大文件分段上传。上传大于30M的文件，使用该接口。客户端将文件分割为不超过 10m/个的文件流并上传。
                        需要指定文件分割总个数，md5等信息，获取返回id后，依据次id上传具体内容

        @apiParam {String}  name 文件名
        @apiParam {Number}  size 文件大小
        @apiParam {String}  md5 文件md5，16进制全小写
        @apiParam {Number}  [hist=0] 是否直方均衡
        @apiParam {Number}  parts 文件分段数量
        @apiParam {String}  [content_type] 类型，例如 image/tiff，text/plain，application/octet-stream

         @apiHeaderExample {json} Header-Example:
         {
         "Content-Type": "multipart/form-data"
         }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "_id": {
                        "$oid": "5ecf60d5bd3a164466160b2a"
                    },
                    "name": "asdf",
                    "upload_id": "62dd1dd5040408c",
                    "parts": 3,
                    "md5": "e534e9c714d4059c123d7b3ab3cf13b1",
                    "size": 123413,
                    "status": 1,
                    "type": 2,
                    "folder": "common",
                    "meta_info": {
                        "hist": 0,
                        "content_type": "image",
                        "measurement": []
                    },
                    "part_record": [],
                    "time": {
                        "$date": 1590677845515
                    }
                }
            }
        """
        init = MultipartInitForm(request.REQUEST)
        if not init.is_valid():
            failed_dict = init.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        init = init.clean()

        file_storage_ex = FileStorage.objects.filter(md5=init.get('md5'), status=0, is_deleted=0).exclude(
            'part_record').first()
        if file_storage_ex:
            if file_storage_ex.name == init.get('name'):
                return MongoJsonResponse(ok(file_storage_ex))
            else:
                new_doc = FileStorage(name=init.get('name'), md5=file_storage_ex.md5, size=file_storage_ex.size,
                                      meta_info=file_storage_ex.meta_info, object_key=file_storage_ex.object_key,
                                      type=file_storage_ex.type, part_record=file_storage_ex.part_record, status=0)
                new_doc.save()
                return MongoJsonResponse(ok(new_doc))

        file_storage_ex = FileStorage.objects.filter(md5=init.get('md5'), status=1, is_deleted=0).first()
        if file_storage_ex:
            if init.get('parts') != file_storage_ex.parts:
                file_storage_ex.parts = init.get('parts')
            if init.get('size') != file_storage_ex.size:
                file_storage_ex.size = init.get('size')
            file_storage_ex.name = init.get('name')
            # file_storage_ex.part_record = None
            file_storage_ex.set_object_key()
            payload = {'objectKey': file_storage_ex.object_key}
            upload_id = init_part(payload)
            file_storage_ex.upload_id = upload_id
            file_storage_ex.save()

            return MongoJsonResponse(ok(file_storage_ex))

        meta = FileMeta(content_type=init.get('content_type'))

        file_storage = FileStorage(name=init.get('name'), parts=init.get('parts'),
                                   md5=init.get('md5'), size=init.get('size'), type=2, meta_info=meta)
        file_storage.set_object_key()
        file_storage.save()
        try:
            payload = {'objectKey': file_storage.object_key}
            upload_id = init_part(payload)
            file_storage.upload_id = upload_id
            file_storage.save()
        except Exception as e:
            logger.error(e)
            file_storage.delete()
            return JsonResponse(ERROR.FILE_PART_INIT_ERROR)
        return MongoJsonResponse(ok(file_storage))


class PartCompleteView(View):
    def post(self, request, id):
        """
        @api {POST} api/attachments/file/:id/part/complete 文件分段上传完成
        @apiVersion 1.0.0
        @apiName upload part complete
        @apiGroup Attachment
        @apiDescription 所有文件分段上传完成，合并完成上传

        @apiParam {String}  id 文件id
        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                }

            }
        """
        file_storage = FileStorage.objects.with_id(id)
        if file_storage is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        if file_storage.type == 1:
            return JsonResponse(ERROR.FILE_TYPE_ERROR)

        try:
            part_record = [p for p in file_storage.part_record if p.status == 0]
            part_record.sort(key=lambda x: x.part)
            etags = [p.etag for p in part_record]
            logger.info('etags:{}'.format(etags))
            payload = {
                'uploadId': file_storage.upload_id,
                'objectKey': file_storage.object_key,
                'size': file_storage.parts,
                'md5': file_storage.md5,
                'etags': ','.join(etags)

            }
            part_complete(payload)
            file_storage.status = 0
            file_storage.save()
        except Exception as e:
            logger.error(e)
            return JsonResponse(ERROR.FILE_PART_COMPLETE_ERROR)
        return MongoJsonResponse(ok())


class PreviewView(View):
    def get(self, request, id):
        """
        @api {POST} api/attachments/file/:id/preview 预览图片地址，有效期24h
        @apiVersion 1.0.0
        @apiName preview
        @apiGroup Attachment
        @apiDescription 获取预览图片地址

        @apiParam {String}  id 文件id

         @apiHeaderExample {json} Header-Example:
         {
         "Content-Type": "multipart/form-data"
         }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                        "http://xxxxxx"
                    }
                }
            }
        """
        file_storage = FileStorage.objects.with_id(id)
        if file_storage is None or file_storage.status != 0:
            return JsonResponse(ERROR.NOT_FOUND_404)
        try:
            payload = {
                'objectKey': file_storage.object_key,
                # 有效期24小时
                'expiresTime': int(time.time()) + 60 * 60 * 24,

            }
            url = preview(payload)
            return JsonResponse(ok(url))
        except Exception as e:
            logger.error(e)
        return JsonResponse(ERROR.FILE_PREVIEW_ERROR)


class DownloadView(View):
    def get(self, request, id):
        """
        @api {GET} api/attachments/file/:id/download 文件下载地址，有效期24h
        @apiVersion 1.0.0
        @apiName download
        @apiGroup Attachment
        @apiDescription 获取文件下载地址

        @apiParam {String}  id 文件id

         @apiHeaderExample {json} Header-Example:
         {
         "Content-Type": "multipart/form-data"
         }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                        "http://xxxxxx"
                    }
                }
            }
        """
        file_storage = FileStorage.objects.with_id(id)
        if file_storage is None or file_storage.status != 0:
            return JsonResponse(ERROR.NOT_FOUND_404)
        try:
            payload = {
                'objectKey': file_storage.object_key,
                'fileName': file_storage.name,
                # 有效期24小时
                'expiresTime': int(time.time()) + 60 * 60 * 24,
            }
            url = download(payload)
            return JsonResponse(ok(url))
        except Exception as e:
            logger.error(e)
        return JsonResponse(ERROR.FILE_DOWNLOAD_ERROR)


class MultiPartPutView(APIDetailView):
    document = FileStorage

    def post(self, request, id):
        """
        @api {POST} api/attachments/file/:id/part/put 文件分段上传
        @apiVersion 1.0.0
        @apiName upload part put
        @apiGroup Attachment
        @apiDescription 分段文件上传

        @apiParam {String}  id 文件id
        @apiParam {file}  file 文件
        @apiParam {Number}  part_number 文件分段编号，从1开始

         @apiHeaderExample {json} Header-Example:
         {
         "Content-Type": "multipart/form-data"
         }

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
                "code": 200,
                "msg": "ok",
                "data": {
                }

            }
        """
        file_storage = FileStorage.objects.with_id(id)
        if file_storage is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        if file_storage.status == 0:
            return JsonResponse(ERROR.FILE_PART_EXISTS)
        if file_storage.type == 1:
            return JsonResponse(ERROR.FILE_TYPE_ERROR)
        part = MultipartPutForm(request.POST)
        if not part.is_valid():
            failed_dict = part.errors.as_json()
            logger.info(failed_dict)
            return JsonResponse(valid_fail(failed_dict))
        part = part.clean()
        file = request.FILES['file']
        if file.size > FILE_PART_SIZE:
            return JsonResponse(ERROR.FILE_PART_SIZE_ERROR)

        try:
            payload = {
                'objectKey': file_storage.object_key,
                'uploadId': file_storage.upload_id,
                'partNumber': int(part.get('part_number'))
            }
            file.seek(0)
            files = [
                ('file', file)
            ]
            result = part_put(files, payload)
            hash_code = md5_hash(file)
            md5 = str(hash_code).lower()
            FileStorage.objects.filter(id=id).update_one(pull__part_record__part=part.get('part_number'))
            record = MultipartRecord(part=part.get('part_number'), size=file.size, status=0, md5=md5,
                                     etag=result.get('etag', ''))
            FileStorage.objects.filter(id=id).update_one(push__part_record=record)

            return JsonResponse(ok())
        except Exception as e:
            logger.error(e)
            return JsonResponse(ERROR.FILE_PART_PUT_ERROR)


class FileStorageView(APIView):
    document = FileStorage
    logic_delete = ('is_deleted', 0, 1)

    def doc_get(self):
        """
        @api {GET} api/attachments/files 文件列表
        @apiVersion 1.0.0
        @apiName get files
        @apiGroup Attachment
        @apiDescription 文件列表

        @apiParam {Number}  [page=1] 当前页码 url参数 ?page=
        @apiParam {Number}  [limit=25] 每页记录数 url参数 ?limit=

        @apiSuccessExample Response-Success:
           HTTP 1.1/ 200K
           {
            "code": 200,
            "msg": "ok",
            "data": {
                "itemsPerPage": 2,
                "totalItems": 6,
                "totalPages": 3,
                "data": [
                    {
                        "_id": {
                            "$oid": "5ece5c0036ba2f90dc9fa532"
                        },
                        "name": "03438_archesnationalpark_5120x3200.jpg",
                        "md5": "e534e9c714d4059c123d7b3ab3cf13bd",
                        "size": 16231735,
                        "status": 0,
                        "is_deleted": 0,
                        "type": 1,
                        "folder": "common",
                        "uploader": {
                            "name": "LG Electronics17Z90N-V.AA76C (version: 0.1)",
                            "online_time": "2021-07-20 14:40:04",
                            "client": [
                                "127.0.0.1",
                                58238
                            ],
                            "machine_code": "7e204f477ea640fb91beb71daf1f2c62",
                            "is_random_gen": 0,
                            "tags": [
                                "a",
                                "b"
                            ],
                            "location": "l1",
                            "asset_serial": "aaad",
                            "agent_version": "1.0",
                            "business_group": "a",
                            "status": 1,
                            "last_update": "2021-08-17 15:21:14",
                            "id": "60f66fc45c900a3bd0a57a4f"
                        },
                        "local": 0,
                        "meta_info": {
                            "hist": 0,
                            "content_type": "image/jpeg",
                            "measurement": [
                                5120,
                                3200
                            ],
                            "thumbnail": "data:image/png;base64,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"
                        },
                        "part_record": [],
                        "time": {
                            "$date": 1590611072710
                        }
                    },
                    {
                        "_id": {
                            "$oid": "5ecf60d5bd3a164466160b2a"
                        },
                        "name": "asdf",
                        "upload_id": "62dd1dd5040408c",
                        "parts": 3,
                        "md5": "e534e9c714d4059c123d7b3ab3cf13b1",
                        "size": 123413,
                        "status": 1,
                        "is_deleted": 0,
                        "type": 2,
                        "folder": "common",
                        "uploader": {
                            "name": "LG Electronics17Z90N-V.AA76C (version: 0.1)",
                            "online_time": "2021-07-20 14:40:04",
                            "client": [
                                "127.0.0.1",
                                58238
                            ],
                            "machine_code": "7e204f477ea640fb91beb71daf1f2c62",
                            "is_random_gen": 0,
                            "tags": [
                                "a",
                                "b"
                            ],
                            "location": "l1",
                            "asset_serial": "aaad",
                            "agent_version": "1.0",
                            "business_group": "a",
                            "status": 1,
                            "last_update": "2021-08-17 15:21:14",
                            "id": "60f66fc45c900a3bd0a57a4f"
                        },
                        "local": 0,
                        "meta_info": {
                            "hist": 0,
                            "content_type": "image",
                            "measurement": []
                        },
                        "part_record": [
                            {
                                "part": 2,
                                "size": 598807,
                                "status": 0,
                                "md5": "d41d8cd98f00b204e9800998ecf8427e"
                            },
                            {
                                "part": 3,
                                "size": 598807,
                                "status": 0,
                                "md5": "d41d8cd98f00b204e9800998ecf8427e"
                            }
                        ],
                        "time": {
                            "$date": 1590677845515
                        }
                    }
                ]
            }
        }
       """
        pass

    def get(self, request):
        query_dict = request.GET.dict()
        page, per_page = page_get(request.GET)

        query = {'is_deleted': 0}
        if query_dict.get('name', None):
            query['name__contains'] = query_dict.get('name')
        query['status'] = query_dict.get('status', 0)
        return MongoJsonResponse(
            ok(mongoengine_page(FileStorage, query, page, per_page, ('part_record',),
                                map=to_dict(exclude=['client_info', 'groups', 'single_group', 'channel_name',
                                                     'channel_layer_alias', 'is_anonymous']))))


class FileStorageDetailView(APIDetailView):
    """
        @api {GET} api/attachments/file/:id 获取文件详情
        @apiVersion 1.0.0
        @apiName get file detail
        @apiGroup Attachment
        @apiDescription 获取文件详情

        @apiParam {String}  id id

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
            {
            "code": 200,
            "msg": "ok",
            "data": {
                "_id": {
                    "$oid": "5ecf60d5bd3a164466160b2a"
                },
                "name": "asdf",
                "upload_id": "62dd1dd5040408c",
                "parts": 3,
                "md5": "e534e9c714d4059c123d7b3ab3cf13b1",
                "size": 123413,
                "status": 1,
                "type": 2,
                "folder": "common",
                "meta_info": {
                    "hist": 0,
                    "content_type": "image",
                    "measurement": []
                },
                "part_record": [
                    {
                        "part": 2,
                        "size": 598807,
                        "status": 0,
                        "md5": "d41d8cd98f00b204e9800998ecf8427e"
                    },
                    {
                        "part": 3,
                        "size": 598807,
                        "status": 0,
                        "md5": "d41d8cd98f00b204e9800998ecf8427e"
                    }
                ],
                "time": {
                    "$date": 1590677845515
                }
            }
        }
        """
    document = FileStorage

    def delete(self, request, id):
        """
        @api {DELETE} api/attachments/file/:id 删除文件
        @apiVersion 1.0.0
        @apiName file delete
        @apiGroup Attachment
        @apiDescription 删除文件

        @apiParam {String}  id id

        @apiSuccessExample Response-Success:
        HTTP 1.1/ 200K
        {
            "code": 200,
            "msg": "ok"
        }
        """
        file = FileStorage.objects(id=id, is_deleted=0).exclude('part_record').first()
        if not file:
            return JsonResponse(ERROR.NOT_FOUND_404)
        code = CodeData.objects(is_deleted=0, source=id).first()
        if code:
            return JsonResponse(
                ERROR.DELETE_REFERENCE_ERROR('文件被创建于 {} 的代码仓库作为源文件引用，无法删除'.format(code.date_created)))
        code = CodeData.objects(is_deleted=0, compiled=id).first()
        if code:
            return JsonResponse(
                ERROR.DELETE_REFERENCE_ERROR('文件被创建于 {} 的代码仓库作为编译文件引用，无法删除'.format(code.date_created)))

        update_op = {'set__is_deleted': 1}
        FileStorage.objects(id=id).update_one(**update_op)
        try:
            payload = {
                'objectKey': file.object_key,
            }
            delete(payload)
        except Exception as e:
            logger.error(e)
            return JsonResponse(ok())

        return JsonResponse(ok())
