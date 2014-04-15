from __future__ import absolute_import

from experiments.utils import participant


def transfer_enrollments_to_user(sender, request, user, **kwargs):
    anon_user = participant(session=request.session)
    authenticated_user = participant(user=user)
    authenticated_user.incorporate(anon_user)
