"""
General social auth settings
Automatically includes on `SSO_AUTH = True`
"""

LOGIN_URL = '/login/sso_tp-oauth2'
AUTHENTICATION_BACKENDS = (
    'sso_auth.social_auth_backends.TpBackend',
    'django.contrib.auth.backends.ModelBackend',
)
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'sso_auth.pipeline.create_or_update_permissions',
    'social_core.pipeline.user.user_details',
    'sso_auth.pipeline.update_user_name'
)

SOCIAL_NEXT_URL = '/'
