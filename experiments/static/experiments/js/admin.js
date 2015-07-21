(function($) {

    $(function() {
        var $table = $('#experiment-results-table');

        $('#experiment-toggle-goals').click(function() {
            $table.toggleClass('experiment-hide-irrelevant');
            return false;
        });

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

        $('[data-set-state]').click(function() {
            var $this = $(this),
                $stateSelect = $('#id_state');

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
                    $stateSelect.val($this.data('set-state'));
                },
                error: function() {
                    $('[data-set-state="' + $stateSelect.val() + '"]').addClass('experiment-state-selected');
                }
            });

            return false;
        });
    });

    // ------- CSRF

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
})(django.jQuery);