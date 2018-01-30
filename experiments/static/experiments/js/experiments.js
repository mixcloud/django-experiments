experiments = function() {
    return {
        confirm_human: function() {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/experiments/confirm_human/');
            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            xhr.onload = function() {
                if (xhr.status < 200 || xhr.status > 299) {
                    throw 'POST to "/experiments/confirm_human/" failed. Returned status of ' + xhr.status;
                }
            };
            xhr.send();
        },
        goal: function(goal_name) {
            var xhr = new XMLHttpRequest();
            this.csrfToken = experimentsCsrfToken && experimentsCsrfToken();
            xhr.open('POST', '/experiments/goal/' + goal_name + '/');
            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            if (this.csrfToken) {
                xhr.setRequestHeader('X-CSRFToken', this.csrfToken);
            }
            xhr.onload = function() {
                if (xhr.status !== 200) {
                    throw 'POST to "/experiments/goal/" failed. Returned status of ' + xhr.status;
                }
            };
            xhr.send();
        },
        getCookie: function(name) {
            var cookieValue = null;
            if (document.cookie) {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = cookies[i] ? cookies[i].trim() : '';
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },
        csrfToken: null
    };
}();


/**
 * Simple helper, prefixed only to avoid name collisions.
 */
function experimentsCreateCookie(name, value, path, days) {
    var expires;
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toGMTString();
    }
    else {
        expires = "";
    }
    document.cookie = name + "=" + value + expires + "; path=" + path;
}


/**
 * Create a global delegate for click events.
 * Trigger a cookie if the required data attribute is present on the clicked node.
 */
if (document.addEventListener) {
    // sets the cookie in the capturing phase so that in the bubbling phase we guarantee that if a request is being issued it will contain the new cookie as well
    document.addEventListener("click", function(event) {
        var goal_name = event.target.getAttribute('data-experiments-goal');
        if (goal_name) {
            experimentsCreateCookie("experiments_goal", goal_name, '/')
        }
    }, true);
}
