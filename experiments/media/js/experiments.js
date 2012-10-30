// experiments contains methods and events for using javascript and the
// django-experiments library.
// Tell the server the user attained goal 'foo'.
// experiments.goal("foo");
//
// Subscribe to an event that triggers when the user attains a goal.
// $(experiments).bind("goal", function(event, goalName) {
//     // do something (like send the goal attainment information to 
//     // a third party service such as google analytics)
// });
experiments = function() {
    return {
        confirm_human: function() {
            $.get("/experiments/confirm_human/");
        },
        goal: function(goal_name) {
            $.post("/experiments/goal/" + goal_name).success(function() {
                // Trigger the experiments 'goal' event so others
                // can do something in reaction to goal attainment.
                $(experiments).trigger('goal', [goal_name]);
            });
        }
    };
}();

$(function(){
    $('[data-experiments-goal]').each(function() {
        $(this).bind('click', function() {
            $.cookie("experiments_goal", $(this).data('experiments-goal'), { path: '/' });
            experiments.goal($(this).data('experiments-goal'));
        });
    });
});

$(function() {
    $(".experiments-goal").each(function() {
        experiments.goal($(this).data('experiments-goal-name'));
    });
});
