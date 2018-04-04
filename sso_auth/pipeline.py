"""
Python social auth pypelines
"""
import logging

from social_core.pipeline import partial

from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction

from person.models import Permission

log = logging.getLogger(__name__)


@transaction.atomic
def set_roles_for_edx_users(user, permissions):
    """
    This function create roles for proctors from sso permissions.
    """
    proctor_perm = {
        'Proctoring', '*'
    }
    global_perm = {
        'Read', 'Update', 'Delete', 'Publication', 'Enroll',
        'Manage(permissions)'
    }
    instructor_is_proctor = settings.INSTRUCTOR_IS_PROCTOR
    permission_list = []
    for permission in permissions:
        if bool(set(permission['obj_perm']) & proctor_perm) or \
                global_perm.issubset(set(permission['obj_perm'])):
            role = Permission.ROLE_PROCTOR if bool(
                set(permission['obj_perm']) & proctor_perm
            ) else Permission.ROLE_INSTRUCTOR
            roles = [role]
            if role == Permission.ROLE_INSTRUCTOR and instructor_is_proctor:
                roles.append(Permission.ROLE_PROCTOR)
            for role in roles:
                permission_list.append(
                    Permission(
                        object_type=permission['obj_type'] if permission['obj_type'] else '*',
                        object_id=permission['obj_id'],
                        user=user,
                        role=role
                    )
                )
    Permission.objects.filter(user=user).delete()
    Permission.objects.bulk_create(permission_list)


def _create_or_update_permissions(backend, user, response, *args, **kwargs):
    permissions = response.get('permissions')
    if permissions is not None:
        try:
            set_roles_for_edx_users(user, permissions)
        except Exception as e:
            log.error('set_roles_for_edx_users error: {}'.format(e))
    return response


@partial.partial
def create_or_update_permissions(backend, user, response, *args, **kwargs):
    """
    Create or update permissions from SSO on every auth
    :return: Response
    """
    return _create_or_update_permissions(backend, user, response, *args, **kwargs)


def _update_user_name(backend, user, response, *args, **kwargs):
    try:
        user = User.objects.get(email=response['email'])
        user.first_name = response.get('firstname')
        user.last_name = response.get('lastname')
        user.save()
    except User.DoesNotExist:
        pass


@partial.partial
def update_user_name(backend, user, response, *args, **kwargs):
    """
    Ensure that we have the necessary information about a user (either an
    existing account or registration data) to proceed with the pipeline.
    """
    _update_user_name(backend, user, response, *args, **kwargs)
