(function($) {

    $(function() {

        var $a = $('.state_toggle > a');
        var URL_TEMPLATE = '/experiments/api/v1/remote_experiment/EXPERIMENT_ID/state/';
        var CONFIRMATION_TIMEOUT = 1000;  // milliseconds
        var UI_TIMEOUT = 1000;  // milliseconds

        var stateToggleClickHandler = function(event) {
            event.preventDefault();
            var $this = $(this);
            if ($this.hasClass('working')) return;
            if ($this.hasClass('really')) {
                executeStageChange($this);
            } else {
                $this.parent().children().removeClass('really');
                $this.addClass('really');
                setTimeout(
                    function() { notConfirmedTimeout($this); },
                    CONFIRMATION_TIMEOUT
                )
            }
        };

        var executeStageChange = function($this) {
            var $siblings = $this.parent().children();
            var experimentID = $this.data('id');
            var state = $this.data('state');
            var url = URL_TEMPLATE.replace('EXPERIMENT_ID', experimentID);

            $siblings.addClass('working');

            $.when(
                $.ajax(
                    url,
                    {
                        method: 'PATCH',
                        contentType: 'application/json',
                        timeout: 3000,  // milliseconds
                        data: JSON.stringify({state: state})
                    }
                ),
                createDelay(UI_TIMEOUT)
            )
            .done(function(ajax_result) {
                var response = ajax_result[0];
                var newState = response.state;
                if (newState !== $this.data('state')) {
                    $siblings.addClass('error');
                } else {
                    $siblings.removeClass('error');
                }
                $siblings.removeClass('active');
                $siblings.filter('[data-state="' + newState + '"]').addClass('active');
            })
            .fail(function() {
                $siblings.removeClass('active');
                $siblings.addClass('error');
            })
            .always(function() {
                $siblings.removeClass('working');
                $siblings.removeClass('really');
            });
        };

        var notConfirmedTimeout = function($this) {
            if ($this.hasClass('working')) return;
            $this.removeClass('really');
        };

        var createDelay = function(timeout) {
            var delay = $.Deferred();
            setTimeout(function() { delay.resolve(); }, timeout);
            return delay;
        };

        $a.on('click', stateToggleClickHandler);

    });

})(django.jQuery);
