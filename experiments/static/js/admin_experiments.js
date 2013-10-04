function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(document).ready(function () {

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                var csrftoken = getCookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    var api = function (url, params, succ) {
        $('#status').show();
        $.ajax({
            url: url,
            type: "POST",
            data: params,
            dataType: "json",
            success: function (resp) {
                $('#status').hide();

                if (resp.success) {
                    succ(resp.data);
                } else {
                    alert(resp.data);
                }
            },
            failure: function() {
                $('#status').hide();
                alert('There was an internal error. Data probably wasn\'t saved');
            }
        });
    };

    // Events
    $("#facebox .closeFacebox").live("click", function (ev) {
        ev.preventDefault();
        $.facebox.close();
    });

    $("#facebox .submitExperiment").live("click", function () {
        var action = $(this).attr("data-action");
        var curname = $(this).attr("data-curname");

        var relevant_chi2_goals = $("#facebox input[name=relevant_chi2_goals]:checked").map(function(){
            return $(this).val()
        }).get().join(",");
        var relevant_mwu_goals = $("#facebox input[name=relevant_mwu_goals]:checked").map(function(){
            return $(this).val()
        }).get().join(",");

        api(action == "add" ? EXPERIMENT.addExperiment : EXPERIMENT.updateExperiment,
            {
                curname: curname,
                name:       $("#facebox input[name=name]").val(),
                switch_key: $("#facebox input[name=switch_key]").val(),
                desc:       $("#facebox textarea[name=desc]").val(),
                chi2_goals: relevant_chi2_goals,
                mwu_goals:  relevant_mwu_goals
            },

            function (response) {
                experiment = JSON.parse(response.experiment);
                var result = $("#experimentData").tmpl(experiment);

                if (action == "add") {
                    if ($("table.experiments tr").length == 0) {
                        $("table.experiments").html(result);
                        $("table.experiments").removeClass("empty");
                        $("div.noExperiments").hide();
                    } else {
                        $("table.experiments tr:last").after(result);
                    }

                    $.facebox.close();
                } else {
                    $("table.experiments tr[data-experiment-name=" + curname + "]").replaceWith(result);
                    $.facebox.close();
                }

            });
    });

    $('#ToggleGoals').live("click", function () {

        obj = $('#container table.goals tbody tr.hiddengoal')

        if (obj.css('display') == 'none') {
            obj.show();
        } else {
            obj.hide()
        }
    });

    $(document).delegate('.toggle_chart', 'click', function(event) {
        event.preventDefault();

        var $graph = $('#' + $(this).data('element-id'));
        $graph.parent().toggle();
        if(!$graph.data('rendered')) {
            var chart_data = google.visualization.arrayToDataTable( EXPERIMENT_CHART_DATA[$graph.data('chart-key')] );
            var chart = new google.visualization.LineChart($graph.get(0));
            var options = {
                height: 750,
                hAxis : {
                    title: 'Performed action at least this many times',
                    logScale: true
                },
                vAxis : {
                    title: 'Fraction of users',
                    //logScale: true
                },
                legend : {
                    position: 'top',
                    alignment: 'center'
                },
                chartArea: {
                    width: "75%",
                    height: "75%"
                }
            }
            chart.draw(chart_data, options);

            $graph.data('rendered', 1);
        }
    });

    $(document).delegate('.js-join-alternative', 'click', function(event) {
        event.preventDefault();

        var $indicator = $(this).parent();
        var experiment = $indicator.data('experiment');
        var alternative = $indicator.data('alternative');

        api(EXPERIMENT.setAlternative,
            {
                'experiment': experiment,
                'alternative': alternative
            },
            function(response) {
                var alternative = response.alternative;
                // Update the display of enrolled variant
                $('.enrollment-indicator').each(function(){
                    var $indicator = $(this);
                    if ($indicator.data('alternative') === alternative) {
                        $indicator.html('Enrolled');
                    } else {
                        $indicator.html('<a href="#" class="js-join-alternative">Join</a>');
                    }
                });

            });
    });


});
