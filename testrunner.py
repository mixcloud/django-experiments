import os
import sys

from django.conf import settings

import django

def runtests():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, test_dir)

    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=('django.contrib.auth',
                        'django.contrib.contenttypes',
                        'django.contrib.sessions',
                        'django.contrib.admin',
                        'experiments',),
        ROOT_URLCONF='experiments.urls',
    )
    django.setup()


    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, failfast=False)
    failures = test_runner.run_tests(['experiments', ])
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
