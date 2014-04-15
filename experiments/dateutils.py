import calendar
from datetime import datetime

from django.conf import settings

USE_TZ = getattr(settings, 'USE_TZ', False)
if USE_TZ:
    from django.utils.timezone import now
else:
    now = datetime.now


def fix_awareness(value):
    tz_aware_value = value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None
    if USE_TZ and not tz_aware_value:
        from django.utils.timezone import get_current_timezone
        return value.replace(tzinfo=get_current_timezone())
    elif not USE_TZ and tz_aware_value:
        return value.replace(tzinfo=None)
    else:
        return value


def timestamp_from_datetime(dt):
    if dt is None:
        return None
    return calendar.timegm(dt.utctimetuple())


def datetime_from_timestamp(ts):
    if ts is None:
        return None
    return datetime.utcfromtimestamp(ts)
