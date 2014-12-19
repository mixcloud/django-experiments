try:
    from django.conf.urls import patterns, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, url

from functools import wraps, update_wrapper

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.util import unquote
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils import simplejson as json
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from experiments.experiment_counters import ExperimentCounter
from experiments.models import Experiment, Enrollment
from experiments.significance import chi_square_p_value, mann_whitney
from experiments.dateutils import now
from experiments.utils import participant
from experiments import conf

MIN_ACTIONS_TO_SHOW = 3


def rate(a, b):
    if not b or a is None:
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
        return HttpResponse(json.dumps(response), mimetype="application/json")
    wrapper = wraps(func)(wrapper)
    return wrapper


class ExperimentsAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'state')
    list_filter = ('name', 'start_date', 'end_date', 'state')
    # date_hierarchy = 'start_date'
    ordering = ('-start_date', )
    search_fields = ('name', )
    fields = ("name", "switch_key", "description",
              "relevant_chi2_goals", "relevant_mwu_goals", "state")

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return ('name',)

    def as_view(self, view):
        def wrapper(*args, **kwargs):
            return self.admin_site.admin_view(view)(*args, **kwargs)
        return update_wrapper(wrapper, view)

    def render_to_response(self, template, data, request):
        return render_to_response(template, data, context_instance=RequestContext(request))

    def get_urls(self):
        urls = super(ExperimentsAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        urlpatterns = patterns('',
            url(r'^state/$', self.as_view(self.state), name='state'),
            url(r'^set_alternative/$', self.as_view(self.set_alternative), name='set_alternative'),
            url(r'^(.+)/results/$', self.as_view(self.results), name='%s_%s_results' % info),
        )
        urlpatterns += urls
        return urlpatterns

    def results(self, request, name):
        experiment = get_object_or_404(self.queryset(request), pk=unquote(name))
        experiment_counter = ExperimentCounter()

        if not self.has_change_permission(request, experiment):
            raise PermissionDenied

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

        opts = self.model._meta
        app_label = opts.app_label

        return self.render_to_response("admin/experiments/experiment/results.html", {
            'module_name': capfirst(force_text(opts.verbose_name_plural)),
            'title': _('Results: %s') % force_text(experiment),
            'app_label': app_label,
            'object': experiment,
            'opts': opts,
            'flag_url': reverse('admin:waffle_flag_change', args=(experiment.switch.pk,)) if experiment.switch else None,
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

        return {
            "success": True,
            "experiment": experiment.to_dict_serialized(),
        }

    @json_result
    def set_alternative(self, request):
        experiment_name = request.POST.get("experiment")
        alternative_name = request.POST.get("alternative")

        experiment = get_object_or_404(self.queryset(request), pk=unquote(experiment_name))

        if not self.has_change_permission(request, experiment):
            raise PermissionDenied

        participant(request).set_alternative(experiment_name, alternative_name)

        return {
            'success': True,
            'alternative': participant(request).get_alternative(experiment_name)
        }

admin.site.register(Enrollment)
admin.site.register(Experiment, ExperimentsAdmin)
