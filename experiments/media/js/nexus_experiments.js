$(document).ready(function () {
    
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
    $(".experiments tr").live("click", function (ev) {
        if (ev.target.tagName == 'A' || ev.target.tagName == 'INPUT' || ev.target.tagName == 'LABEL') {
            return;
        }

        activated = $(this).get(0)

        $(".experiments tr").each(function (_, el) {
            if (el == activated) {
                $(el).removeClass("collapsed");
            } else {
                $(el).addClass("collapsed");
            }
        });
    });


    $(".experiments .delete").live("click", function () {
        var row = $(this).parents("tr:first");
        var table = row.parents("table:first");

        var confirmdelete = confirm("Delete experiment \"" + row.attr("data-experiment-name") + '\"? This can be dangerous if a lot of people are enrolled!')

        if (confirmdelete) {
            api(EXPERIMENT.deleteExperiment, { name: row.attr("data-experiment-name") }, function (response) {
                row.remove();
                if (!table.find("tr").length) {
                    $("div.noExperiments").show();
                }
            });
        }
    });


    //Change state of experiment
    $("#container div.state button").live("click", function () {
        var el = $(this)
        var row = $(this).parent()
        var state = el.attr("data-state");

        api(EXPERIMENT.updateState,
            {
                name: row.attr("data-experiment-name"),
                state: state
            },
            function (response) {
                experiment = JSON.parse(response.experiment);
                if (experiment.state == state) {
                    row.find(".toggled").removeClass("toggled");
                    el.addClass("toggled");

                    //Hide or show end_date if disabled toggled
                    end_date = row.parent().parent().find("#" + experiment.name + "_end_date")

                    if (experiment.state == 0) {
                        end_date.html("To: " + experiment.end_date);
                        end_date.show();
                    } else {
                        end_date.hide();
                    }

                    //Hide or show conditions if selective toggled
                    conditions = row.parent().parent().find(".conditions")

                    if (experiment.state == 1) {
                        conditions.show();
                    } else {
                        conditions.hide();
                    }
                }
            });
    });

    $(".addExperiment").click(function (ev) {
        ev.preventDefault();
        $.facebox($("#experimentForm").tmpl({
            add:                 true,
            relevant_chi2_goals: [],
            relevant_mwu_goals:  [],
            all_goals:           nexus_experiments_all_goals
        }));
    });

    $(".experiments .edit").live("click", function () {
        var row = $(this).parents("tr:first");
        $.facebox($("#experimentForm").tmpl({
            add:                 false,
            curname:             row.attr("data-experiment-name"),
            name:                row.attr("data-experiment-name"),
            switch_key:          row.attr("data-experiment-switch"),
            desc:                row.attr("data-experiment-desc"),
            relevant_goals:      row.attr("data-experiment-goals"),
            relevant_chi2_goals: row.attr("data-experiment-chi2-goals").split(","),
            relevant_mwu_goals:  row.attr("data-experiment-mwu-goals").split(","),
            all_goals:           nexus_experiments_all_goals
        }));
    });

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

    $('.search input').keyup(function () {
        var query = $(this).val();

        $('.experiments tr').removeClass('hidden');

        if (!query) {
            return;
        }
        $('.experiments tr').each(function (_, el) {
            var score = 0;
           
            score += $(el).attr('data-experiment-name').score(query);
            score += $(el).attr('data-experiment-desc').score(query);
            
            if (score === 0) {
                $(el).addClass('hidden');
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
                    title: 'User count',
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


});
