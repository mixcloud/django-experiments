
(function($) {

    $(function() {

        var $a = $('.state_toggle > a');
        var URL_TEMPLATE = '/experiments/api/v1/remote_experiment/EXPERIMENT_ID/state/';

        var stateToggleClickHandler = function(event) {
            event.preventDefault();

            var $this = $(this);
            var experimentID = $this.data('id');
            var state = $this.data('state');
            var url = URL_TEMPLATE.replace('EXPERIMENT_ID', experimentID);
            $.ajax(
                url,
                {
                    method: 'PATCH',
                    contentType: 'application/json',
                    data: JSON.stringify({state: state})
                }
            )
                .done(function() {
                    console.info( "success" );
                })
                .fail(function() {
                    console.info( "error" );
                })
                .always(function() {
                    console.info( "complete" );
                });
        };

        $a.on('click', stateToggleClickHandler);


    });

})(django.jQuery);
