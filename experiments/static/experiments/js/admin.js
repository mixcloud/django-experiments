google.load('visualization', '1.0', {'packages':['corechart']});

(function($) {

    $(function() {
        var $table = $('#experiment-results-table');

        $('#experiment-toggle-goals').click(function() {
            $table.toggleClass('experiment-hide-irrelevant');
            return false;
        });

        $('[data-alternative]').click(function() {
            var $this = $(this);

            if ($this.hasClass('experiment-selected-alternative')) {
                return false;
            }

            var $currentSelected = $('.experiment-selected-alternative[data-alternative]');

            $.ajax({
                url: $table.data('set-alternative-url'),
                data: {
                    experiment: $table.data('experiment-name'),
                    alternative: $this.data('alternative')
                },
                type: 'POST',
                dataType: 'json',
                success: function(data) {
                    if (data && data.success) {
                        $('[data-alternative="' + data.alternative + '"]').addClass('experiment-selected-alternative');
                    } else {
                        $currentSelected.addClass('experiment-selected-alternative');
                    }
                },
                error: function() {
                    $currentSelected.addClass('experiment-selected-alternative');
                }
            });

            $('[data-alternative]').removeClass('experiment-selected-alternative');

            return false;
        });

        $('[data-set-state]').click(function() {
            var $this = $(this),
                $stateSelect = $('#id_state');

            $('[data-set-state]').removeClass('experiment-state-selected');

            $.ajax({
                url: $table.data('set-state-url'),
                data: {
                    experiment: $table.data('experiment-name'),
                    state: $this.data('set-state')
                },
                type: 'POST',
                success: function() {
                    $this.addClass('experiment-state-selected');
                    $stateSelect.val($this.data('set-state'));
                },
                error: function() {
                    $('[data-set-state="' + $stateSelect.val() + '"]').addClass('experiment-state-selected');
                }
            });

            return false;
        });

        $('[data-chart-goal]').click(function() {
            var goal = $(this).data('chart-goal');

            $('#' + goal + '_mwu_row').toggle();

            var $graph = $('#' + goal + '_chart');

            if (!$graph.data('rendered')) {
                $graph.data('rendered', true);

                var chartData = google.visualization.arrayToDataTable(window.Experiments.EXPERIMENT_CHART_DATA[goal]),
                    chart = new google.visualization.LineChart($graph[0]),
                    options = {
                        height: 750,
                        hAxis: {
                            title: 'Performed action at least this many times',
                            logScale: true
                        },
                        vAxis : {
                            title: 'Fraction of users'
                        },
                        legend : {
                            position: 'top',
                            alignment: 'center'
                        },
                        chartArea: {
                            width: "75%",
                            height: "75%"
                        }
                    };

                chart.draw(chartData, options);
            }
        });

        function getGoalList(goalType) {
            if (goalType === 'chi2') {
                return $('#id_relevant_chi2_goals').val() + ',';
            }
            if (goalType === 'mwu') {
                return $('#id_relevant_mwu_goals').val() + ','
            }
        }

        function setGoalList(goalType, goalList) {
            if (goalType === 'chi2') {
                return $('#id_relevant_chi2_goals').val(goalList.replace(/,$/, ''));
            }
            if (goalType === 'mwu') {
                return $('#id_relevant_mwu_goals').val(goalList.replace(/,$/, ''));
            }
        }

        var chi2Goals = getGoalList('chi2'),
            mwuGoals = getGoalList('mwu');

        var $goals = $('#goal-list').children().each(function() {
            var $tr = $(this);
            if (chi2Goals.indexOf($tr.data('goal') + ',') > -1) {
                $tr.find('[data-goal-type="chi2"]').attr('checked', true);
            }
            if (mwuGoals.indexOf($tr.data('goal') + ',') > -1) {
                $tr.find('[data-goal-type="mwu"]').attr('checked', true);
            }
        });

        $goals.bind('click', function(event) {
            var $target = $(event.target);
            if ($target.is(':checkbox')) {
                var goalType = $target.data('goal-type'),
                    goalList = getGoalList(goalType),
                    goal = $target.closest('tr').data('goal');

                if ($target.is(':checked')) {
                    if (goalList.indexOf(goal + ',') === -1) {
                        goalList += goal;
                    }
                } else {
                    goalList = goalList.replace(goal + ',', '');
                }
                setGoalList(goalType, goalList);
            }
        });
    });

    // ------- CSRF

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = $.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) {
                return;
            }

            if (!this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });
})(django.jQuery);