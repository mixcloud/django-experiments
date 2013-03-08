from django.conf import settings

USE_TZ = getattr(settings, 'USE_TZ', False)
if USE_TZ:
    from django.utils.timezone import now
else:
    from datetime import datetime
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
