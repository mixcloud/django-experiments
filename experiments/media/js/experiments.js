experiments = function() {
    return {
        confirm_human: function() {
            $.get("/experiments/confirm_human/");
        },
        goal: function(goal_name) {
            $.get("/experiments/goal/" + goal_name);
        }
    };
}();

$(function(){
    $('[data-experiments-goal]').each(function() {
        $(this).bind('click', function() {
            $.cookie("experiments_goal", $(this).data('experiments-goal'), { path: '/' });
        });
    });
});

