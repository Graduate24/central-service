import traceback

from asgiref.sync import sync_to_async
from bson import ObjectId
from django.utils import timezone
from mongoengine import *
from mongoengine_pagination import DocumentPro

from authentication.docs import DjangoUser
from utils.log import logger


class Firmware(EmbeddedDocument):
    manufacturer = StringField()
    name = StringField()
    version = StringField()
    description = StringField()
    releaseDate = StringField()


class Baseboard(EmbeddedDocument):
    manufacturer = StringField()
    model = StringField()
    version = StringField()
    serialNumber = StringField()


class CentralProcessor(EmbeddedDocument):
    physicalProcessorCount = IntField()
    logicalProcessorCount = IntField()
    identifier = StringField()
    processorId = StringField()


class Memory(EmbeddedDocument):
    available = StringField()
    total = StringField()
    swapUsed = StringField()
    swapTotal = StringField()


class OperateSystem(EmbeddedDocument):
    family = StringField()
    manufacturer = StringField()
    version = StringField()
    codeName = StringField()
    buildNumber = StringField()


class NetworkInterface(EmbeddedDocument):
    name = StringField()
    displayName = StringField()
    macAddr = StringField()
    mtu = IntField()
    speed = StringField()
    ipv4addr = ListField(StringField())
    ipv6addr = ListField(StringField())
    bytesRecv = LongField()
    bytesSent = LongField()
    packetRecv = LongField()
    packetSent = LongField()


class NetworkInfo(EmbeddedDocument):
    hostname = StringField()
    domainName = StringField()
    dnsServers = ListField(StringField())
    ipv4DefaultGateway = StringField()
    ipv6DefaultGateway = StringField()
    networkInterfaces = EmbeddedDocumentListField(NetworkInterface)


class FileSystem(EmbeddedDocument):
    name = StringField()
    type = StringField()
    usable = StringField()
    usableBytes = LongField()
    totalSpace = StringField()
    totalSpaceBytes = LongField()
    freePercentage = StringField()
    volume = StringField()
    logicalVolume = StringField()
    mount = StringField()


class FileSystemInfo(EmbeddedDocument):
    total = StringField()
    usable = StringField()
    totalBytes = LongField()
    usableBytes = LongField()
    fileSystem = EmbeddedDocumentListField(FileSystem)


class SystemInfo(EmbeddedDocument):
    manufacturer = StringField()
    model = StringField()
    serialNumber = StringField()
    firmware = EmbeddedDocumentField(Firmware)
    baseboard = EmbeddedDocumentField(Baseboard)
    central_processor = EmbeddedDocumentField(CentralProcessor)
    memory = EmbeddedDocumentField(Memory)
    operate_system = EmbeddedDocumentField(OperateSystem)
    network_info = EmbeddedDocumentField(NetworkInfo)
    filesystem_info = EmbeddedDocumentField(FileSystemInfo)


class OnlineClient(DocumentPro):
    name = StringField()
    groups = ListField(StringField(max_length=50, required=True))
    single_group = StringField(max_length=50, required=True)
    channel_name = StringField(max_length=100, required=True)
    channel_layer_alias = StringField(max_length=100, required=True)
    is_anonymous = IntField(required=True, default=0)
    online_time = DateTimeField(required=True, default=timezone.now)
    client = ListField(required=True)
    machine_code = StringField(required=True, unique=True)
    is_random_gen = IntField(required=True)
    tags = ListField(StringField(max_length=30), default=[])
    location = StringField()
    asset_serial = StringField()
    client_info = EmbeddedDocumentField(SystemInfo)
    agent_version = StringField()
    business_group = StringField()
    # 状态 0,离线，1,在线
    status = IntField(required=True, default=1)
    last_update = DateTimeField(required=True, default=timezone.now)

    @staticmethod
    def only_fields():
        return 'name', 'online_time', 'client', 'machine_code', 'tags', 'location', 'asset_serial', 'agent_version', \
               'status', 'last_update', 'business_group'

    @staticmethod
    def pre_match(query_dict):
        match = {}
        if query_dict.get('name', None):
            match['name'] = {'$regex': '^' + query_dict.get('name')}
        if query_dict.get('business_group', None):
            match['business_group'] = query_dict.get('business_group')
        if query_dict.get('machine_code', None):
            match['machine_code'] = {'$regex': '^' + query_dict.get('machine_code')}
        if query_dict.get('location', None):
            match['location'] = query_dict.get('location')
        if query_dict.get('asset_serial', None):
            match['asset_serial'] = {'$regex': '^' + query_dict.get('asset_serial')}
        if query_dict.get('status', None):
            match['status'] = int(query_dict.get('status'))
        if query_dict.get('tags', None):
            match['tags'] = {'$in': query_dict.get('tags')}
        time_query = {}
        if query_dict.get('last_update_from', None):
            from datetime import datetime
            start_from = datetime.strptime(query_dict.get('last_update_from'), '%Y-%m-%d %H:%M:%S')
            time_query['$gte'] = start_from
        if query_dict.get('last_update_to', None):
            from datetime import datetime
            start_to = datetime.strptime(query_dict.get('last_update_to'), '%Y-%m-%d %H:%M:%S')
            time_query['$lte'] = start_to
        if time_query:
            match['last_update'] = time_query
        if query_dict.get('id', None):
            match['_id'] = ObjectId(query_dict.get('id'))
        return {'$match': match}

    @sync_to_async
    def connect(self):
        origin = OnlineClient.objects(machine_code=self.machine_code).first()
        if not origin:
            self.save()
        else:
            origin.single_group = self.single_group
            origin.channel_name = self.channel_name
            origin.groups = self.groups
            origin.channel_layer_alias = self.channel_layer_alias
            origin.client = self.client
            origin.is_random_gen = self.is_random_gen
            origin.machine_code = self.machine_code
            origin.save()

    @staticmethod
    @sync_to_async
    def disconnect(channel_name):
        OnlineClient.objects(channel_name=channel_name).update_one(set__status=0)

    @staticmethod
    def projects(keys, is_include=1):
        project = {}
        for key in keys:
            project[key] = is_include

        return {'$project': project}

    @staticmethod
    def host_info(payload, **kwargs):
        """
        {
          'systemInfo':
            {
              'manufacturer': 'LG Electronics',
              'model': '17Z90N-V.AA76C (version: 0.1)',
              'serialNumber': 'unknown',
              'firmware':
                {'manufacturer': 'Phoenix Technologies Ltd.',
                'name': 'unknown',
                'description': 'dmi:bvnPhoenixTechnologiesLtd.:bvrC2ZE0160X64:',
                'version': 'C2ZE0160 X64',
                'releaseDate': '04/07/2020'
                },
              'baseboard':
                {'manufacturer': 'LG Electronics',
                'model': '17Z90N',
                'version': 'FAB1',
                'serialNumber': ''
                },
              'machineCode':
                {'isRandomGen': False, 'code': '7e204f477ea640fb91beb71daf1f2c62'}},
            'centralProcessorInfo':
                {
                'physicalProcessorCount': 4,
                'logicalProcessorCount': 8,
                'identifier': 'Intel64 Family 6 Model 126 Stepping 5',
                'processorId': 'AFC1FBFF007006E5'
                },
            'memoryInfo':
                {'available': '3.2 GiB',
                'total': '15.3 GiB',
                'swapUsed': '55.5 MiB',
                'swapTotal': '7.6 GiB'
                }
            }
        """
        try:
            system = payload['systemInfo']
            firmware_info = system['firmware']
            baseboard_info = system['baseboard']
            machine_code = system['machineCode']
            central_processor_info = payload['centralProcessorInfo']
            memory_info = payload['memoryInfo']
            os_info = payload['operateSystemInfo']
            network_info = payload['networkInfo']
            filesystem_info = payload['fileSystemInfo']

            system_info = SystemInfo()
            system_info.manufacturer = system['manufacturer']
            system_info.model = system['model']
            system_info.serialNumber = system['serialNumber']

            firmware = Firmware(**firmware_info)
            baseboard = Baseboard(**baseboard_info)
            central_processor = CentralProcessor(**central_processor_info)
            memory = Memory(**memory_info)
            operate_system = OperateSystem(**os_info)
            network = NetworkInfo(**network_info)
            filesystem = FileSystemInfo(**filesystem_info)

            system_info.firmware = firmware
            system_info.baseboard = baseboard
            system_info.central_processor = central_processor
            system_info.memory = memory
            system_info.operate_system = operate_system
            system_info.network_info = network
            system_info.filesystem_info = filesystem
            logger.info('update client:{} host info'.format(machine_code['code']))
            name = system.get('manufacturer', '') + system.get('model', '')
            OnlineClient.objects(machine_code=machine_code['code']).update_one(set__client_info=system_info,
                                                                               set__last_update=timezone.now(),
                                                                               set__status=1,
                                                                               set__name=name)
        except Exception:
            traceback.print_exc()


class EventMessage(Document):
    user = EmbeddedDocumentField(DjangoUser)
    # 事件类别
    # 1 上线；2 下线;
    category = IntField(required=True, default=0)
    source_id = StringField()
    source_type = StringField()
    message = StringField()
    date = DateTimeField(required=True, default=timezone.now)

    @sync_to_async
    def user_online_event(self, user_pk):
        self.user = DjangoUser(pk=user_pk)
        self.category = 1
        self.message = '上线'
        self.save()

    @sync_to_async
    def user_offline_event(self, user_pk):
        self.user = DjangoUser(pk=user_pk)
        self.category = 2
        self.message = '下线'
        self.save()
