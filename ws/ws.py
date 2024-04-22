from concurrent.futures.thread import ThreadPoolExecutor

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

default_channel_layer = get_channel_layer('default')
executor = ThreadPoolExecutor(max_workers=20)


def send_group_message(message=None, group_name='root', alias='default', action=None):
    if message is None:
        message = {}
    if alias == 'default':
        channel_layer = default_channel_layer
    else:
        channel_layer = get_channel_layer(alias)
    message = {
        'type': 'on_action',
        'message': message if action is None else action(message)
    }
    async_to_sync(channel_layer.group_send)(group_name, message)
