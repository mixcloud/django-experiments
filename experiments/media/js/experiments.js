// Subscribe to an event that triggers when the user attains a goal.
// $(experiments).bind("goal-attained", function(event, goalName) {
//     // do something (like send the goal attainment information to 
//     // a third party service such as google analytics)
// });

experiments = function() {
    return {
        confirm_human: function() {
            $.get("/experiments/confirm_human/");
        },
        goal: function(goal_name) {
            $.post("/experiments/goal/" + goal_name);

            // Trigger the experiments 'goal' event so others
            // can do something in reaction to goal attainment.
            $(experiments).trigger('goal-attained', [goal_name]);
        }
    };
}();

if (document.addEventListener) {
    // sets the cookie in the capturing phase so that in the bubbling phase we guarantee that if a request is being issued it will contain the new cookie as well
    document.addEventListener("click", function(event) {
        if ((event.target).hasAttribute('data-experiments-goal')) {
            $.cookie("experiments_goal", $(event.target).data('experiments-goal'), { path: '/' });

            // Trigger the experiments 'goal' event so others
            // can do something in reaction to goal attainment.
            $(experiments).trigger('goal-attained', [goal_name]);
        }
    }, true);
} else { // IE 8
    $(document).delegate('[data-experiments-goal]', 'click', function(e) {
        // if a request is fired by the click event, the cookie might get set after it, thus the goal will be recorded with the next request (if there will be one)
        $.cookie("experiments_goal", $(this).data('experiments-goal'), { path: '/' });

            // Trigger the experiments 'goal' event so others
            // can do something in reaction to goal attainment.
            $(experiments).trigger('goal-attained', [goal_name]);
    });
}

$(function() {
    $(".experiments-goal").each(function() {

        // Trigger the experiments 'goal-attained' event so others
        // can do something in reaction to template-tag goal attainment.
        $(experiments).trigger('goal-attained', [$(this).data("experiments-goal-name")]);
    });
});
