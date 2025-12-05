from django.test import TestCase
from django.urls import reverse

from main.models import YouTubeVideo
from resources.models import Lesson, Module


class VideoGalleryMappingTests(TestCase):
    def test_youtube_ids_map_to_module_and_lesson(self):
        mod = Module.objects.create(
            title="Short Link Module",
            description="",
            category=Module.CATEGORY_DIGITAL,
            video_url="https://youtu.be/abc123",
        )
        lesson = Lesson.objects.create(
            title="Short Lesson",
            slug="short-lesson",
            description="",
            video_static_path="/static/resources/videos/demo.mp4",
            youtube_video_id="abc123",
            duration_seconds=30,
        )
        video = YouTubeVideo.objects.create(
            title="Short link",
            video_url="https://youtube.com/watch?v=abc123",
            category="",
            tags="soft-skills, resume",
        )

        response = self.client.get(reverse("video_gallery"))
        self.assertEqual(response.status_code, 200)
        page_videos = response.context["page_obj"].object_list
        ctx_video = next(v for v in page_videos if v.id == video.id)

        self.assertEqual(getattr(ctx_video, "youtube_id2", ""), "abc123")
        self.assertEqual(getattr(ctx_video, "module_id", None), mod.id)
        self.assertEqual(getattr(ctx_video, "lesson_slug", ""), lesson.slug)
        self.assertEqual(getattr(ctx_video, "effective_category", ""), "module")
        self.assertIn("soft-skills", getattr(ctx_video, "effective_tags", ""))

    def test_title_slug_collisions_do_not_attach_wrong_module_and_filtering(self):
        # Two modules with identical slugs should not auto-attach by title
        Module.objects.create(
            title="Duplicate Name",
            description="",
            category=Module.CATEGORY_DIGITAL,
        )
        Module.objects.create(
            title="Duplicate Name",
            description="",
            category=Module.CATEGORY_WORKFORCE,
        )
        video_other = YouTubeVideo.objects.create(
            title="Duplicate Name",
            video_url="https://youtu.be/zzz111",
            category="",
        )
        video_quick = YouTubeVideo.objects.create(
            title="Quick Tip",
            video_url="https://youtu.be/quick000",
            category="quick",
        )

        resp_bad_cat = self.client.get(reverse("video_gallery"), {"cat": "invalid"})
        self.assertEqual(resp_bad_cat.status_code, 200)
        page_all = resp_bad_cat.context["page_obj"].object_list
        ids_all = {v.id for v in page_all}
        self.assertIn(video_other.id, ids_all)
        self.assertIn(video_quick.id, ids_all)

        ctx_other = next(v for v in page_all if v.id == video_other.id)
        self.assertFalse(getattr(ctx_other, "module_id", None))
        self.assertEqual(getattr(ctx_other, "effective_category", ""), "other")

        resp_quick = self.client.get(reverse("video_gallery"), {"cat": "quick"})
        self.assertEqual(resp_quick.status_code, 200)
        ids_quick = {v.id for v in resp_quick.context["page_obj"].object_list}
        self.assertEqual(ids_quick, {video_quick.id})

    def test_pagination_limits_results(self):
        videos = [
            YouTubeVideo.objects.create(
                title=f"Video {i}",
                video_url=f"https://youtu.be/{i}",
                category="other",
            )
            for i in range(15)
        ]

        first_page = self.client.get(reverse("video_gallery"))
        self.assertEqual(first_page.status_code, 200)
        page_obj1 = first_page.context["page_obj"]
        self.assertLessEqual(len(page_obj1.object_list), 12)

        second_page = self.client.get(reverse("video_gallery"), {"page": 2})
        page_obj2 = second_page.context["page_obj"]
        self.assertEqual(page_obj2.number, 2)
        self.assertEqual(len(page_obj2.object_list), len(videos) - len(page_obj1.object_list))
