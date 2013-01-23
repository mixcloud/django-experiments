experiments = function() {
    return {
        confirm_human: function() {
            $.get("/experiments/confirm_human/");
        },
        goal: function(goal_name) {
            $.post("/experiments/goal/" + goal_name + "/");
        }
    };
}();

if (document.addEventListener) {
    // sets the cookie in the capturing phase so that in the bubbling phase we guarantee that if a request is being issued it will contain the new cookie as well
    document.addEventListener("click", function(event) {
        closest = $(event.target).closest('[data-experiments-goal]')
        if (closest.length) {
            $.cookie("experiments_goal", $(closest[0]).data('experiments-goal'), { path: '/' });
        }
    }, true);
} else { // IE 8
    $(document).delegate('[data-experiments-goal]', 'click', function(e) {
        // if a request is fired by the click event, the cookie might get set after it, thus the goal will be recorded with the next request (if there will be one)
        $.cookie("experiments_goal", $(this).data('experiments-goal'), { path: '/' });
    });
}
