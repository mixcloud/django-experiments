from django.conf import settings

USE_TZ = getattr(settings, 'USE_TZ', False)
if USE_TZ:
    from django.utils.timezone import now
else:
    from datetime import datetime
    now = datetime.now
