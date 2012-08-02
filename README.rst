Django-Experiments
==================

Django-Experiments is an AB Testing Framework for Django and Nexus. It is
completely usable via template tags. It provides support for conditional
user enrollment via Gargoyle.

If you don't know what AB testing is, check out `wikipedia <http://en.wikipedia.org/wiki/A/B_testing>`_.

.. image:: https://s3-eu-west-1.amazonaws.com/mixcloud-public/screenshot1.jpg

.. image:: https://s3-eu-west-1.amazonaws.com/mixcloud-public/screenshot2.jpg

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
- `Gargoyle <https://github.com/disqus/gargoyle/>`_
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
        'gargoyle',
        'experiments',
    ]

And add our middleware:

::

    MIDDLEWARE_CLASSES [
        ...
        'experiments.middleware.ExperimentsMiddleware',
    ]

We haven't configured our goals yet, we'll do that in a bit.

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

Our registration successful page will contain our goal, “registration”:

::

    {% experiment_goal "registration" %}

This will be fired when the user loads the page. There are three ways
ways of using goals: a server-sided python function, a JavaScript onclick event, or
cookies.

The python function, somewhere in your django views:

::

    from experiments.utils import record_goal

    record_goal(request, 'registration')

The JavaScript onclick method:

::

    <button onclick="experiments.goal('registration')">Complete Registration</button>

The cookie method:

::

    <span data-experiments-goal="registration">Complete Registration</span>

The goal is independent from the experiment as many experiments can all
have the same goal. The goals are defined in the settings.py file for
your project.

Confirming Human
~~~~~~~~~~~~~~~~

The framework can distinguish between humans and bots. By including

::

    {% include "experiments/confirm_human.html" %}

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

**Gargoyle** - If a switch\_key is specified, the experiment will rely
on the gargoyle switch to determine if the user is included in the
experiment. More on this below.

Using Gargoyle
~~~~~~~~~~~~~~

Gargoyle lets you toggle features to selective sets of users based on a
set of conditions. Connecting an experiment to a gargoyle “switch”
allows us to run targeted experiments - very useful if we don’t want to
expose everyone to it. For example, we could specify to run the result
to 10% of our users, or only to staff.


All Settings
------------

::

    #Experiment Goals
    EXPERIMENTS_GOALS = ()

    #Auto-create experiment if doesn't exist
    EXPERIMENTS_AUTO_CREATE = True

    #Auto-create gargoyle switch if switch doesn't exist when added to experiment
    EXPERIMENTS_SWITCH_AUTO_CREATE = True

    #Auto-delete gargoyle switch that the experiment is linked to on experiment deletion
    EXPERIMENTS_SWITCH_AUTO_DELETE = True

    #Naming scheme for gargoyle switch name if auto-creating
    EXPERIMENTS_SWITCH_LABEL = "Experiment: %s"

    #Toggle whether the framework should verify user is human. Be careful.
    EXPERIMENTS_VERIFY_HUMAN = False

    #Example Redis Settings
    EXPERIMENTS_REDIS_HOST = 'localhost'
    EXPERIMENTS_REDIS_PORT = 6379
    EXPERIMENTS_REDIS_DB = 0

    #Middleware
    MIDDLEWARE_CLASSES [
        ...
        'experiments.middleware.ExperimentsMiddleware',
    ]

    #Installed Apps
    INSTALLED_APPS = [
        ...
        'django.contrib.humanize',
        'nexus',
        'gargoyle',
        'experiments',
    ]   