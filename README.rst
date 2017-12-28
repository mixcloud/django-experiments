Django-Experiments
==================

.. image:: https://codeship.com/projects/1c7cb7a0-caa8-0130-f2cb-36bd8b1bab14/status?branch=master
   :target: https://codeship.com/projects/4846

Django-Experiments is an AB Testing Framework for Django.

It is possible to set up an experiment through template tags only.
Through the Django admin you can monitor and control experiment progress.

If you don't know what AB testing is, check out `wikipedia <http://en.wikipedia.org/wiki/A/B_testing>`_.


This Fork
---------

See Changelog from ``1.3.0`` onwards.


Forked from: https://github.com/mixcloud/django-experiments


Installation
------------

Django-Experiments is best installed via pip:

::

    pip install consumeraffairs-django-experiments

This should download django-experiments and any dependencies. If downloading from the repo,
pip is still the recommended way to install dependencies:

::

    pip install -e .

Dependencies
------------
- `Django <https://github.com/django/django/>`_
- `Redis <http://redis.io/>`_
- `django-jsonfield <https://github.com/dmkoch/django-jsonfield/>`_
- `django-modeldict <https://github.com/disqus/django-modeldict>`_

(Detailed list in setup.py)

It also requires 'django.contrib.humanize' to be in INSTALLED_APPS.

Usage
-----

The example project is a good place to get started and have a play.
Results are stored in redis and displayed in the Django admin. The key
components of this framework are: the experiments, alternatives and
goals.


Configuration
~~~~~~~~~~~~~

Before you can start configuring django-experiments, you must ensure
you have a redis server up and running. See `redis.io <http://redis.io/>`_ for downloads and documentation.

This is a quick guide to configuring your settings file to the bare minimum.
First, add the relevant settings for your redis server (we run it as localhost):

::

    #Example Redis Settings
    EXPERIMENTS_REDIS_HOST = 'localhost'
    EXPERIMENTS_REDIS_PORT = 6379
    EXPERIMENTS_REDIS_DB = 0

Next, activate the apps by adding them to your INSTALLED_APPS:

::

    #Installed Apps
    INSTALLED_APPS = [
        ...
        'django.contrib.admin',
        'django.contrib.humanize',
        'experiments',
    ]

Include 'django.contrib.humanize' as above if not already included.

Include the app URLconf in your urls.py file:

    url(r'experiments/', include('experiments.urls')),

We haven't configured our goals yet, we'll do that in a bit. Please ensure
you have correctly configured your STATIC_URL setting.

OPTIONAL:
If you want to use the built in retention goals you will need to include the retention middleware:

::

    MIDDLEWARE_CLASSES [
        ...
        'experiments.middleware.ConfirmHumanMiddleware',
        'experiments.middleware.ExperimentsRetentionMiddleware',
    ]

*Note, more configuration options are detailed below.*


Note: `ConfirmHumanMiddleware` is optional, not needed it you plan on running only template-based tests.
If used, it should come after these classes:

::
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.SessionAuthenticationMiddleware',



Jinja2:

If using Jinja2 template engine (tested with ``django_jinja``), add the extension to enable template tags:

::

    TEMPLATES = [
        {
            'BACKEND': 'django_jinja.backend.Jinja2',
            'OPTIONS': {
                'extensions': [
                    ...
                    'experiments.templatetags.experiments.ExperimentsExtension',
                ],
                ...
            },
        },
    ]


Experiments and Alternatives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The experiment can be manually created in your Django admin. Adding alternatives must currently be done in template tags or by calling the relevant code, as described below.

An experiment allows you to test the effect of various design
alternatives on user interaction. Django-Experiments is designed to work
from within django templates, to make it easier for designers. We begin
by loading our module (unless using Jinja2):

::

    {% load experiments %}

and we then define our first experiment and alternative, using the
following syntax:

::

    {% experiment EXPERIMENT ALTERNATIVE %}

We are going to run an experiment called “register\_text” to see what
registration link text causes more users to complete the registration
process. Our first alternative must always be the “control” alternative.
This is our fallback if the experiment is disabled.

::

    {% experiment register_text control %}
        <a href = "register.html">Register now.</a>
    {% endexperiment %}

So while the experiment is disabled, users will see a register link
saying “Register now”. Let’s define another, more polite alternative:

::

    {% experiment register_text polite %}
        <a href = "register.html">Please register!</a>
    {% endexperiment %}

While experiment is disabled, users will still see the “control”
alternative, and their registration link will say “Register now”. When
the experiment is enabled, users will be randomly assigned to each
alternative. This information is stored in the enrollment, a unique
combination of the user, the experiment and which alternative they are
assigned to.

Make sure the experiment tag has access to the request object (not an
issue for regular templates but you might have to manually add it
inside an inclusion tag) or it will silently fail to work.

The experiment_enroll assignment tag can also be used (note that it
takes strings or variables unlike the older experiment tag):

::

     {% experiment_enroll "experiment_name" "alternative1" "alternative2" as assigned_alternative %}
     {% if assigned_alternative == "alternative1" or assigned_alternative == "alternative2" %}
        <a href = "register.html">Please register!</a>
     {% else %}
        <a href = "register.html">Register now.</a>
     {% endif %}

You can also enroll users in experiments and find out what alternative they
are part of from python. To enroll a user in an experiment and show a
different result based on the alternative:

::

    from experiments.utils import participant
    alternative = participant(request).enroll('register_text', ['polite'])
    if alternative == 'polite':
        text_to_show = get_polite_text()
    elif alternative == 'control':
        text_to_show = get_normal_text()

If you wish to find out what experiment alternative a user is part of, but not
enroll them if they are not yet a member, you can use get_alternative. This
will return 'control' if the user is not enrolled. 'control' is also returned
for users who are enrolled in the experiment but have been assigned to the
control group - there is no way to differentiate between these cases.

::

    from experiments.utils import participant
    alternative = participant(request).get_alternative('register_text')
    if alternative == 'polite':
        header_text = get_polite_text_summary()
    elif alternative == 'control':
        header_text = get_normal_text_summary()

You can also weight the experiments using the following techniques

::

   alternative = participant(request).enroll('example_test', {'control': 99, 'v2': 1})

::

   {% experiment example_test control 99 %}v2{% endexperiment %}
   {% experiment example_test v2 1 %}v2{% endexperiment %}

By default the participant function expects a HttpRequest object, but you can
alternatively pass a user or session as a keyword argument

::

    participant(user=current_user).get_alternative('register_text')
    participant(session=session).get_alternative('register_text')


\*\ *Experiments will be dynamically created by default if they are
defined in a template but not in the admin. This can be overridden in
settings.*

After creating an experiment either using the Django admin, or through
template tags or code, you must enable the experiment in the Django
admin or manually for it to work.



Goals
~~~~~

Goals allow us to acknowledge when a user hits a certain page. You
specify them in the EXPERIMENTS\_GOALS tuple in your settings. Given the
example above, we would want a goal to be triggered once the user has
completed the registration process.

Add the goal to our EXPERIMENT_GOALS tuple in settings.py:

::

    EXPERIMENTS_GOALS = ("registration",)

Goals are simple strings that uniquely identify a goal.

Our registration successful page will contain the goal template tag:

::

    {% experiment_goal "registration" %}

This will be fired when the user loads the page. This is not the only way of firing a goal. In total, there are four ways of recording goals:

1. **Django Template Tags** (as above).

    ::

        {% experiment_goal "registration" %}

2. **Server side**, using a python function somewhere in your django views:

    ::

        from experiments.utils import participant

        participant(request).goal('registration')

3. **JavaScript onclick**:

    ::

        <button onclick="experiments.goal('registration')">Complete Registration</button>

    (Please note, this requires CSRF authentication. Please see the `Django Docs <https://docs.djangoproject.com/en/1.4/ref/contrib/csrf/#ajax>`_)

4. **Cookies**:

    ::

        <span data-experiments-goal="registration">Complete Registration</span>

Multiple goals can be recorded via the cookie using space as a separator.

The goal is independent from the experiment as many experiments can all
have the same goal. The goals are defined in the settings.py file for
your project.

Retention Goals
~~~~~~~~~~~~~~~

There are two retention goals (VISIT_PRESENT_COUNT_GOAL and VISIT_NOT_PRESENT_COUNT_GOAL that
default to '_retention_present_visits' and '_retention_not_present_visits' respectively). To
use these install the retention middleware. A visit is defined by no page views within
SESSION_LENGTH hours (defaults to 6).

VISIT_PRESENT_COUNT_GOAL does not trigger until the next visit after the user is enrolled and
should be used in most cases. VISIT_NOT_PRESENT_COUNT_GOAL triggers on the first visit after
enrollment and should be used in situations where the user isn't present when being enrolled
(for example when sending an email). Both goals are tracked for all experiments so take care
to only use one when interpreting the results.

Confirming Human
~~~~~~~~~~~~~~~~

The framework can distinguish between humans and bots. By including

::

    {% load experiments %}

    {% experiments_confirm_human %}

at some point in your code (we recommend you put it in your base.html
file), unregistered users will then be confirmed as human. This can be
quickly overridden in settings, but be careful - bots can really mess up
your results!

If you want to customize the confirm human code you can change the
CONFIRM_HUMAN_SESSION_KEY setting and manage setting the value yourself.
Note that you need to call confirm_human on the participant when they
become confirmed as well as setting session[CONFIRM_HUMAN_SESSION_KEY]
equal to True.

Managing Experiments
--------------------

Experiments can be managed in the Django admin (/admin/experiments/experiment/ by
default).

The States
~~~~~~~~~~

**Control** - The experiment is essentially disabled. All users will see
the control alternative, and no data will be collected.

**Enabled** - The experiment is enabled globally, for all users.


Settings
--------

::

    #Experiment Goals
    EXPERIMENTS_GOALS = ()

    #Auto-create experiment if doesn't exist
    EXPERIMENTS_AUTO_CREATE = True

    #Toggle whether the framework should verify user is human. Be careful.
    EXPERIMENTS_VERIFY_HUMAN = False

    #Example Redis Settings
    EXPERIMENTS_REDIS_HOST = 'localhost'
    EXPERIMENTS_REDIS_PORT = 6379
    EXPERIMENTS_REDIS_DB = 0

See conf.py for other settings


Changelog
---------

1.4.0
~~~~~
 - multisite admin dashboard

1.3.6
~~~~~
 - compatibility improvements of unit tests

1.3.5
~~~~~
 - bugfix for python2

1.3.4
~~~~~
 - bugfix related to auto-create of experiments

1.3.3
~~~~~
 - experiment conditionals
 - ability to create experiments from the admin (though without code ATM)
 - removed South migrations
 - new template tab {% experiment_enrolled_alternative %}

1.3.2
~~~~~
 - added confirm_human middleware

1.3.1
~~~~~
 - added unittests for Jinja2 extension
 - updated user enrolment tag to only enrol in specified alternatives (plus the control)

1.3.0 (withdrawn)
~~~~~~~~~~~~~~~~~
 - fork to ConsumerAffairs
 - added jinja2 support
 - removed some older python version from Tox
 - removed dependency on jQuery, dropped support for IE8

pre-1.3.0 (unreleased)
~~~~~~~~~~~~~~~~~~~~~~
 - Conform to common expectations in `setup.py`:
    - Separate `install_requires` and `tests_require` (not reading from `requirements.txt`)
    - Add trove classifiers including Python and Django supported versions
    - Fix license name (from "MIT license, see LICENSE file" to "MIT")
    - Make `setup.py` ready for Python 3 (read `README.rst` using codecs module)
    - Dropped an irrelevant workaround for ancient Python bugs
 - Add `setup.cfg` to support building of universal wheels (preparing for Python 3)
 - Tox runs `python setup.py test` (honouring both `install_requires` and `tests_require`)
 - Prepared `tox.ini` for Python 3 and Django 1.11 compatibility

1.2.0
~~~~~
 - Add support for Django 1.10 (Thanks to @Kobold)
 - Make requirements.txt more flexible
 - Tox support added for testing on multiple Django Versions (Thanks to @Kobold again!)

1.1.6
~~~~~
 - Change to use django-modeldict-yplan as its maintained
 - Change to use pythons inbuilt unittest and not Django's as its Deprecated)

1.1.5
~~~~~
 - Removing experiment_helpers template tag library since it is no longer used and breaks under Django 1.9 (thanks david12341235)

1.1.4
~~~~~

 - Removing django-jsonfield from requirements.txt (thank you to bustavo) and adding jsonfield

1.1.2
~~~~~

 - Updating migrations
 - Documentation improvements
 - Updating example app

1.1.1
~~~~~

 - Fixing EXPERIMENTS_AUTO_CREATE flag (previously setting it to True did nothing)

1.1.0
~~~~~

 - Nexus is no longer required or used - the standard Django admin for the Experiment model takes over the functionality previously provided by Nexus - NOTE this may have some backwards incompatibilities depending on how you included the media files
 - Promote an experiment to a particular alternative (other than Control) through the admin
 - New experiment_enroll assignment tag (see below)

1.0.0
~~~~~

Bumping version to 1.0.0 because django-experiments is definitely production
ready but also due to backwards incompatible changes that have been merged in.

 - Django 1.7 and 1.8 support (including custom user models)
 - Fixed numerous bugs to do with retention goals - before this update they are not trustworthy. See retention section below for more information.
 - Fixed bug caused by the participant cache on request
 - Fixed bugs related to confirm human and made the functionality pluggable
 - Added "force_alternative" option to participant.enroll (important note: forcing the alternative in a non-random way will generate potentially invalid results)
 - Removal of gargoyle integration and extra "request" parameters to methods that no longer need them such as is_enrolled (BACKWARDS INCOMPATIBLE CHANGE)
 - ExperimentsMiddleware changed to ExperimentsRetentionMiddleware (BACKWARDS INCOMPATIBLE CHANGE)
 - More tests and logging added

0.3.5
~~~~~

- Add migration scripts for south
- Fix rendering when probabilities close to 100%
- Reduce database load when a user performs an action multiple times

0.3.4
~~~~~

- Updated JS goal to POST method. Requires csrf javascript.
- Random number on template tag goal image to prevent caching


0.3.3
~~~~~

- Static media handled by nexus again

0.3.2
~~~~~

- Fixed missing edit/delete images

0.3.1
~~~~~

- Replaced django static template tags. Supports django 1.3 again!

0.3.0
~~~~~

- Added django permission support.
- Started using django static instead of nexus:media. (django 1.4 only)
