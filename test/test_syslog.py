import logging
from rfc5424logging import Rfc5424SysLogHandler

syslog = logging.getLogger('syslog-thusa')
syslog.setLevel(logging.INFO)

sh = Rfc5424SysLogHandler(address=('10.0.0.1', 514))
syslog.addHandler(sh)

extra = {
    'structured_data': {
        'sd_id2': {'key2': 'value2', 'key3': 'value3'}
    }
}

syslog.info('This is an interesting message', extra=extra)
