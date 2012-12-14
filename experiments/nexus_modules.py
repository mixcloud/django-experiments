from django.conf.urls.defaults import patterns, url

from functools import wraps

from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import ValidationError

from experiments.models import Experiment, ENABLED_STATE, GARGOYLE_STATE, CONTROL_GROUP
from experiments.significance import chi_square_p_value, mann_whitney

import nexus
import json

def rate(a, b):
    if not b or a == None:
        return None
    return 100. * a / b

def improvement(a, b):
    if not b or not a:
        return None
    return (a - b) * 100. / b

def chi_squared_confidence(a_count, a_conversion, b_count, b_conversion):
    contingency_table = [[a_count - a_conversion, a_conversion],
                         [b_count - b_conversion, b_conversion]]

    chi_square, p_value = chi_square_p_value(contingency_table)
    if p_value is not None:
        return (1 - p_value) * 100
    else:
        return None

def average_actions(distribution, count):
    if not count:
        return 0
    total_actions = sum(actions*frequency for (actions, frequency) in distribution.items())
    return total_actions / float(count)

def fixup_distribution(distribution, count):
    zeros = count - sum(distribution.values())
    distribution[0] = zeros

def mann_whitney_confidence(a_distribution, a_count, b_distribution, b_count):
    fixup_distribution(a_distribution, a_count)
    fixup_distribution(b_distribution, b_count)
    p_value = mann_whitney(a_distribution, b_distribution)[1]
    if p_value is not None:
        return (1 - p_value * 2) * 100 # Two tailed probability
    else:
        return None

class ExperimentException(Exception):
    pass

def json_result(func):
    "Decorator to make JSON views simpler"
    def wrapper(self, request, *args, **kwargs):
        try:
            response = {
                "success": True,
                "data": func(self, request, *args, **kwargs)
            }
        except ExperimentException, exc:
            response = {
                "success": False,
                "data": exc.message
            }
        except Experiment.DoesNotExist:
            response = {
                "success": False,
                "data": "Experiment cannot be found"
            }
        except ValidationError, e:
            response = {
                "success": False,
                "data": u','.join(map(unicode, e.messages)),
            }
        except Exception:
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            raise
        return HttpResponse(json.dumps(response), mimetype="application/json")
    wrapper = wraps(func)(wrapper)
    return wrapper

class ExperimentsModule(nexus.NexusModule):
    home_url = 'index'
    name = 'experiments'

    def get_title(self):
        return 'Experiments'

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^$', self.as_view(self.index), name='index'),
            url(r'^add/$', self.as_view(self.add), name='add'),
            url(r'^update/$', self.as_view(self.update), name='update'),
            url(r'^delete/$', self.as_view(self.delete), name='delete'),
            url(r'^state/$', self.as_view(self.state), name='state'),
            url(r'^results/(?P<name>[a-zA-Z0-9-_]+)/$', self.as_view(self.results), name='results'),
        )
        return urlpatterns

    def render_on_dashboard(self, request):
        enabled_experiments_count = Experiment.objects.filter(state__in=[ENABLED_STATE, GARGOYLE_STATE]).count()
        enabled_experiments = list(Experiment.objects.filter(state__in=[ENABLED_STATE, GARGOYLE_STATE]).order_by("start_date")[:5])
        return self.render_to_string('nexus/experiments/dashboard.html', {
            'enabled_experiments': enabled_experiments,
            'enabled_experiments_count': enabled_experiments_count,
        }, request)

    def index(self, request):
        sort_by = request.GET.get('by', '-start_date')
        experiments = Experiment.objects.all().order_by(sort_by)

        return self.render_to_response("nexus/experiments/index.html", {
            "experiments": [e.to_dict() for e in experiments],
            "all_goals": json.dumps(getattr(settings, 'EXPERIMENTS_GOALS', [])),
            "sorted_by": sort_by,
        }, request)

    def results(self, request, name):
        experiment = Experiment.objects.get(name=name)

        try:
            chi2_goals = experiment.relevant_chi2_goals.replace(" ", "").split(",")
        except AttributeError:
            chi2_goals = [u'']
        try:
            mwu_goals = experiment.relevant_mwu_goals.replace(" ", "").split(",")
        except AttributeError:
            mwu_goals = [u'']
        relevant_goals = set(chi2_goals + mwu_goals)

        alternatives = {}
        for alternative_name in experiment.alternatives.keys():
            alternatives[alternative_name] = experiment.participant_count(alternative_name)
        alternatives = sorted(alternatives.items())

        control_participants = experiment.participant_count(CONTROL_GROUP)

        results = {}

        for goal in getattr(settings, 'EXPERIMENTS_GOALS', []):
            alternatives_conversions = {}
            control_conversions = experiment.goal_count(CONTROL_GROUP, goal)
            control_conversion_rate = rate(control_conversions, control_participants)
            control_conversion_distribution = experiment.goal_distribution(CONTROL_GROUP, goal)
            control_average_goal_actions = average_actions(control_conversion_distribution, control_participants)
            for alternative_name in experiment.alternatives.keys():
                if not alternative_name == CONTROL_GROUP:
                    alternative_conversions = experiment.goal_count(alternative_name, goal)
                    alternative_participants = experiment.participant_count(alternative_name)
                    alternative_conversion_rate = rate(alternative_conversions,  alternative_participants)
                    alternative_confidence = chi_squared_confidence(alternative_participants, alternative_conversions, control_participants, control_conversions)
                    if goal in mwu_goals:
                        alternative_conversion_distribution = experiment.goal_distribution(alternative_name, goal)
                        alternative_average_goal_actions = average_actions(alternative_conversion_distribution, alternative_participants)
                        alternative_distribution_confidence = mann_whitney_confidence(
                            alternative_conversion_distribution, alternative_participants,
                            control_conversion_distribution, control_participants)
                    else:
                        alternative_average_goal_actions = None
                        alternative_distribution_confidence = None
                    alternative = {
                        'conversions': alternative_conversions,
                        'conversion_rate': alternative_conversion_rate,
                        'improvement': improvement(alternative_conversion_rate, control_conversion_rate),
                        'confidence': alternative_confidence,
                        'average_goal_actions': alternative_average_goal_actions,
                        'mann_whitney_confidence': alternative_distribution_confidence,
                    }
                    alternatives_conversions[alternative_name] = alternative

            control = {
                'conversions':control_conversions,
                'conversion_rate':control_conversion_rate,
                'average_goal_actions': control_average_goal_actions,
            }

            results[goal] = {
                "control": control,
                "alternatives": sorted(alternatives_conversions.items()),
                "relevant": goal in relevant_goals or relevant_goals == set([u'']),
                "mwu" : goal in mwu_goals
            }

        return self.render_to_response("nexus/experiments/results.html", {
            'experiment': experiment.to_dict(),
            'alternatives': alternatives,
            'control_participants': control_participants,
            'results': results,
        }, request)

    @json_result
    def state(self, request):
        if not request.user.has_perm('experiments.change_experiment'):
            raise ExperimentException("You do not have permission to do that!")

        experiment = Experiment.objects.get(name=request.POST.get("name"))
        try:
            state = int(request.POST.get("state"))
        except ValueError:
            raise ExperimentException("State must be integer")

        experiment.state = state

        if state == 0:
            import datetime
            experiment.end_date = datetime.datetime.now()
        else:
            experiment.end_date = None

        experiment.save()

        response = {
            "success": True,
            "experiment": experiment.to_dict_serialized(),
        }

        return response

    @json_result
    def add(self, request):
        if not request.user.has_perm('experiments.add_experiment'):
            raise ExperimentException("You do not have permission to do that!")

        name = request.POST.get("name")

        if not name:
            raise ExperimentException("Name cannot be empty")

        if len(name) > 128:
            raise ExperimentException("Name must be less than or equal to 128 characters in length")

        experiment, created = Experiment.objects.get_or_create(
            name         = name,
            defaults     = dict(
                switch_key = request.POST.get("switch_key"),
                description = request.POST.get("desc"),
                relevant_chi2_goals = request.POST.get("chi2_goals"),
                relevant_mwu_goals = request.POST.get("mwu_goals"),
            ),
        )

        if not created:
            raise ExperimentException("Experiment with name %s already exists" % name)

        response = {
            'success': True,
            'experiment': experiment.to_dict_serialized(),
        }

        return response

    @json_result
    def update(self, request):
        if not request.user.has_perm('experiments.change_experiment'):
            raise ExperimentException("You do not have permission to do that!")

        experiment = Experiment.objects.get(name=request.POST.get("curname"))

        experiment.switch_key = request.POST.get("switch_key")
        experiment.description = request.POST.get("desc")
        experiment.relevant_chi2_goals = request.POST.get("chi2_goals")
        experiment.relevant_mwu_goals = request.POST.get("mwu_goals")
        experiment.save()

        response = {
            'success': True,
            'experiment': experiment.to_dict_serialized()
        }

        return response


#    @permission_required(u'experiments.delete_experiment')
    @json_result
    def delete(self, request):
        if not request.user.has_perm('experiments.delete_experiment'):
            raise ExperimentException("You don't have permission to do that!")
        experiment = Experiment.objects.get(name=request.POST.get("name"))

        experiment.enrollment_set.all().delete()
        experiment.delete()
        return {'successful': True}

nexus.site.register(ExperimentsModule, 'experiments')
