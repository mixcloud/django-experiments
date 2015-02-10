Django-Experiments
==================

Django-Experiments is an AB Testing Framework for Django and Nexus. It is
completely usable via template tags.

If you don't know what AB testing is, check out `wikipedia <http://en.wikipedia.org/wiki/A/B_testing>`_.

.. image:: https://s3-eu-west-1.amazonaws.com/mixcloud-public/django-experiments/Screen+Shot+2014-09-03+at+2.20.32+PM.png

.. image:: https://s3-eu-west-1.amazonaws.com/mixcloud-public/django-experiments/Screen+Shot+2014-09-03+at+2.20.47+PM.png

Changelog
---------

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


Installation
------------

Django-Experiments is best installed via pip:

::

    pip install django-experiments

This should download django-experiments and any dependencies. If downloading from the repo, 
pip is still the recommended way to install dependencies:

::

    pip install -r requirements.txt

Dependencies
------------
- `Django <https://github.com/django/django/>`_
- `Nexus <https://github.com/dcramer/nexus/>`_
- `Redis <http://redis.io/>`_
- `jsonfield <https://github.com/bradjasper/django-jsonfield/>`_

(Detailed list in requirements.txt)

Usage
-----

The example project is a good place to get started and have a play.
Results are stored in redis and displayed in the nexus admin. The key
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
        'django.contrib.humanize',
        'nexus',
        'experiments',
    ]

We haven't configured our goals yet, we'll do that in a bit. Please ensure
you have correctly configured your STATIC_URL setting.

*Note, more configuration options are detailed below.*


Experiments and Alternatives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The experiment is manually created in your nexus admin.\*

An experiment allows you to test the effect of various design
alternatives on user interaction. Nexus Experiments is designed to work
from within django templates, to make it easier for designers. We begin
by loading our module:

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

By default the participant function expects a HttpRequest object, but you can
alternatively pass a user or session as a keyword argument

::

    participant(user=current_user).get_alternative('register_text')
    participant(session=session).get_alternative('register_text')


\*\ *Experiments will be dynamically created by default if they are
defined in a template but not in the admin. This can be overridden in
settings.*


Goals
~~~~~

Goals allow us to acknowledge when a user hits a certain page. You
specify them in the EXPERIMENTS\_GOALS tuple in your settings. Given the
example above, we would want a goal to be triggered once the user has
completed the registration process.

Add the goal to our EXPERIMENT_GOALS tuple in setting.py:

::

    EXPERIMENTS_GOALS = ("registration")

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

Managing Experiments
--------------------

Experiments can be managed in the nexus dashboard (/nexus/experiments by
default).

The States
~~~~~~~~~~

**Control** - The experiment is essentially disabled. All users will see
the control alternative, and no data will be collected.

**Enabled** - The experiment is enabled globally, for all users.


All Settings
------------

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


    #Installed Apps
    INSTALLED_APPS = [
        ...
        'django.contrib.humanize',
        'nexus',
        'experiments',
    ]
