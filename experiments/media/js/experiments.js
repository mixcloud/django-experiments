experiments = function() {
    return {
        confirm_human: function() {
            $.get("/experiments/confirm_human/");
        },
        goal: function(goal_name) {
            $.post("/experiments/goal/" + goal_name);
        }
    };
}();

$(document).delegate('[data-experiments-goal]', 'click', function() {
    $.cookie("experiments_goal", $(this).data('experiments-goal'), { path: '/' });
});
