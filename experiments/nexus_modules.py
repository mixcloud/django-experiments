from django.conf.urls import patterns, url

from functools import wraps

from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import ValidationError

from experiments.experiment_counters import ExperimentCounter
from experiments.models import Experiment, ENABLED_STATE
from experiments.significance import chi_square_p_value, mann_whitney
from experiments.dateutils import now
from experiments.utils import participant
from experiments import conf

import nexus
import json

MIN_ACTIONS_TO_SHOW = 3


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


def average_actions(distribution):
    total_users = 0
    total_actions = 0
    for actions, frequency in distribution.items():
        total_users += frequency
        total_actions += actions * frequency
    if total_users:
        return total_actions / float(total_users)
    else:
        return 0


def fixup_distribution(distribution, count):
    zeros = count - sum(distribution.values())
    distribution[0] = zeros + distribution.get(0, 0)
    return distribution


def mann_whitney_confidence(a_distribution, b_distribution):
    p_value = mann_whitney(a_distribution, b_distribution)[1]
    if p_value is not None:
        return (1 - p_value * 2) * 100  # Two tailed probability
    else:
        return None


def points_with_surrounding_gaps(points):
    """
    This function makes sure that any gaps in the sequence provided have stopper points at their beginning
    and end so a graph will be drawn with correct 0 ranges. This is more efficient than filling in all points
    up to the maximum value. For example:

    input: [1,2,3,10,11,13]
    output [1,2,3,4,9,10,11,12,13]
    """
    points_with_gaps = []
    last_point = -1
    for point in points:
        if last_point + 1 == point:
            pass
        elif last_point + 2 == point:
            points_with_gaps.append(last_point + 1)
        else:
            points_with_gaps.append(last_point + 1)
            points_with_gaps.append(point - 1)
        points_with_gaps.append(point)
        last_point = point
    return points_with_gaps


def conversion_distributions_to_graph_table(conversion_distributions):
    ordered_distributions = list(conversion_distributions.items())
    total_entries = dict((name, float(sum(dist.values()) or 1)) for name, dist in ordered_distributions)
    graph_head = [['x'] + [name for name, dist in ordered_distributions]]

    points_in_any_distribution = sorted(set(k for name, dist in ordered_distributions for k in dist.keys()))
    points_with_gaps = points_with_surrounding_gaps(points_in_any_distribution)
    graph_body = [[point] + [dist.get(point, 0) / total_entries[name] for name, dist in ordered_distributions] for point in points_with_gaps]

    accumulator = [0] * len(ordered_distributions)
    for point in range(len(graph_body) - 1, -1, -1):
        accumulator = [graph_body[point][j + 1] + accumulator[j] for j in range(len(ordered_distributions))]
        graph_body[point][1:] = accumulator

    interesting_points = [point for point in points_in_any_distribution if max(dist.get(point, 0) for name, dist in ordered_distributions) >= MIN_ACTIONS_TO_SHOW]
    if len(interesting_points):
        highest_interesting_point = max(interesting_points)
    else:
        highest_interesting_point = 0
    graph_body = [g for g in graph_body if g[0] <= highest_interesting_point and g[0] != 0]

    graph_table = graph_head + graph_body
    return json.dumps(graph_table)


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
        return HttpResponse(json.dumps(response), content_type="application/json")
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
            url(r'^set_alternative/$', self.as_view(self.set_alternative), name='set_alternative'),
            url(r'^results/(?P<name>[a-zA-Z0-9-_]+)/$', self.as_view(self.results), name='results'),
        )
        return urlpatterns

    def render_on_dashboard(self, request):
        enabled_experiments_count = Experiment.objects.filter(state=ENABLED_STATE).count()
        enabled_experiments = list(Experiment.objects.filter(state=ENABLED_STATE).order_by("start_date")[:5])
        return self.render_to_string('nexus/experiments/dashboard.html', {
            'enabled_experiments': enabled_experiments,
            'enabled_experiments_count': enabled_experiments_count,
        }, request)

    def index(self, request):
        sort_by = request.GET.get('by', '-start_date')
        experiments = Experiment.objects.all().order_by(sort_by)

        return self.render_to_response("nexus/experiments/index.html", {
            "experiments": [e.to_dict() for e in experiments],
            "all_goals": json.dumps(conf.ALL_GOALS),
            "sorted_by": sort_by,
        }, request)

    def results(self, request, name):
        experiment = Experiment.objects.get(name=name)
        experiment_counter = ExperimentCounter()

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
            alternatives[alternative_name] = experiment_counter.participant_count(experiment, alternative_name)
        alternatives = sorted(alternatives.items())

        control_participants = experiment_counter.participant_count(experiment, conf.CONTROL_GROUP)

        results = {}

        for goal in conf.ALL_GOALS:
            show_mwu = goal in mwu_goals

            alternatives_conversions = {}
            control_conversions = experiment_counter.goal_count(experiment, conf.CONTROL_GROUP, goal)
            control_conversion_rate = rate(control_conversions, control_participants)

            if show_mwu:
                mwu_histogram = {}
                control_conversion_distribution = fixup_distribution(experiment_counter.goal_distribution(experiment, conf.CONTROL_GROUP, goal), control_participants)
                control_average_goal_actions = average_actions(control_conversion_distribution)
                mwu_histogram['control'] = control_conversion_distribution
            else:
                control_average_goal_actions = None
            for alternative_name in experiment.alternatives.keys():
                if not alternative_name == conf.CONTROL_GROUP:
                    alternative_conversions = experiment_counter.goal_count(experiment, alternative_name, goal)
                    alternative_participants = experiment_counter.participant_count(experiment, alternative_name)
                    alternative_conversion_rate = rate(alternative_conversions, alternative_participants)
                    alternative_confidence = chi_squared_confidence(alternative_participants, alternative_conversions, control_participants, control_conversions)
                    if show_mwu:
                        alternative_conversion_distribution = fixup_distribution(experiment_counter.goal_distribution(experiment, alternative_name, goal), alternative_participants)
                        alternative_average_goal_actions = average_actions(alternative_conversion_distribution)
                        alternative_distribution_confidence = mann_whitney_confidence(alternative_conversion_distribution, control_conversion_distribution)
                        mwu_histogram[alternative_name] = alternative_conversion_distribution
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
                'conversions': control_conversions,
                'conversion_rate': control_conversion_rate,
                'average_goal_actions': control_average_goal_actions,
            }

            results[goal] = {
                "control": control,
                "alternatives": sorted(alternatives_conversions.items()),
                "relevant": goal in relevant_goals or relevant_goals == set([u'']),
                "mwu": goal in mwu_goals,
                "mwu_histogram": conversion_distributions_to_graph_table(mwu_histogram) if show_mwu else None
            }

        return self.render_to_response("nexus/experiments/results.html", {
            'experiment': experiment.to_dict(),
            'alternatives': alternatives,
            'control_participants': control_participants,
            'results': results,
            'column_count': len(alternatives_conversions) * 3 + 2,  # Horrible coupling with template design
            'user_alternative': participant(request).get_alternative(experiment.name),
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
            experiment.end_date = now()
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
            name=name,
            defaults=dict(
                description=request.POST.get("desc"),
                relevant_chi2_goals=request.POST.get("chi2_goals"),
                relevant_mwu_goals=request.POST.get("mwu_goals"),
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
        experiment_counter = ExperimentCounter()
        experiment = Experiment.objects.get(name=request.POST.get("name"))

        experiment.enrollment_set.all().delete()
        experiment_counter.delete(experiment)
        experiment.delete()
        return {'successful': True}

    @json_result
    def set_alternative(self, request):
        experiment_name = request.POST.get("experiment")
        alternative_name = request.POST.get("alternative")
        participant(request).set_alternative(experiment_name, alternative_name)
        return {
            'success': True,
            'alternative': participant(request).get_alternative(experiment_name)
        }

nexus.site.register(ExperimentsModule, 'experiments')
