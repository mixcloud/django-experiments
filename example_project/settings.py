import os.path
import sys

# Experiments Settings
EXPERIMENTS_GOALS = (
    'page_goal',
    'js_goal',
    'cookie_goal',
)

EXPERIMENTS_AUTO_CREATE = True

EXPERIMENTS_SWITCH_AUTO_CREATE = True
EXPERIMENTS_SWITCH_AUTO_DELETE = True

EXPERIMENTS_SWITCH_LABEL = "Experiment: %s"

EXPERIMENTS_VERIFY_HUMAN = True  # Careful with this setting, if it is toggled
                                 # then participant counters will not increment
                                 # accordingly

# Redis Settings
EXPERIMENTS_REDIS_HOST = 'localhost'
EXPERIMENTS_REDIS_PORT = 6379
EXPERIMENTS_REDIS_DB = 0


# Media Settings
STATIC_URL = '/static/'

# Other settings
# Django settings for example_project project.
NEXUS_MEDIA_PREFIX = '/nexus/media/'

DEBUG = True
TEMPLATE_DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

INTERNAL_IPS = ('127.0.0.1',)

MANAGERS = ADMINS

PROJECT_ROOT = os.path.dirname(__file__)

sys.path.insert(0, os.path.abspath(os.path.join(PROJECT_ROOT, '..')))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'experiments.db',   # Or path to database file if using sqlite3.
        'USER': '',                 # Not used with sqlite3.
        'PASSWORD': '',             # Not used with sqlite3.
        'HOST': '',                 # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                 # Set to empty string for default. Not used with sqlite3.
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:6379',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'gfjo;2r3l;hjropjf30j3fl;m234nc9p;o2mnpfnpfj'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'waffle.middleware.WaffleMiddleware',
    'experiments.middleware.ExperimentsMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'nexus',
    'waffle',
    'experiments',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
)
