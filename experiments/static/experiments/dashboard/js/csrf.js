(function($) {
    // Mostly copied from the Django docs

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
})(django.jQuery);
