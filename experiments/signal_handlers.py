from experiments.utils import participant, clear_participant_cache


def transfer_enrollments_to_user(sender, request, user, **kwargs):
    anon_user = participant(session=request.session)
    authenticated_user = participant(user=user)
    authenticated_user.incorporate(anon_user)

    clear_participant_cache(request)


def handle_user_logged_out(sender, request, user, **kwargs):
    clear_participant_cache(request)