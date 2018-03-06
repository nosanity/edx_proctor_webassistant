"""
Tests for SSO Auth decorators
"""
import unittest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings


class SetTokenCookieDecoratorTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            'test',
            'test@test.com',
            'password'
        )
        user.is_active = True
        user.save()

    @unittest.skipIf(settings.SSO_ENABLED, 'Skipping in case if SSO_ENABLED == True')
    def test_set_token_cookie_without_sso(self):
        client = Client()
        response = client.post(reverse('login'), {
            'username': 'test',
            'password': 'password'
        })
        self.assertIn('authenticated_token', response.cookies)
