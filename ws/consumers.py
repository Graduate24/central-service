import json
from urllib import parse

from channels.generic.websocket import AsyncWebsocketConsumer

from utils.log import logger
from utils.mongo_json import dumps
from ws.handlers import ClientOnlineHandler
from ws.models import OnlineClient


class WsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get('query_string', None)
        if not query_string:
            logger.info('no machine code found, abort connect')
            return
        url = self.scope['path'] + '?' + str(query_string, encoding='utf8')
        query = dict(parse.parse_qsl(parse.urlsplit(url).query))
        # 加入root组，所有链接端
        await self.channel_layer.group_add(
            'root',
            self.channel_name
        )
        machine_code = query['code']
        groups = ['root']
        online_client = OnlineClient()
        client_identifier = self.scope['client'][0] + '-' + str(self.scope['client'][1])
        logger.info('connect from: {}, query_string:{}, add to root'.format(self.channel_name, query_string))
        await self.channel_layer.group_add(
            machine_code,
            self.channel_name
        )

        groups.append(machine_code)
        online_client.single_group = machine_code
        online_client.channel_name = self.channel_name
        online_client.groups = groups
        online_client.channel_layer_alias = self.channel_layer_alias
        online_client.client = self.scope['client']
        online_client.is_random_gen = query['isRandomGen']
        online_client.machine_code = machine_code
        await online_client.connect()

        logger.info('connect from: {}, add to {}'.format(client_identifier, machine_code))
        await self.accept()
        # init host info
        logger.info('init host info action')
        await self.send(text_data=dumps({'action': 'hostinfo', 'data': {}}))

    async def disconnect(self, close_code):
        # 离开Root组
        await self.channel_layer.group_discard(
            'root',
            self.channel_name
        )

        query_string = self.scope.get('query_string', None)
        url = self.scope['path'] + '?' + str(query_string, encoding='utf8')
        query = dict(parse.parse_qsl(parse.urlsplit(url).query))
        machine_code = query['code']
        client_identifier = self.scope['client'][0] + '-' + str(self.scope['client'][1])
        await self.channel_layer.group_discard(
            machine_code,
            self.channel_name
        )
        await OnlineClient.disconnect(self.channel_name)
        logger.info('disconnect from : {},discard {}'.format(client_identifier, machine_code))

        # Receive message from WebSocket

    async def receive(self, text_data):
        single_group_identifier = self.scope['client'][0] + ':' + str(self.scope['client'][1])
        query_string = self.scope.get('query_string', None)
        logger.info(
            'receive from: {}, message: {}, query_string:{}'.format(single_group_identifier, text_data, query_string))
        url = self.scope['path'] + '?' + str(query_string, encoding='utf8')
        query = dict(parse.parse_qsl(parse.urlsplit(url).query))
        machine_code = query['code']

        # await self.channel_layer.group_send(
        #     single_group_identifier,
        #     {
        #         'type': 'on_message',
        #         'message': text_data
        #     }
        # )
        text_data_json = json.loads(text_data) if not isinstance(text_data, dict) else text_data
        func = text_data_json.get('action', None)
        if func:
            payload = text_data_json.get('data', {})
            extra = {'from_client': single_group_identifier, 'machine_code': machine_code}
            logger.info('------- action:{} , payload:{} '.format(func, payload))
            ret = switch_action(func)(payload, **extra)
            if not ret:
                return
            await self.send(text_data=dumps(ret))

    # Receive message from room group

    async def on_message(self, event):
        message = event['message']
        try:
            text_data_json = json.loads(message) if not isinstance(message, dict) else message
            func = text_data_json['action']
            payload = text_data_json.get('payload', {})
            logger.info('switch function: {}'.format(func))
            ret = await switch_action(func)(payload)
            ret = {'code': 200, 'msg': 'ok', 'data': ret}
            await self.send(text_data=dumps(ret))
        except Exception as e:
            await self.send(text_data=json.dumps({'code': 500, 'msg': str(e)}))

    async def on_action(self, event):
        message = event['message']
        try:
            await self.send(text_data=dumps(message))
        except Exception as e:
            logger.info(str(e))


def switch_action(fun):
    async def default(x):
        return {'code': 404, 'msg': 'action not found'}

    return {
        'heartbeat': ClientOnlineHandler.online_client_async,
        'objectCreate': ClientOnlineHandler.objectCreate,
        'hostInfo': OnlineClient.host_info,
        'batchEvent': ClientOnlineHandler.batchEvent,
        'fullBatchEvent': ClientOnlineHandler.fullBatchEvent
    }.get(fun, default)
