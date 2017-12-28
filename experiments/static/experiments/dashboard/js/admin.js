google.load('visualization', '1.0', {'packages':['corechart']});

(function($) {

    $(function() {
        var $table = $('#experiment-results-table');

        $('#experiment-toggle-goals').click(function() { $table.toggleClass('experiment-hide-irrelevant'); return false; });

        // ------------------------------ Changing the alternative

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

        // ------------------------------ Changing the state

        $('[data-set-state]').click(function() {
            var $this = $(this),
                $stateLabel = $('.form-row.state .grp-readonly, .form-row.field-state .readonly');
                $prevStateButton = $('[data-set-state].experiment-state-selected');
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
                    $stateLabel.html($this.html());
                },
                error: function() {
                    $('[data-set-state="' + $prevStateButton.data('set-state') + '"]').addClass('experiment-state-selected');
                }
            });

            return false;
        });

        // ------------------------------ Showing MWU charts

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

        // ------------------------------ Relevant goal checkbox inputs

        function getGoalList(goalType) {
            if (goalType === 'chi2') {
                return $('#id_relevant_chi2_goals').val() + ',';
            }
            if (goalType === 'mwu') {
                return $('#id_relevant_mwu_goals').val() + ','
            }
            if (goalType === 'primary') {
                return $('#id_primary_goals').val() + ','
            }
        }

        function setGoalList(goalType, goalList) {
            if (goalType === 'chi2') {
                return $('#id_relevant_chi2_goals').val(goalList.replace(/,$/, ''));
            }
            if (goalType === 'mwu') {
                return $('#id_relevant_mwu_goals').val(goalList.replace(/,$/, ''));
            }
            if (goalType === 'primary') {
                return $('#id_primary_goals').val(goalList.replace(/,$/, ''));
            }
        }

        /**
         * Keep checkboxes for "primary" goals enabled or disabled, and uncheck if needed
         */
        function refreshPrimaryCheckboxes() {
            var goalList = getGoalList('primary');
            $('#goal-list').children().each(function() {
                var $tr = $(this);
                var goal = $tr.data('goal');
                var isActualGoal = $tr.find(
                    '[data-goal-type="chi2"]:checked, [data-goal-type="mwu"]:checked'
                ).length > 0;
                var $primaryCheckbox = $tr.find('[data-goal-type="primary"]');
                var isChecked = $primaryCheckbox.is(':checked');

                $primaryCheckbox.attr('disabled', !isActualGoal);
                if (!isActualGoal) {
                    $primaryCheckbox.attr('checked', false);
                }

                if (isChecked) {
                    if (goalList.indexOf(goal + ',') === -1) {
                        goalList += goal;
                    }
                } else {
                    goalList = goalList.replace(goal + ',', '');
                }
            });
            setGoalList('primary', goalList);
        }

        var chi2Goals = getGoalList('chi2'),
            mwuGoals = getGoalList('mwu'),
            primaryGoals = getGoalList('primary');

        var $goals = $('#goal-list').children().each(function() {
            var $tr = $(this);
            if (chi2Goals.indexOf($tr.data('goal') + ',') > -1) {
                $tr.find('[data-goal-type="chi2"]').attr('checked', true);
            }
            if (mwuGoals.indexOf($tr.data('goal') + ',') > -1) {
                $tr.find('[data-goal-type="mwu"]').attr('checked', true);
            }
            if (primaryGoals.indexOf($tr.data('goal') + ',') > -1) {
                $tr.find('[data-goal-type="primary"]').attr('checked', true);
            }
        });

        refreshPrimaryCheckboxes();

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
                if (goalType !== 'primary') {
                    refreshPrimaryCheckboxes();
                }
            }
        });

        // Tweak appearance of Alternatives inline
        $('.js-alternatives').prependTo('#experimentalternative_set-group');

    });

})(django.jQuery);
