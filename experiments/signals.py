from __future__ import absolute_import

from experiments.utils import create_user

def transfer_enrollments_to_user(sender, request, user, **kwargs):
    anon_user = create_user(session=request.session)
    authenticated_user = create_user(user=user)
    authenticated_user.incorporate(anon_user)
