from django.dispatch import Signal

user_enrolled = Signal()
user_enrolled.__doc__ = """
sends arguments: 'experiment', 'alternative', 'user', 'session'
"""
