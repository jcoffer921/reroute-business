from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import BlogPost


class JournalPrivacyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user_one = user_model.objects.create_user(
            username="journal_user_one", email="one@example.com", password="pass1234"
        )
        self.user_two = user_model.objects.create_user(
            username="journal_user_two", email="two@example.com", password="pass1234"
        )
        self.staff_user = user_model.objects.create_user(
            username="staff_member", email="staff@example.com", password="pass1234", is_staff=True
        )

        self.user_one_entry = BlogPost.objects.create(
            title="Entry One",
            content="Private reflections from user one.",
            owner=self.user_one,
            visibility=BlogPost.VISIBILITY_PRIVATE,
            category=BlogPost.CATEGORY_JOURNAL,
            published=False,
        )
        self.user_two_entry = BlogPost.objects.create(
            title="Entry Two",
            content="Private reflections from user two.",
            owner=self.user_two,
            visibility=BlogPost.VISIBILITY_PRIVATE,
            category=BlogPost.CATEGORY_JOURNAL,
            published=False,
        )
        self.public_story = BlogPost.objects.create(
            title="Public Story",
            content="Visible to everyone.",
            visibility=BlogPost.VISIBILITY_PUBLIC,
            category=BlogPost.CATEGORY_STORY,
            slug="public-story",
            published=True,
        )

    def test_user_cannot_access_another_users_journal_detail(self):
        self.client.login(username="journal_user_one", password="pass1234")
        response = self.client.get(reverse("journal_detail", args=[self.user_two_entry.pk]))
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_access_another_users_journal_edit(self):
        self.client.login(username="journal_user_one", password="pass1234")
        response = self.client.get(reverse("journal_edit", args=[self.user_two_entry.pk]))
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_access_another_users_journal_delete(self):
        self.client.login(username="journal_user_one", password="pass1234")
        response = self.client.get(reverse("journal_delete", args=[self.user_two_entry.pk]))
        self.assertEqual(response.status_code, 404)

    def test_public_stories_list_excludes_private_entries(self):
        response = self.client.get(reverse("stories_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Story")
        self.assertNotContains(response, "Entry One")
        self.assertNotContains(response, "Entry Two")

    def test_anonymous_user_redirected_from_journal_routes(self):
        detail_url = reverse("journal_detail", args=[self.user_one_entry.pk])
        edit_url = reverse("journal_edit", args=[self.user_one_entry.pk])
        delete_url = reverse("journal_delete", args=[self.user_one_entry.pk])

        for url in [reverse("journal_home"), reverse("journal_create"), detail_url, edit_url, delete_url]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response.url)

    def test_any_user_can_view_public_story_detail(self):
        response = self.client.get(reverse("stories_detail", args=[self.public_story.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Story")

    def test_staff_can_view_public_stories(self):
        self.client.login(username="staff_member", password="pass1234")
        response = self.client.get(reverse("stories_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Story")
