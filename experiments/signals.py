from django.dispatch import Signal

user_enrolled = Signal(providing_args=['experiment', 'alternative', 'user', 'session'])
