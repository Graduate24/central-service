import os
import shutil
import time

from asgiref.sync import sync_to_async

from analysis.models import RuleTemplate, ChangeLog
from analysis.workflow_handlers import *
from sacentral.settings import CODE_ROOT
from utils.file_server import upload, digest_hash
from utils.log import logger
from utils.response_code import ok


class ClientOnlineHandler:

    @staticmethod
    def online_client(payload=None):
        """
        在线
        :param payload:
        :return:
        """
        return {'online_client': payload}

    @staticmethod
    @sync_to_async
    def online_client_async(payload=None):
        return ClientOnlineHandler.online_client(payload)

    @staticmethod
    def objectCreate(payload=None):
        # create object action. send analysis task to engine.
        # {'objectKey','watchPath','size', 'md5'}
        logger.info("object create action.send analysis task to engine")
        # 1. create file storage.
        fs = file_archive(payload)
        # 2. add code database.
        code_data = post_codedata(fs)
        # 3. init workflow
        rule_template = RuleTemplate.objects(is_deleted=0, status=1, default=1).first()
        if not rule_template:
            logger.info('no default rule template found, abort analysis')
            return
        # TODO create a task before workflow
        workflow = init_workflow(WorkflowType.compile_sa_ml.value, code_data, payload.get('from_client', ''),
                                 rule_template)
        handler = next_handler(workflow)
        if handler:
            handler.handle()
        return ok()

    @staticmethod
    def batchEvent(payload=None, **kwargs):
        """
        [
            {
                "pathIdentity": {
                    "dirPath": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo",
                    "normalizeDirPath": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo"
                },
                "eventData": [
                    {
                        "objectKey": "watch/ed2ec2cf13eb7ad58c8fcb0111b94bdd/web.xml",
                        "filePath": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo/WEB-INF/web.xml",
                        "size": 1204,
                        "md5": "ed2ec2cf13eb7ad58c8fcb0111b94bdd",
                        "monitorDir": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo",
                        "event": "init"
                    }
                ]
            }
        ]
        """
        logger.info("batch event")

        logger.info(kwargs)
        machine_code = kwargs.get('machine_code')
        client = OnlineClient.objects(machine_code=machine_code).exclude('client_info').first()
        if not client:
            logger.info('no monitor info found. abort')
            return

        for p in payload:
            t = time.time()
            version = str(int(round(t * 1000)))
            path_identity = p.get('pathIdentity')
            monitor_path = path_identity.get('dirPath')
            norm_monitor_path = path_identity.get('normalizeDirPath')
            event_data = p.get('eventData')

            # 1. find project of latest version with same monitor path
            last_version = MonitorProject.objects(monitor=client, is_deleted=0,
                                                  monitor_path=monitor_path).order_by('-version').first()
            project = None
            if not last_version:
                pfs = []
                for e in event_data:
                    file_path = e.get('filePath')
                    object_key = e.get('objectKey', None)
                    size = e.get('size', None)
                    md5 = e.get('md5', None)
                    event = e.get('event')
                    if event != 'objectDelete':
                        fs = FileStorage(name=ntpath.basename(file_path), size=size, md5=md5,
                                         object_key=object_key, status=0, meta_info=FileMeta(), uploader=client,
                                         version=version, source_path=file_path)
                        fs.save()
                        pfs.append(fs)

                first_version = MonitorProject.objects(monitor=client, monitor_path=monitor_path,
                                                       name=ntpath.basename(norm_monitor_path), version=version,
                                                       files=[f.id for f in pfs])
                first_version.save()
                project = first_version
            else:
                last_version_files = last_version.files
                last_version_id = last_version.version

                # delete files in event
                del_file_paths = [e.get('filePath') for e in event_data]
                files_after_delete = [f for f in last_version_files if not del_file_paths.__contains__(f.source_path)]

                changelogs = [create_changelogs_with_event(e, client, version) for e in event_data]
                new_files = new_files_from_changelog(changelogs)
                copied_files = [copy_file_with_new_version(f, version) for f in files_after_delete]
                pfs = copied_files + new_files

                new_version = MonitorProject(monitor=client, monitor_path=monitor_path,
                                             name=ntpath.basename(norm_monitor_path), version=version,
                                             files=[f.id for f in pfs], change_log=changelogs)
                new_version.save()
                project = new_version

            # archive zip file
            archive_and_start_task(project, pfs, norm_monitor_path, kwargs.get('from_client', ''))
            return ok()

    @staticmethod
    def fullBatchEvent(payload=None, **kwargs):
        """
        [
            {
                "pathIdentity": {
                    "dirPath": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo",
                    "normalizeDirPath": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo"
                },
                "eventData": [
                    {
                        "objectKey": "watch/ed2ec2cf13eb7ad58c8fcb0111b94bdd/web.xml",
                        "filePath": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo/WEB-INF/web.xml",
                        "size": 1204,
                        "md5": "ed2ec2cf13eb7ad58c8fcb0111b94bdd",
                        "monitorDir": "/home/ran/download/apache-tomcat-10.0.4/webapps/jsp-demo",
                        "event": "init"
                    }
                ]
            }
        ]
        """
        logger.info("full batch event")

        logger.info(kwargs)
        machine_code = kwargs.get('machine_code')
        client = OnlineClient.objects(machine_code=machine_code).exclude('client_info').first()

        for p in payload:
            path_identity = p.get('pathIdentity')
            monitor_path = path_identity.get('dirPath')
            norm_monitor_path = path_identity.get('normalizeDirPath')
            event_data = p.get('eventData')
            t = time.time()
            version = str(int(round(t * 1000)))
            pfs = []
            for e in event_data:
                file_path = e.get('filePath')
                object_key = e.get('objectKey')
                size = e.get('size')
                md5 = e.get('md5')
                logger.info('file_path:{}, basename:{}'.format(file_path, ntpath.basename(file_path)))
                fs = FileStorage(name=ntpath.basename(file_path), size=size, md5=md5,
                                 object_key=object_key, status=0, meta_info=FileMeta(), uploader=client,
                                 version=version, source_path=file_path)
                fs.save()
                pfs.append(fs)
            logger.info('norm_monitor_path:{}, ntpath.basename(norm_monitor_path):{}'.format(norm_monitor_path,
                                                                                             ntpath.basename(
                                                                                                 norm_monitor_path)))
            project = MonitorProject(monitor=client, name=ntpath.basename(norm_monitor_path),
                                     monitor_path=monitor_path, version=version, files=[f.id for f in pfs])
            project.save()
            archive_and_start_task(project, pfs, norm_monitor_path, kwargs.get('from_client', ''))
            return ok()


def create_file_with_event(e, client, version):
    file_path = e.get('filePath')
    object_key = e.get('objectKey', None)
    size = e.get('size', None)
    md5 = e.get('md5', None)

    fs = FileStorage(name=ntpath.basename(file_path), size=size, md5=md5,
                     object_key=object_key, status=0, meta_info=FileMeta(), uploader=client,
                     version=version, source_path=file_path)
    fs.save()
    return fs


def create_changelogs_with_event(e, client, version):
    file_path = e.get('filePath')
    object_key = e.get('objectKey', None)
    size = e.get('size', None)
    md5 = e.get('md5', None)
    event = e.get('event')

    cl = ChangeLog(path=file_path, event=event, md5=md5)

    if event != 'objectDelete':
        fs = FileStorage(name=ntpath.basename(file_path), size=size, md5=md5,
                         object_key=object_key, status=0, meta_info=FileMeta(), uploader=client,
                         version=version, source_path=file_path)
        fs.save()
        cl.file = fs

    cl.save()
    return cl


def new_files_from_changelog(changelogs):
    return [c.file for c in changelogs if c.event != 'objectDelete']


def copy_file_with_new_version(old_file, version):
    fs = FileStorage(version=version, name=old_file.name, upload_id=old_file.upload_id, parts=old_file.parts,
                     md5=old_file.md5, size=old_file.size, status=old_file.status, type=old_file.type,
                     folder=old_file.folder, local=old_file.local, meta_info=old_file.meta_info,
                     part_record=old_file.part_record, object_key=old_file.object_key, source_path=old_file.source_path)
    fs.save()
    return fs


def archive_and_start_task(project, pfs, norm_monitor_path, from_client=''):
    # archive zip file
    dir_name = ntpath.basename(norm_monitor_path)
    logger.info('norm_monitor_path:{}, dir_name:{}'.format(norm_monitor_path, dir_name))
    path = os.path.join(CODE_ROOT, str(project.id), project.version, dir_name)
    if not os.path.exists(path):
        os.makedirs(path)
    for f in pfs:
        target_path = os.path.normpath(
            (path + os.path.sep + f.source_path[len(norm_monitor_path):].replace(ntpath.sep, os.sep)))
        if os.path.basename(target_path).startswith('.'):
            continue
        par = os.path.dirname(target_path)
        if not os.path.exists(par):
            os.makedirs(par)
        logger.info('-- download {}'.format(target_path))
        f.download(target_path)
    shutil.make_archive(path, 'zip', path)
    zip_file = path + '.zip'
    md5 = digest_hash(zip_file)
    ex = FileStorage.objects(is_deleted=0, status=0, md5=md5).first()
    if ex:
        fs = FileStorage(name=ntpath.basename(zip_file), size=ex.size, md5=md5,
                         object_key=ex.object_key, status=0, meta_info=ex.meta_info, uploader=ex.uploader)
        fs.save()
    else:
        name, size, parts, md5, object_key = upload(zip_file, 'project')
        fs = FileStorage(name=name, size=size, md5=md5, parts=parts,
                         object_key=object_key, status=0, meta_info=FileMeta(), local=1)
        fs.save()

    # 2. add code database.
    code_data = post_codedata(fs, project)
    # 3. init workflow
    rule_template = RuleTemplate.objects(is_deleted=0, status=1, default=1).first()
    if not rule_template:
        logger.info('no default rule template found, abort analysis')
        return

    workflow = init_workflow(WorkflowType.compile_sa_ml.value, code_data, project.monitor.name,
                             rule_template, project, project.monitor)
    handler = next_handler(workflow)
    if handler:
        handler.handle()
