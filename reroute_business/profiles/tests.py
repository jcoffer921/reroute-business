from django.test import TestCase, RequestFactory
from django.urls import reverse, NoReverseMatch
from django.contrib.auth.models import User

from .models import EmployerProfile
from reroute_business.main.context_processors import role_flags


class ProfileRoutingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        # Standard user
        cls.user = User.objects.create_user(username="user1", password="pass")
        # Employer user + profile
        cls.employer = User.objects.create_user(username="boss", password="pass")
        EmployerProfile.objects.create(user=cls.employer, company_name="Boss Inc")

    def test_profile_routes_reverse(self):
        """Global and namespaced profile routes should reverse cleanly."""
        # User profile name
        self.assertEqual(reverse('my_profile'), '/profile/')

        # Employer profile — global alias should be present
        url = reverse('employer_profile')
        self.assertIn('/profile/employer/profile/', url)

        # Namespaced version via app include
        url_ns = reverse('profiles:employer_profile')
        self.assertIn('/profile/employer/profile/', url_ns)

    def test_context_processor_profile_url_user(self):
        req = self.factory.get('/')
        req.user = self.user
        ctx = role_flags(req)
        self.assertIn('PROFILE_URL', ctx)
        self.assertIn('/settings/', ctx['PROFILE_URL'])
        self.assertIn('panel=profile', ctx['PROFILE_URL'])

    def test_context_processor_profile_url_employer(self):
        req = self.factory.get('/')
        req.user = self.employer
        ctx = role_flags(req)
        self.assertIn('PROFILE_URL', ctx)
        self.assertIn('/settings/', ctx['PROFILE_URL'])
        self.assertIn('panel=profile', ctx['PROFILE_URL'])
