
(function($) {

    $(function() {

        var $a = $('.state_toggle > a');
        var URL_TEMPLATE = '/experiments/api/v1/remote_experiment/EXPERIMENT_ID/state/';

        var stateToggleClickHandler = function(event) {
            event.preventDefault();

            var $this = $(this);
            if ($this.hasClass('working')) return;
            var $siblings = $this.parent().children();
            var experimentID = $this.data('id');
            var state = $this.data('state');
            var url = URL_TEMPLATE.replace('EXPERIMENT_ID', experimentID);
            $siblings.addClass('working');
            $.ajax(
                url,
                {
                    method: 'PATCH',
                    contentType: 'application/json',
                    timeout: 3000,  // milliseconds
                    data: JSON.stringify({state: state})
                }
            )
            .done(function(data) {
                var newState = data.state;
                console.info(newState, $this.data('state'));
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
                $this.parent().children().addClass('error');
            })
            .always(function() {
                $siblings.removeClass('working');
            });
        };

        $a.on('click', stateToggleClickHandler);

    });

})(django.jQuery);
