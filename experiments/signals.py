import django.dispatch


user_enrolled = django.dispatch.Signal(providing_args=['experiment', 'alternative', 'user', 'session'])
