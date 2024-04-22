import logging
from sacentral.settings import SYSLOG

syslog = logging.getLogger('syslog-thusa')
syslog.setLevel(logging.INFO)
try:
    from rfc5424logging import Rfc5424SysLogHandler
    sh = Rfc5424SysLogHandler(address=(SYSLOG.get('HOST'), SYSLOG.get('PORT')), enterprise_id='thusa')
    syslog.addHandler(sh)
except Exception:
    import traceback
    traceback.print_exc()
