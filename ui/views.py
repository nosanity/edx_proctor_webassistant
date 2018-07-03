"""
Views for application
"""
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as lgt, login as auth_login, \
    REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, resolve_url
from django.utils.http import is_safe_url
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import View

from sso_auth.social_auth_backends import NpoedBackend


class Index(View):
    """
    Main site view
    """
    template_name = 'index.html'

    def get(self, request):
        """
        Main view
        """
        user_has_access = request.user and request.user.is_authenticated \
            and request.user.permission_set.exists()
        login_url = reverse('social:begin', args=(
            'sso_npoed-oauth2',)) if settings.SSO_ENABLED else reverse('login')
        if not request.user.is_authenticated and settings.SSO_ENABLED:
            return HttpResponseRedirect(login_url)
        return render(
            request,
            self.template_name,
            {
                'user_has_access': user_has_access,
                'sso_enabled': settings.SSO_ENABLED,
                'project_name': settings.PROJECT_NAME,
                'my_profile_url': settings.SSO_NPOED_URL + '/profile' if settings.SSO_ENABLED else '',
                'my_courses_url': settings.PLP_NPOED_URL + '/my' if settings.PLP_NPOED_URL else '',
                'logo': settings.LOGO_NAME,
                'logo_is_url': settings.LOGO_NAME.startswith('http') if settings.LOGO_NAME else False,
                'login_url': login_url,
                'notifications_url': settings.NOTIFICATIONS['WEB_URL'],
                'profile_url': NpoedBackend.PROFILE_URL,
                'spa_config': json.dumps(settings.SPA_CONFIG),
                'suspicious_attempt_sound': settings.SUSPICIOUS_ATTEMPT_SOUND,
                'suspicious_attempt_sound_is_url': settings.SUSPICIOUS_ATTEMPT_SOUND.startswith('http')
                    if settings.SUSPICIOUS_ATTEMPT_SOUND else False,
            },
        )


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Okay, security check complete. Log the user in.
            auth_login(request, form.get_user())

            return HttpResponseRedirect(redirect_to)
        else:
            for field, text in form.error_messages.items():
                messages.error(request, text)
    return HttpResponseRedirect("/")


def logout(request, next_page=None,
           redirect_field_name=REDIRECT_FIELD_NAME, *args, **kwargs):
    """
    This view needed for correct redirect to sso-logout page
    """
    if redirect_field_name in request.POST or redirect_field_name in request.GET:
        next_page = request.POST.get(redirect_field_name,
                                     request.GET.get(redirect_field_name))

    if next_page:
        next_page = request.build_absolute_uri(next_page)
    else:
        next_page = request.build_absolute_uri('/')

    domain = settings.AUTH_SESSION_COOKIE_DOMAIN

    lgt(request)

    response = redirect('%s?%s=%s' % (settings.SSO_NPOED_URL + "/logout",
                                      redirect_field_name, next_page))
    response.set_cookie('authenticated', False, domain=domain)
    response.set_cookie('authenticated_user', 'Anonymous', domain=domain)
    response.set_cookie('authenticated_token', None, domain=domain)
    return response
